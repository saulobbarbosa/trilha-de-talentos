from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402

from app.config import get_settings  # noqa: E402
from scripts.net_utils import get_lan_ip  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicia o Trilha de Talentos na rede local.")
    parser.add_argument("--https", action="store_true", help="Usa o certificado HTTPS local autoassinado.")
    parser.add_argument("--port", type=int, default=None, help="Porta HTTP/HTTPS.")
    parser.add_argument("--host", default=None, help="Endereco de escuta.")
    args = parser.parse_args()

    settings = get_settings()
    port = args.port or settings.app_port
    host = args.host or settings.app_host
    use_https = args.https or settings.use_https
    lan_ip = get_lan_ip()
    scheme = "https" if use_https else "http"

    dist_index = ROOT / "dist" / "index.html"
    if not dist_index.is_file():
        print("AVISO: frontend nao compilado. Execute setup.bat ou: npm install && npm run build")

    ssl_certfile = None
    ssl_keyfile = None
    if use_https:
        cert = settings.https_cert_path
        key = settings.https_key_path
        if not cert.exists() or not key.exists():
            print("Certificado HTTPS ausente. Gerando certificado local...")
            from scripts.make_cert import main as make_certificate

            make_certificate()
        ssl_certfile = str(cert)
        ssl_keyfile = str(key)

    print()
    print("=" * 68)
    print("  TRILHA DE TALENTOS - servidor local")
    print("=" * 68)
    print(f"  Neste computador : {scheme}://127.0.0.1:{port}")
    print(f"  Celular (Wi-Fi)  : {scheme}://{lan_ip}:{port}")
    print()
    print("  O celular precisa estar na MESMA rede Wi-Fi deste computador.")
    print("  Se nao abrir no celular, libere a porta no Firewall do Windows")
    print(f"  (executar como Administrador):")
    print(f'    netsh advfirewall firewall add rule name="Trilha de Talentos {port}" dir=in action=allow protocol=TCP localport={port}')
    if use_https:
        print()
        print("  HTTPS autoassinado: o celular mostrara um aviso de seguranca.")
        print("  Aceite/confie no certificado para liberar a camera ao vivo.")
    print("  Pressione Ctrl+C para encerrar.")
    print("=" * 68)
    print()

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        log_level="info",
    )


if __name__ == "__main__":
    main()
