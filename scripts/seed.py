from __future__ import annotations

import sys
from datetime import date, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import (  # noqa: E402
    Reservation,
    ReservationStatus,
    Role,
    Training,
    TrainingStatus,
    User,
)
from app.security import hash_password  # noqa: E402

RH_EMAIL = "rh@lins.com.br"
RH_PASSWORD = "LinsRh@2026"

LEADER_EMAIL = "lider@lins.com.br"
LEADER_PASSWORD = "LinsLider@2026"

INSTRUCTOR_EMAIL = "instrutor@lins.com.br"
INSTRUCTOR_PASSWORD = "LinsInstrutor@2026"

EMPLOYEES = [
    ("Rafael Souza", "rafael@lins.com.br", "Rafael@2026"),
    ("Beatriz Lima", "beatriz@lins.com.br", "Beatriz@2026"),
    ("João Pedro Alves", "joao@lins.com.br", "Joao@2026"),
]


def _get_or_create_user(
    db,
    *,
    name: str,
    email: str,
    password: str,
    role: Role,
    leader_id: int | None = None,
    must_change_password: bool,
) -> tuple[User, bool]:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user, False
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role.value,
        leader_id=leader_id,
        must_change_password=must_change_password,
        face_enrolled=False,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user, True


def _get_or_create_training(
    db,
    *,
    title: str,
    description: str,
    instructor: User,
    created_by: User,
    day: date,
    start: time,
    end: time,
    location: str,
    seats: int,
    hours: float,
) -> tuple[Training, bool]:
    training = db.scalar(
        select(Training).where(
            Training.title == title,
            Training.instructor_id == instructor.id,
        )
    )
    if training:
        return training, False
    training = Training(
        title=title,
        description=description,
        instructor_id=instructor.id,
        date=day,
        start_time=start,
        end_time=end,
        location=location,
        seats=seats,
        workload_hours=hours,
        status=TrainingStatus.AGENDADO.value,
        created_by_id=created_by.id,
    )
    db.add(training)
    db.flush()
    return training, True


def main() -> None:
    init_db()
    db = SessionLocal()
    created_credentials: list[tuple[str, str, str]] = []
    try:
        rh, created = _get_or_create_user(
            db,
            name="Juliana Prado",
            email=RH_EMAIL,
            password=RH_PASSWORD,
            role=Role.RH,
            must_change_password=False,
        )
        if created:
            created_credentials.append((rh.name, rh.email, RH_PASSWORD))

        leader, created = _get_or_create_user(
            db,
            name="Marcos Oliveira",
            email=LEADER_EMAIL,
            password=LEADER_PASSWORD,
            role=Role.LIDER,
            must_change_password=False,
        )
        if created:
            created_credentials.append((leader.name, leader.email, LEADER_PASSWORD))

        instructor, created = _get_or_create_user(
            db,
            name="Carlos Mendes",
            email=INSTRUCTOR_EMAIL,
            password=INSTRUCTOR_PASSWORD,
            role=Role.INSTRUTOR,
            must_change_password=False,
        )
        if created:
            created_credentials.append((instructor.name, instructor.email, INSTRUCTOR_PASSWORD))

        employees: list[User] = []
        for name, email, password in EMPLOYEES:
            employee, created = _get_or_create_user(
                db,
                name=name,
                email=email,
                password=password,
                role=Role.FUNCIONARIO,
                leader_id=leader.id,
                must_change_password=True,
            )
            employees.append(employee)
            if created:
                created_credentials.append((employee.name, employee.email, password))

        today = date.today()
        trainings: list[Training] = []
        training_specs = [
            {
                "title": "NR-12 Segurança em Máquinas",
                "description": "Interpretação da NR-12, riscos em máquinas e dispositivos de proteção.",
                "day": today + timedelta(days=8),
                "start": time(8, 0),
                "end": time(17, 0),
                "location": "Sala 3 · Unidade Lins",
                "seats": 30,
                "hours": 8,
            },
            {
                "title": "Boas Práticas de Fabricação",
                "description": "Higiene, controle de contaminação e boas práticas no ambiente industrial.",
                "day": today + timedelta(days=15),
                "start": time(8, 0),
                "end": time(12, 0),
                "location": "Auditório",
                "seats": 50,
                "hours": 4,
            },
            {
                "title": "Primeiros Socorros",
                "description": "Atendimento inicial, avaliação da cena e acionamento do socorro.",
                "day": today + timedelta(days=22),
                "start": time(13, 0),
                "end": time(17, 0),
                "location": "Sala 1",
                "seats": 20,
                "hours": 4,
            },
        ]
        for spec in training_specs:
            training, _ = _get_or_create_training(
                db,
                title=spec["title"],
                description=spec["description"],
                instructor=instructor,
                created_by=rh,
                day=spec["day"],
                start=spec["start"],
                end=spec["end"],
                location=spec["location"],
                seats=spec["seats"],
                hours=spec["hours"],
            )
            trainings.append(training)

        first_training = trainings[0]
        for employee in employees[:2]:
            reservation = db.scalar(
                select(Reservation).where(
                    Reservation.training_id == first_training.id,
                    Reservation.employee_id == employee.id,
                )
            )
            if not reservation:
                db.add(
                    Reservation(
                        training_id=first_training.id,
                        employee_id=employee.id,
                        created_by_id=leader.id,
                        status=ReservationStatus.ATIVA.value,
                    )
                )

        db.commit()

        print("\nSeed concluido (idempotente).")
        print(f"Banco: {ROOT / 'data' / 'app.db'}")
        print(f"Treinamentos de exemplo: {len(trainings)}; funcionarios de teste: {len(employees)}.")
        if created_credentials:
            print("\nCredenciais criadas neste seed (guarde e troque depois):")
            print(f"{'Perfil':<14} {'Nome':<20} {'E-mail':<24} Senha")
            print("-" * 82)
            for name, email, password in created_credentials:
                print(f"{'':<14} {name:<20} {email:<24} {password}")
            print("\nFuncionarios entram com senha temporaria e devem troca-la no primeiro acesso.")
        else:
            print("Usuarios ja existiam; senhas atuais foram preservadas.")
        print("\nRH: rh@lins.com.br / LinsRh@2026 (se ainda nao alterado)")
        print("Lider: lider@lins.com.br / LinsLider@2026")
        print("Instrutor: instrutor@lins.com.br / LinsInstrutor@2026")
        print("Funcionarios: rafael@, beatriz@, joao@lins.com.br / Rafael@2026, Beatriz@2026, Joao@2026")
        print("A senha temporaria dos funcionarios exige troca no primeiro acesso.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
