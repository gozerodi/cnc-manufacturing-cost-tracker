import dataclasses

from sqlalchemy.exc import IntegrityError

from app.core.database import get_session
from app.repositories import customer_repository


class DuplicateCustomerError(Exception):
    pass


@dataclasses.dataclass
class CustomerListItem:
    id: int
    name: str


def create_customer(name: str) -> int:
    trimmed_name = name.strip()
    session = get_session()
    try:
        if customer_repository.get_by_name(session, trimmed_name) is not None:
            raise DuplicateCustomerError(f"'{trimmed_name}' already exists.")
        try:
            customer = customer_repository.create(session, trimmed_name)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise DuplicateCustomerError(f"'{trimmed_name}' already exists.")
        return customer.id
    finally:
        session.close()


def list_customers() -> list[CustomerListItem]:
    session = get_session()
    try:
        customers = customer_repository.list_all(session)
        return [CustomerListItem(id=customer.id, name=customer.name) for customer in customers]
    finally:
        session.close()
