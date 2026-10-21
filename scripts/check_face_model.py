from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.face import FaceServiceError, cosine_similarity, get_face_service  # noqa: E402

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida o modelo facial com fotos locais.")
    parser.add_argument(
        "folder",
        nargs="?",
        default="imagens_teste/pessoa1",
        help="Pasta com 2 ou mais fotos da mesma pessoa.",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.30,
        help="Similaridade mínima entre duas capturas da mesma pessoa.",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_absolute():
        folder = ROOT / folder
    files = sorted(path for path in folder.iterdir() if path.suffix.lower() in EXTENSIONS)
    if len(files) < 2:
        print(f"Informe pelo menos duas imagens em {folder}.")
        return 2

    service = get_face_service()
    samples = []
    for path in files:
        try:
            sample = service.analyze(path.read_bytes())
        except FaceServiceError as exc:
            print(f"[FALHA] {path.name}: {exc.message}")
            return 1
        samples.append((path.name, sample))
        print(
            f"[OK] {path.name}: qualidade={sample.quality:.4f} "
            f"rosto={sample.bbox[2] - sample.bbox[0]}x{sample.bbox[3] - sample.bbox[1]}"
        )

    similarities = [
        (first[0], second[0], cosine_similarity(first[1].embedding, second[1].embedding))
        for first, second in combinations(samples, 2)
    ]
    for first, second, score in similarities:
        print(f"[SIM] {first} x {second}: {score:.4f}")

    minimum = min(score for _, _, score in similarities)
    print(f"\nMenor similaridade: {minimum:.4f} (mínimo configurado: {args.min_similarity:.4f})")
    if minimum < args.min_similarity:
        print("Resultado: as capturas não parecem ser da mesma pessoa ou têm baixa qualidade.")
        return 1
    print("Resultado: capturas consistentes para cadastro facial.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
