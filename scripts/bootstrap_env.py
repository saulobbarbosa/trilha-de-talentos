from __future__ import annotations

import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
EXAMPLE_PATH = ROOT / ".env.example"


def main() -> None:
    if not EXAMPLE_PATH.exists():
        raise SystemExit("Arquivo .env.example nao encontrado.")

    if ENV_PATH.exists():
        content = ENV_PATH.read_text(encoding="utf-8")
        if "TROCAR_POR_CHAVE_ALEATORIA" in content or "SECRET_KEY=" not in content:
            content = _replace_secret_key(content)
            ENV_PATH.write_text(content, encoding="utf-8")
            print(".env atualizado com uma SECRET_KEY aleatoria.")
        else:
            print(".env ja existe; mantido sem alteracoes.")
    else:
        content = EXAMPLE_PATH.read_text(encoding="utf-8")
        content = _replace_secret_key(content)
        ENV_PATH.write_text(content, encoding="utf-8")
        print(".env criado a partir de .env.example.")

    for directory in [
        ROOT / "data",
        ROOT / "data" / "certificates",
        ROOT / "data" / "certs",
        ROOT / "data" / "insightface",
        ROOT / "imagens_teste" / "pessoa1",
        ROOT / "imagens_teste" / "pessoa2",
        ROOT / "imagens_teste" / "pessoa3",
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    print("Pastas locais verificadas.")


def _replace_secret_key(content: str) -> str:
    key = secrets.token_urlsafe(48)
    lines = []
    replaced = False
    for line in content.splitlines():
        if line.startswith("SECRET_KEY="):
            lines.append(f"SECRET_KEY={key}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(f"SECRET_KEY={key}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Erro ao preparar .env: {exc}", file=sys.stderr)
        raise SystemExit(1)
