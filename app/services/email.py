from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Certificate, OutboxEmail, Training, User

logger = logging.getLogger("trilha.email")
settings = get_settings()


def site_url(request: Request) -> str:
    if settings.public_base_url.strip():
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def queue_email(db: Session, *, recipient: str, subject: str, body: str) -> OutboxEmail:
    email = OutboxEmail(recipient=recipient, subject=subject, body=body)
    db.add(email)
    db.flush()

    if settings.smtp_host.strip():
        try:
            _send_smtp(recipient, subject, body)
            email.sent = True
            email.error = None
        except (OSError, smtplib.SMTPException) as exc:
            email.sent = False
            email.error = f"Falha no envio: {exc}"[:2000]
            logger.warning("Falha ao enviar e-mail id=%s: %s", email.id, exc)

    return email


def _send_smtp(recipient: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.ehlo()
        if settings.smtp_use_tls:
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def _training_when(training: Training) -> str:
    return (
        f"{training.date.strftime('%d/%m/%Y')}, das "
        f"{training.start_time.strftime('%H:%M')} às {training.end_time.strftime('%H:%M')}"
    )


def queue_account_created_email(
    db: Session,
    *,
    user: User,
    temporary_password: str,
    base_url: str,
) -> OutboxEmail:
    body = (
        f"Olá, {user.name}!\n\n"
        "Seu acesso ao Trilha de Talentos foi criado.\n\n"
        f"E-mail: {user.email}\n"
        f"Senha temporária: {temporary_password}\n\n"
        f"Acesse {base_url} e altere a senha no primeiro acesso.\n"
        "Se você não reconhece este cadastro, procure o RH.\n\n"
        "Universidade Lins"
    )
    return queue_email(
        db,
        recipient=user.email,
        subject="Seu acesso ao Trilha de Talentos",
        body=body,
    )


def queue_password_reset_email(
    db: Session,
    *,
    user: User,
    temporary_password: str,
    base_url: str,
) -> OutboxEmail:
    body = (
        f"Olá, {user.name}!\n\n"
        "O RH gerou uma nova senha temporária para sua conta.\n\n"
        f"E-mail: {user.email}\n"
        f"Senha temporária: {temporary_password}\n\n"
        f"Acesse {base_url} e cadastre uma senha pessoal.\n"
        "Se você não solicitou esta alteração, procure o RH imediatamente.\n\n"
        "Universidade Lins"
    )
    return queue_email(
        db,
        recipient=user.email,
        subject="Nova senha temporária - Trilha de Talentos",
        body=body,
    )


def queue_reservation_confirmed_email(
    db: Session,
    *,
    user: User,
    training: Training,
    reserved_by: User,
    base_url: str,
) -> OutboxEmail:
    body = (
        f"Olá, {user.name}!\n\n"
        f"Sua vaga foi reservada por {reserved_by.name}.\n\n"
        f"Treinamento: {training.title}\n"
        f"Quando: {_training_when(training)}\n"
        f"Local: {training.location}\n"
        f"Instrutor: {training.instructor.name if training.instructor else 'A definir'}\n"
        f"Carga horária: {training.workload_hours:g}h\n\n"
        f"Consulte seus treinamentos em {base_url}.\n\n"
        "Universidade Lins"
    )
    return queue_email(
        db,
        recipient=user.email,
        subject=f"Reserva confirmada: {training.title}",
        body=body,
    )


def queue_reservation_cancelled_email(
    db: Session,
    *,
    user: User,
    training: Training,
    cancelled_by: User,
) -> OutboxEmail:
    body = (
        f"Olá, {user.name}!\n\n"
        f"Sua reserva foi cancelada por {cancelled_by.name}.\n\n"
        f"Treinamento: {training.title}\n"
        f"Quando: {_training_when(training)}\n"
        f"Local: {training.location}\n\n"
        "Se houver dúvidas, procure seu líder ou o RH.\n\n"
        "Universidade Lins"
    )
    return queue_email(
        db,
        recipient=user.email,
        subject=f"Reserva cancelada: {training.title}",
        body=body,
    )


def queue_training_cancelled_email(
    db: Session,
    *,
    user: User,
    training: Training,
    reason: str | None,
) -> OutboxEmail:
    reason_line = f"Motivo informado: {reason}\n\n" if reason else ""
    body = (
        f"Olá, {user.name}!\n\n"
        f"O treinamento abaixo foi cancelado pelo RH.\n\n"
        f"Treinamento: {training.title}\n"
        f"Quando: {_training_when(training)}\n"
        f"Local: {training.location}\n\n"
        f"{reason_line}"
        "Sua reserva foi cancelada automaticamente.\n\n"
        "Universidade Lins"
    )
    return queue_email(
        db,
        recipient=user.email,
        subject=f"Treinamento cancelado: {training.title}",
        body=body,
    )


def queue_certificate_issued_email(
    db: Session,
    *,
    user: User,
    training: Training,
    certificate: Certificate,
    base_url: str,
) -> OutboxEmail:
    verify_url = f"{base_url.rstrip('/')}/verificar/{certificate.verification_code}"
    pdf_url = (
        f"{base_url.rstrip('/')}/api/certificates/verify/"
        f"{certificate.verification_code}/pdf"
    )
    body = (
        f"Olá, {user.name}!\n\n"
        f"Seu certificado do treinamento abaixo foi emitido.\n\n"
        f"Treinamento: {training.title}\n"
        f"Quando: {_training_when(training)}\n"
        f"Local: {training.location}\n"
        f"Carga horária: {training.workload_hours:g}h\n"
        f"Código de verificação: {certificate.verification_code}\n\n"
        f"Baixe o PDF em {pdf_url}.\n"
        f"Consulte a autenticidade em {verify_url}.\n\n"
        "Universidade Lins"
    )
    return queue_email(
        db,
        recipient=user.email,
        subject=f"Certificado emitido: {training.title}",
        body=body,
    )
