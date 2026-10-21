from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, Training, User
from app.services.certificate_pdf import build_certificate_pdf, build_qr_png, verification_url

router = APIRouter(prefix="/api/certificates", tags=["certificados"])

NOT_FOUND = "Certificado não encontrado. Confira o código informado."


def _certificate_row(db: Session, code: str) -> tuple[Certificate, Training, User]:
    normalized = code.strip().upper()
    row = db.execute(
        select(Certificate, Training, User)
        .join(Training, Training.id == Certificate.training_id)
        .join(User, User.id == Certificate.employee_id)
        .where(Certificate.verification_code == normalized)
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return row[0], row[1], row[2]


@router.get("/verify/{code}")
def verify_certificate(code: str, db: Session = Depends(get_db)) -> dict:
    certificate, training, employee = _certificate_row(db, code)
    return {
        "valid": True,
        "holder_name": employee.name,
        "training_title": training.title,
        "training_date": training.date.isoformat(),
        "workload_hours": training.workload_hours,
        "code": certificate.verification_code,
        "issued_at": certificate.issued_at.isoformat(),
    }


@router.get("/verify/{code}/pdf")
def download_certificate_pdf(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    certificate, training, employee = _certificate_row(db, code)
    content = build_certificate_pdf(
        certificate,
        training,
        employee,
        verify_url=verification_url(request, certificate.verification_code),
    )
    filename = f"certificado-{certificate.verification_code}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/verify/{code}/qr.png")
def certificate_qr(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    certificate, _training, _employee = _certificate_row(db, code)
    content = build_qr_png(verification_url(request, certificate.verification_code))
    filename = f"qr-{certificate.verification_code}.png"
    return Response(
        content=content,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
