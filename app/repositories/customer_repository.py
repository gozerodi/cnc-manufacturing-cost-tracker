from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer


def create(session: Session, name: str) -> Customer:
    customer = Customer(name=name)
    session.add(customer)
    session.flush()
    return customer


def get_by_name(session: Session, name: str) -> Customer | None:
    stmt = select(Customer).where(Customer.name == name)
    return session.scalars(stmt).first()


def list_all(session: Session) -> list[Customer]:
    stmt = select(Customer).order_by(Customer.created_at.desc(), Customer.id.desc())
    return list(session.scalars(stmt))
