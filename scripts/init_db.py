from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.database import init_db  # noqa: E402


def main() -> None:
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    init_db()
    print(f"Banco inicializado: {settings.database_path}")


if __name__ == "__main__":
    main()
