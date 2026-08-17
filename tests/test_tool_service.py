import decimal
import uuid

import pytest

from app.core.database import get_session
from app.models import Tool
from app.services import tool_service


@pytest.fixture
def tool_name():
    return f"Test Tool {uuid.uuid4().hex[:8]}"


def _delete_tool_if_exists(tool_id: int) -> None:
    session = get_session()
    try:
        session.query(Tool).filter_by(id=tool_id).delete()
        session.commit()
    finally:
        session.close()


def test_calculate_price_per_corner_matches_spec_example():
    price_per_corner = tool_service.calculate_price_per_corner(decimal.Decimal("1000"), 4)
    assert price_per_corner == decimal.Decimal("250.0000")


def test_create_update_and_delete_tool(tool_name):
    tool_id = tool_service.create_tool(tool_name, 4, decimal.Decimal("1000"))
    try:
        items = tool_service.list_tools()
        created = next(item for item in items if item.id == tool_id)
        assert created.price_per_corner == decimal.Decimal("250.0000")
        assert items[0].id == tool_id

        tool_service.update_tool(tool_id, tool_name, 5, decimal.Decimal("1000"))
        updated = next(item for item in tool_service.list_tools() if item.id == tool_id)
        assert updated.corner_count == 5
        assert updated.price_per_corner == decimal.Decimal("200.0000")

        tool_service.delete_tool(tool_id)
        remaining = tool_service.list_tools()
        assert all(item.id != tool_id for item in remaining)
    finally:
        _delete_tool_if_exists(tool_id)
