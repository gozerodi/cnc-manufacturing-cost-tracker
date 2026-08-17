import decimal
import uuid

import pytest

from app.core.database import get_session
from app.models import Personnel, PersonnelCost
from app.services import personnel_service


@pytest.fixture
def personnel_name():
    return f"Test Staff {uuid.uuid4().hex[:8]}"


def _delete_personnel(personnel_id: int) -> None:
    session = get_session()
    try:
        session.query(PersonnelCost).filter_by(personnel_id=personnel_id).delete()
        session.query(Personnel).filter_by(id=personnel_id).delete()
        session.commit()
    finally:
        session.close()


def test_calculate_hourly_cost_matches_spec_example():
    hourly_cost = personnel_service.calculate_hourly_cost(decimal.Decimal("30000"), 20, 9)
    assert hourly_cost.quantize(decimal.Decimal("0.01")) == decimal.Decimal("166.67")


def test_create_and_list_personnel(personnel_name):
    personnel_id = personnel_service.create_personnel(
        personnel_name, "production", decimal.Decimal("30000"), 20, 9
    )
    try:
        items = personnel_service.list_personnel()
        created = next(item for item in items if item.id == personnel_id)
        assert created.name == personnel_name
        assert created.type == "production"
        assert created.hourly_cost.quantize(decimal.Decimal("0.01")) == decimal.Decimal("166.67")
        assert items[0].id == personnel_id
    finally:
        _delete_personnel(personnel_id)


def test_update_personnel_creates_new_cost_row_keeps_old(personnel_name):
    personnel_id = personnel_service.create_personnel(
        personnel_name, "production", decimal.Decimal("30000"), 20, 9
    )
    try:
        session = get_session()
        try:
            initial_cost_count = (
                session.query(PersonnelCost).filter_by(personnel_id=personnel_id).count()
            )
        finally:
            session.close()
        assert initial_cost_count == 1

        personnel_service.update_personnel(
            personnel_id, personnel_name, "production", decimal.Decimal("36000"), 20, 9
        )

        session = get_session()
        try:
            cost_rows = (
                session.query(PersonnelCost)
                .filter_by(personnel_id=personnel_id)
                .order_by(PersonnelCost.id)
                .all()
            )
        finally:
            session.close()

        assert len(cost_rows) == 2
        assert cost_rows[0].monthly_salary == decimal.Decimal("30000.0000")
        assert cost_rows[1].monthly_salary == decimal.Decimal("36000.0000")

        updated_items = personnel_service.list_personnel()
        updated = next(item for item in updated_items if item.id == personnel_id)
        assert updated.monthly_salary == decimal.Decimal("36000.0000")
    finally:
        _delete_personnel(personnel_id)


def test_soft_delete_hides_personnel_from_list(personnel_name):
    personnel_id = personnel_service.create_personnel(
        personnel_name, "administrative", decimal.Decimal("20000"), 22, 8
    )
    try:
        personnel_service.soft_delete_personnel(personnel_id)
        items = personnel_service.list_personnel()
        assert all(item.id != personnel_id for item in items)
    finally:
        _delete_personnel(personnel_id)


def test_list_personnel_newest_first(personnel_name):
    first_id = personnel_service.create_personnel(
        f"{personnel_name}-1", "production", decimal.Decimal("10000"), 20, 8
    )
    second_id = personnel_service.create_personnel(
        f"{personnel_name}-2", "production", decimal.Decimal("10000"), 20, 8
    )
    try:
        items = personnel_service.list_personnel()
        first_index = next(i for i, item in enumerate(items) if item.id == first_id)
        second_index = next(i for i, item in enumerate(items) if item.id == second_id)
        assert second_index < first_index
    finally:
        _delete_personnel(first_id)
        _delete_personnel(second_id)
