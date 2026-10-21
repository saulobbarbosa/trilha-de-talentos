from __future__ import annotations

import ipaddress
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography import x509  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from cryptography.x509.oid import NameOID  # noqa: E402

from app.config import get_settings  # noqa: E402
from scripts.net_utils import get_lan_ip  # noqa: E402


def main(force: bool = False) -> None:
    settings = get_settings()
    cert_path = settings.https_cert_path
    key_path = settings.https_key_path
    if cert_path.exists() and key_path.exists() and not force:
        print(f"Certificado HTTPS ja existe em {cert_path}")
        return

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    lan_ip = get_lan_ip()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Trilha de Talentos (local)"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Trilha de Talentos"),
        ]
    )
    san_entries: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]
    try:
        san_entries.append(x509.IPAddress(ipaddress.ip_address(lan_ip)))
    except ValueError:
        pass

    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))

    print(f"Certificado HTTPS gerado para localhost e {lan_ip}:")
    print(f"  Certificado: {cert_path}")
    print(f"  Chave:       {key_path}")
    print("No celular, instale/confie no certificado ou aceite o aviso do navegador.")
    print("Inicie com: start.bat --https")


if __name__ == "__main__":
    try:
        main(force="--force" in sys.argv)
    except Exception as exc:
        print(f"Erro ao gerar certificado: {exc}", file=sys.stderr)
        raise SystemExit(1)
