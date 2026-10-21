from __future__ import annotations

from datetime import date
from io import BytesIO
from types import SimpleNamespace

from PIL import Image
from sqlalchemy import select

from app.database import SessionLocal
from app.models import OutboxEmail, TrainingStatus
from app.services.certification import completion_state
from tests.test_milestone_5_api import _complete, _create_completion_data, _login_instructor


def _issue_certificate(client) -> tuple[dict, str]:
    data = _create_completion_data()
    _login_instructor(client)
    response = _complete(client, data["training_id"])
    assert response.status_code == 200, response.text
    certificates = response.json()["certificates"]
    assert len(certificates) == 1
    return data, certificates[0]["code"]


def test_public_pdf_and_qr_download(client):
    data, code = _issue_certificate(client)
    client.cookies.clear()

    verification = client.get(f"/api/certificates/verify/{code.lower()}")
    assert verification.status_code == 200, verification.text
    assert verification.json()["code"] == code

    pdf = client.get(f"/api/certificates/verify/{code.lower()}/pdf")
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF-")
    assert len(pdf.content) > 5000
    assert code in pdf.headers["content-disposition"]
    assert "attachment" in pdf.headers["content-disposition"]

    qr = client.get(f"/api/certificates/verify/{code}/qr.png")
    assert qr.status_code == 200, qr.text
    assert qr.headers["content-type"].startswith("image/png")
    assert qr.content.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(BytesIO(qr.content))
    assert image.format == "PNG"
    assert image.width >= 150
    assert image.height == image.width

    db = SessionLocal()
    try:
        outbox = db.scalar(
            select(OutboxEmail).where(
                OutboxEmail.recipient == data["present_email"],
                OutboxEmail.subject.like("Certificado emitido:%"),
            )
        )
        assert outbox is not None
        assert f"/api/certificates/verify/{code}/pdf" in outbox.body
    finally:
        db.close()


def test_certificate_assets_return_404_for_unknown_code(client):
    for suffix in ("/pdf", "/qr.png"):
        response = client.get(f"/api/certificates/verify/LINS-AAAAA-AAAAA-AAAAA{suffix}")
        assert response.status_code == 404
        assert "não encontrado" in response.json()["detail"]


def test_completion_warning_pluralization():
    training = SimpleNamespace(
        status=TrainingStatus.AGENDADO.value,
        date=date.today(),
        completed_at=None,
    )

    plural = completion_state(
        training,
        [
            (SimpleNamespace(name="A"), None, None),
            (SimpleNamespace(name="B"), None, None),
            (SimpleNamespace(name="C"), object(), None),
        ],
    )
    assert "2 participantes sem presença não receberão certificado." in plural["warnings"]

    singular = completion_state(
        training,
        [
            (SimpleNamespace(name="A"), None, None),
            (SimpleNamespace(name="B"), object(), None),
        ],
    )
    assert "1 participante sem presença não receberá certificado." in singular["warnings"]
