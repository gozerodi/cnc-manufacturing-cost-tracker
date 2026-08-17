from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Personnel


def create(session: Session, name: str, type_: str) -> Personnel:
    personnel = Personnel(name=name, type=type_, is_active=True)
    session.add(personnel)
    session.flush()
    return personnel


def get_by_id(session: Session, personnel_id: int) -> Personnel | None:
    return session.get(Personnel, personnel_id)


def list_active(session: Session) -> list[Personnel]:
    stmt = (
        select(Personnel)
        .where(Personnel.is_active.is_(True))
        .order_by(Personnel.created_at.desc(), Personnel.id.desc())
    )
    return list(session.scalars(stmt))


def update_basic_info(session: Session, personnel_id: int, name: str, type_: str) -> Personnel:
    personnel = session.get(Personnel, personnel_id)
    personnel.name = name
    personnel.type = type_
    return personnel


def soft_delete(session: Session, personnel_id: int) -> None:
    personnel = session.get(Personnel, personnel_id)
    personnel.is_active = False
