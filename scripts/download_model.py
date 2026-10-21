from __future__ import annotations

import sys
import time
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402

MODEL_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
EXPECTED_FILES = [
    "1k3d68.onnx",
    "2d106det.onnx",
    "det_10g.onnx",
    "genderage.onnx",
    "w600k_r50.onnx",
]


def main() -> None:
    settings = get_settings()
    model_dir = settings.model_root_path / "models" / "buffalo_l"
    if all((model_dir / name).is_file() for name in EXPECTED_FILES):
        total = sum((model_dir / name).stat().st_size for name in EXPECTED_FILES)
        print(f"Modelo buffalo_l ja presente em {model_dir} ({total / (1024 * 1024):.1f} MB).")
        return

    model_dir.mkdir(parents=True, exist_ok=True)
    zip_path = settings.model_root_path / "buffalo_l.zip"
    settings.model_root_path.mkdir(parents=True, exist_ok=True)

    print("Baixando modelo buffalo_l (SCRFD + ArcFace, ~280 MB)...")
    started = time.time()
    with requests.get(MODEL_URL, stream=True, timeout=(20, 120), headers={"User-Agent": "trilha-de-talentos/1.0"}) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        last_report = 0.0
        with zip_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                if total and time.time() - last_report > 2:
                    percent = downloaded * 100 / total
                    print(f"  {percent:5.1f}% ({downloaded / (1024 * 1024):.0f} MB de {total / (1024 * 1024):.0f} MB)", flush=True)
                    last_report = time.time()

    print("Extraindo arquivos ONNX...")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(model_dir)

    missing = [name for name in EXPECTED_FILES if not (model_dir / name).is_file()]
    if missing:
        raise SystemExit(
            "Download incompleto. Arquivos ausentes: " + ", ".join(missing) + ". Apague data/insightface/buffalo_l.zip e tente novamente."
        )

    try:
        zip_path.unlink()
    except OSError:
        pass
    print(f"Modelo pronto em {model_dir} em {time.time() - started:.0f}s.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"Erro de rede ao baixar o modelo: {exc}", file=sys.stderr)
        raise SystemExit(1)
