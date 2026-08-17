from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Machine


def create(session: Session, name: str) -> Machine:
    machine = Machine(name=name, is_active=True)
    session.add(machine)
    session.flush()
    return machine


def get_by_id(session: Session, machine_id: int) -> Machine | None:
    return session.get(Machine, machine_id)


def list_active(session: Session) -> list[Machine]:
    stmt = (
        select(Machine)
        .where(Machine.is_active.is_(True))
        .order_by(Machine.created_at.desc(), Machine.id.desc())
    )
    return list(session.scalars(stmt))


def update_name(session: Session, machine_id: int, name: str) -> Machine:
    machine = session.get(Machine, machine_id)
    machine.name = name
    return machine


def soft_delete(session: Session, machine_id: int) -> None:
    machine = session.get(Machine, machine_id)
    machine.is_active = False
