from __future__ import annotations

import enum
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(str, enum.Enum):
    RH = "rh"
    LIDER = "lider"
    INSTRUTOR = "instrutor"
    FUNCIONARIO = "funcionario"


class TrainingStatus(str, enum.Enum):
    AGENDADO = "agendado"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class ReservationStatus(str, enum.Enum):
    ATIVA = "ativa"
    CANCELADA = "cancelada"


class AttendanceMethod(str, enum.Enum):
    FACE = "face"
    MANUAL = "manual"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    leader_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    face_enrolled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    leader: Mapped[User | None] = relationship(remote_side=[id], back_populates="team")
    team: Mapped[list[User]] = relationship(back_populates="leader")

    embeddings: Mapped[list[FaceEmbedding]] = relationship(back_populates="user", cascade="all, delete-orphan")
    consents: Mapped[list[FaceConsent]] = relationship(back_populates="user", cascade="all, delete-orphan")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), default="buffalo_l", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="embeddings")


class FaceConsent(Base):
    __tablename__ = "face_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    term_version: Mapped[str] = mapped_column(String(20), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship(back_populates="consents")


class Training(Base):
    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    workload_hours: Mapped[float] = mapped_column(Float, default=8, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=TrainingStatus.AGENDADO.value, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    instructor: Mapped[User] = relationship(foreign_keys=[instructor_id])
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    reservations: Mapped[list[Reservation]] = relationship(back_populates="training", cascade="all, delete-orphan")
    attendances: Mapped[list[Attendance]] = relationship(back_populates="training", cascade="all, delete-orphan")
    certificates: Mapped[list[Certificate]] = relationship(back_populates="training", cascade="all, delete-orphan")


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (UniqueConstraint("training_id", "employee_id", name="uq_reservation_training_employee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ReservationStatus.ATIVA.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    training: Mapped[Training] = relationship(back_populates="reservations")
    employee: Mapped[User] = relationship(foreign_keys=[employee_id])
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("training_id", "employee_id", name="uq_attendance_training_employee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    training: Mapped[Training] = relationship(back_populates="attendances")
    employee: Mapped[User] = relationship(foreign_keys=[employee_id])
    instructor: Mapped[User] = relationship(foreign_keys=[instructor_id])


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("training_id", "employee_id", name="uq_certificate_training_employee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    training: Mapped[Training] = relationship(back_populates="certificates")
    employee: Mapped[User] = relationship()


class OutboxEmail(Base):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
