from __future__ import annotations

import io
import logging
import threading
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings

logger = logging.getLogger("trilha.face")
settings = get_settings()

MODEL_NAME = "buffalo_l"
MODEL_PROVIDER = "CPUExecutionProvider"
EMBEDDING_DIMENSIONS = 512
ANALYSIS_MAX_SIDE = 1920
MIN_IMAGE_SIDE = 240
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class FaceServiceError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class FaceServiceUnavailable(FaceServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="modelo_indisponivel", status_code=503)


class FaceQualityError(FaceServiceError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message, code=code, status_code=422)


@dataclass(frozen=True)
class FaceSample:
    embedding: np.ndarray
    detection_score: float
    quality: float
    bbox: tuple[int, int, int, int]
    model_name: str = MODEL_NAME


def _read_image(data: bytes) -> np.ndarray:
    try:
        with Image.open(io.BytesIO(data)) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise FaceQualityError(
                    "Formato de imagem não aceito. Use JPG, PNG ou WebP.",
                    code="formato_invalido",
                )
            width, height = probe.size
            if width * height > settings.face_max_image_pixels:
                raise FaceQualityError(
                    "A imagem é grande demais. Use uma foto de até 20 megapixels.",
                    code="imagem_grande",
                )
            if min(width, height) < MIN_IMAGE_SIDE:
                raise FaceQualityError(
                    "A imagem tem resolução muito baixa. Use uma foto maior.",
                    code="imagem_pequena",
                )
            image = ImageOps.exif_transpose(probe).convert("RGB")
            image.thumbnail((ANALYSIS_MAX_SIDE, ANALYSIS_MAX_SIDE), Image.Resampling.LANCZOS)
            rgb = np.asarray(image)
    except FaceServiceError:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise FaceQualityError(
            "Não foi possível ler a imagem. Escolha um arquivo JPG, PNG ou WebP nítido.",
            code="imagem_invalida",
        )
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def cosine_similarity(first: np.ndarray, second: np.ndarray) -> float:
    if first.shape != second.shape:
        return -1.0
    return float(np.dot(first, second))


def vector_from_bytes(data: bytes) -> np.ndarray:
    vector = np.frombuffer(data, dtype=np.float32)
    if vector.size != EMBEDDING_DIMENSIONS:
        raise ValueError("Vetor facial com dimensão inválida.")
    return vector


class FaceService:
    def __init__(self) -> None:
        self._analysis = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._analysis is not None

    def ensure_loaded(self) -> None:
        if self._analysis is not None:
            return
        with self._lock:
            if self._analysis is not None:
                return
            model_dir = settings.model_root_path / "models" / MODEL_NAME
            required_files = [
                model_dir / "det_10g.onnx",
                model_dir / "w600k_r50.onnx",
            ]
            missing = [path.name for path in required_files if not path.is_file()]
            if missing:
                raise FaceServiceUnavailable(
                    "Modelo facial buffalo_l não encontrado. Execute o setup com download do modelo."
                )
            try:
                from insightface.app import FaceAnalysis

                analysis = FaceAnalysis(
                    name=MODEL_NAME,
                    root=str(settings.model_root_path),
                    providers=[MODEL_PROVIDER],
                    allowed_modules=["detection", "recognition"],
                )
                analysis.prepare(
                    ctx_id=-1,
                    det_size=(settings.face_det_size, settings.face_det_size),
                )
            except Exception as exc:
                logger.exception("Falha ao carregar o modelo facial")
                raise FaceServiceUnavailable(
                    "Não foi possível carregar o modelo facial. Verifique os arquivos locais e os logs."
                ) from exc
            self._analysis = analysis
            logger.info("Modelo %s carregado em CPU.", MODEL_NAME)

    def analyze(self, data: bytes) -> FaceSample:
        image = _read_image(data)
        self.ensure_loaded()
        with self._lock:
            faces = self._analysis.get(image) if self._analysis is not None else []
        if not faces:
            raise FaceQualityError(
                "Não encontramos um rosto na imagem. Centralize o rosto, melhore a iluminação e tente novamente.",
                code="rosto_nao_encontrado",
            )
        if len(faces) > 1:
            raise FaceQualityError(
                "Há mais de um rosto na imagem. Faça a captura sozinho e evite pessoas ao fundo.",
                code="multiplos_rostos",
            )

        face = faces[0]
        detection_score = float(face.det_score)
        if detection_score < settings.face_min_det_score:
            raise FaceQualityError(
                "A imagem ficou desfocada, escura ou com o rosto parcialmente encoberto. Tente outra captura.",
                code="qualidade_baixa",
            )

        x1, y1, x2, y2 = (int(round(value)) for value in face.bbox)
        width = max(x2 - x1, 0)
        height = max(y2 - y1, 0)
        if min(width, height) < settings.face_min_face_pixels:
            raise FaceQualityError(
                "Aproxime-se da câmera para o rosto ocupar melhor o enquadramento.",
                code="rosto_pequeno",
            )

        image_height, image_width = image.shape[:2]
        center_x = ((x1 + x2) / 2) / image_width
        center_y = ((y1 + y2) / 2) / image_height
        if not (0.10 <= center_x <= 0.90 and 0.10 <= center_y <= 0.90):
            raise FaceQualityError(
                "Centralize o rosto dentro do guia antes de capturar.",
                code="rosto_fora_do_centro",
            )

        embedding = np.asarray(face.normed_embedding, dtype=np.float32)
        if embedding.size != EMBEDDING_DIMENSIONS:
            raise FaceServiceUnavailable("O modelo facial retornou um vetor inesperado.")
        embedding = embedding / max(float(np.linalg.norm(embedding)), 1e-12)

        return FaceSample(
            embedding=embedding,
            detection_score=round(detection_score, 4),
            quality=round(detection_score, 4),
            bbox=(x1, y1, x2, y2),
        )


_service: FaceService | None = None
_service_lock = threading.Lock()


def get_face_service() -> FaceService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = FaceService()
    return _service
