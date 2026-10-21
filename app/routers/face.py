from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_onboarded_user
from app.models import FaceConsent, FaceEmbedding, User
from app.security import client_ip, require_csrf
from app.services.audit import log_action
from app.services.face import (
    MODEL_NAME,
    MODEL_PROVIDER,
    FaceServiceError,
    cosine_similarity,
    get_face_service,
    vector_from_bytes,
)
from app.services.face_consent import (
    FACE_CONSENT_VERSION,
    consent_term_payload,
)

router = APIRouter(prefix="/api/face", tags=["reconhecimento-facial"])
settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
GENERIC_CONTENT_TYPES = {"", "application/octet-stream"}


class ConsentRequest(BaseModel):
    term_version: str = Field(min_length=1, max_length=20)
    accepted: bool

    @field_validator("term_version")
    @classmethod
    def _trim_version(cls, value: str) -> str:
        return value.strip()


def _current_consent(db: Session, user_id: int) -> FaceConsent | None:
    return db.scalar(
        select(FaceConsent)
        .where(
            FaceConsent.user_id == user_id,
            FaceConsent.term_version == FACE_CONSENT_VERSION,
        )
        .order_by(FaceConsent.accepted_at.desc(), FaceConsent.id.desc())
        .limit(1)
    )


def _iso_utc(value: datetime | None) -> str | None:
    return f"{value.isoformat()}Z" if value else None


def _embedding_count(db: Session, user_id: int) -> int:
    return (
        db.scalar(
            select(func.count(FaceEmbedding.id)).where(FaceEmbedding.user_id == user_id)
        )
        or 0
    )


def _status_payload(db: Session, user: User) -> dict:
    consent = _current_consent(db, user.id)
    samples = _embedding_count(db, user.id)
    required = settings.face_enroll_samples
    service = get_face_service()
    return {
        "term": {
            "current_version": FACE_CONSENT_VERSION,
            "accepted": consent is not None,
            "accepted_at": _iso_utc(consent.accepted_at if consent else None),
            "needs_acceptance": consent is None,
        },
        "enrollment": {
            "samples": samples,
            "required": required,
            "complete": samples >= required,
            "can_capture": consent is not None and samples < required,
        },
        "model": {
            "name": MODEL_NAME,
            "provider": MODEL_PROVIDER,
            "preload": settings.face_model_preload,
            "loaded": service.loaded,
        },
    }


@router.get("/term")
def consent_term(_: User = Depends(get_onboarded_user)) -> dict:
    return consent_term_payload()


@router.get("/status")
def face_status(
    user: User = Depends(get_onboarded_user),
    db: Session = Depends(get_db),
) -> dict:
    return _status_payload(db, user)


@router.post("/consent")
def accept_consent(
    payload: ConsentRequest,
    request: Request,
    user: User = Depends(get_onboarded_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    if not payload.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O consentimento só pode ser registrado com a opção de aceite.",
        )
    if payload.term_version != FACE_CONSENT_VERSION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O termo de consentimento foi atualizado. Recarregue a página e leia a nova versão.",
        )

    existing = _current_consent(db, user.id)
    if existing is None:
        consent = FaceConsent(
            user_id=user.id,
            term_version=FACE_CONSENT_VERSION,
            ip_address=client_ip(request),
        )
        db.add(consent)
        log_action(
            db,
            actor_id=user.id,
            action="consentimento_facial_aceito",
            entity="face_consent",
            entity_id=user.id,
            details={"term_version": FACE_CONSENT_VERSION},
            ip_address=client_ip(request),
        )
        db.commit()

    return {"status": _status_payload(db, user)}


