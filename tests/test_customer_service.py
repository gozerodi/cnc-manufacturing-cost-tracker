import uuid

import pytest

from app.core.database import get_session
from app.models import Customer
from app.services import customer_service


@pytest.fixture
def customer_name():
    return f"Test Customer {uuid.uuid4().hex[:8]}"


def _delete_customer(customer_id: int) -> None:
    session = get_session()
    try:
        session.query(Customer).filter_by(id=customer_id).delete()
        session.commit()
    finally:
        session.close()


def test_create_and_list_customer(customer_name):
    customer_id = customer_service.create_customer(customer_name)
    try:
        items = customer_service.list_customers()
        assert any(item.id == customer_id and item.name == customer_name for item in items)
        assert items[0].id == customer_id
    finally:
        _delete_customer(customer_id)


def test_duplicate_customer_name_rejected(customer_name):
    customer_id = customer_service.create_customer(customer_name)
    try:
        with pytest.raises(customer_service.DuplicateCustomerError):
            customer_service.create_customer(customer_name)

        with pytest.raises(customer_service.DuplicateCustomerError):
            customer_service.create_customer(f"  {customer_name}  ")
    finally:
        _delete_customer(customer_id)
