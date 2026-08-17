import decimal
import uuid

import pytest

from app.core.database import get_session
from app.models import Machine, MachineCost
from app.services import machine_service


@pytest.fixture
def machine_name():
    return f"Test Machine {uuid.uuid4().hex[:8]}"


def _delete_machine(machine_id: int) -> None:
    session = get_session()
    try:
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.commit()
    finally:
        session.close()


def test_create_and_list_machine(machine_name):
    machine_id = machine_service.create_machine(machine_name, decimal.Decimal("300"))
    try:
        items = machine_service.list_machines()
        created = next(item for item in items if item.id == machine_id)
        assert created.name == machine_name
        assert created.hourly_cost == decimal.Decimal("300.0000")
        assert items[0].id == machine_id
    finally:
        _delete_machine(machine_id)


def test_update_machine_creates_new_cost_row_keeps_old(machine_name):
    machine_id = machine_service.create_machine(machine_name, decimal.Decimal("300"))
    try:
        machine_service.update_machine(machine_id, machine_name, decimal.Decimal("350"))

        session = get_session()
        try:
            cost_rows = (
                session.query(MachineCost)
                .filter_by(machine_id=machine_id)
                .order_by(MachineCost.id)
                .all()
            )
        finally:
            session.close()

        assert len(cost_rows) == 2
        assert cost_rows[0].hourly_cost == decimal.Decimal("300.0000")
        assert cost_rows[1].hourly_cost == decimal.Decimal("350.0000")

        updated = next(
            item for item in machine_service.list_machines() if item.id == machine_id
        )
        assert updated.hourly_cost == decimal.Decimal("350.0000")
    finally:
        _delete_machine(machine_id)


def test_soft_delete_hides_machine_from_list(machine_name):
    machine_id = machine_service.create_machine(machine_name, decimal.Decimal("100"))
    try:
        machine_service.soft_delete_machine(machine_id)
        items = machine_service.list_machines()
        assert all(item.id != machine_id for item in items)
    finally:
        _delete_machine(machine_id)