@router.delete("/consent")
def revoke_consent(
    request: Request,
    user: User = Depends(get_onboarded_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    embeddings_removed = _embedding_count(db, user.id)
    consents_removed = (
        db.scalar(select(func.count(FaceConsent.id)).where(FaceConsent.user_id == user.id))
        or 0
    )
    db.execute(delete(FaceEmbedding).where(FaceEmbedding.user_id == user.id))
    db.execute(delete(FaceConsent).where(FaceConsent.user_id == user.id))
    user.face_enrolled = False
    log_action(
        db,
        actor_id=user.id,
        action="consentimento_facial_revogado",
        entity="face_consent",
        entity_id=user.id,
        details={
            "term_version": FACE_CONSENT_VERSION,
            "embeddings_removed": embeddings_removed,
            "consents_removed": consents_removed,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    return {
        "status": _status_payload(db, user),
        "embeddings_removed": embeddings_removed,
        "consents_removed": consents_removed,
    }


@router.delete("/enrollment")
def reset_enrollment(
    request: Request,
    user: User = Depends(get_onboarded_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    embeddings_removed = _embedding_count(db, user.id)
    db.execute(delete(FaceEmbedding).where(FaceEmbedding.user_id == user.id))
    user.face_enrolled = False
    log_action(
        db,
        actor_id=user.id,
        action="cadastro_facial_reiniciado",
        entity="user",
        entity_id=user.id,
        details={"embeddings_removed": embeddings_removed},
        ip_address=client_ip(request),
    )
    db.commit()
    return {"status": _status_payload(db, user), "embeddings_removed": embeddings_removed}


@router.post("/enrollment/samples", status_code=status.HTTP_201_CREATED)
def add_enrollment_sample(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_onboarded_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> dict:
    if _current_consent(db, user.id) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aceite o termo de consentimento antes de cadastrar o rosto.",
        )

    required = settings.face_enroll_samples
    samples = _embedding_count(db, user.id)
    if samples >= required:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seu cadastro facial já está concluído. Use a opção de refazer o cadastro para capturar novamente.",
        )

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES and content_type not in GENERIC_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Envie uma imagem JPG, PNG ou WebP.",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    raw = file.file.read(max_bytes + 1)
    file.file.close()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A imagem enviada está vazia.",
        )
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"A imagem deve ter no máximo {settings.max_upload_mb} MB.",
        )

    service = get_face_service()
    try:
        sample = service.analyze(raw)
    except FaceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    existing = db.scalars(
        select(FaceEmbedding)
        .where(FaceEmbedding.user_id == user.id)
        .order_by(FaceEmbedding.id)
    ).all()
    best_similarity = -1.0
    for stored in existing:
        try:
            stored_vector = vector_from_bytes(stored.vector)
        except ValueError:
            continue
        best_similarity = max(best_similarity, cosine_similarity(sample.embedding, stored_vector))

    if existing and best_similarity < settings.face_enroll_min_similarity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Esta captura não parece ser da mesma pessoa das anteriores. Refaça o cadastro com uma sequência consistente.",
        )

    next_count = samples + 1
    db.add(
        FaceEmbedding(
            user_id=user.id,
            vector=sample.embedding.astype("float32", copy=False).tobytes(),
            model_name=sample.model_name,
        )
    )
    enrollment_complete = next_count >= required
    if enrollment_complete:
        user.face_enrolled = True

    log_action(
        db,
        actor_id=user.id,
        action="amostra_facial_cadastrada",
        entity="face_embedding",
        entity_id=user.id,
        details={
            "sample": next_count,
            "quality": sample.quality,
            "detection_score": sample.detection_score,
            "model_name": sample.model_name,
        },
        ip_address=client_ip(request),
    )
    if enrollment_complete:
        log_action(
            db,
            actor_id=user.id,
            action="cadastro_facial_concluido",
            entity="user",
            entity_id=user.id,
            details={"samples": next_count, "model_name": sample.model_name},
            ip_address=client_ip(request),
        )
    db.commit()

    message = (
        "Cadastro facial concluído com sucesso."
        if enrollment_complete
        else f"Captura {next_count} de {required} validada. Continue seguindo as orientações."
    )
    return {
        "status": _status_payload(db, user),
        "sample": {
            "index": next_count,
            "quality": sample.quality,
            "message": message,
        },
    }
