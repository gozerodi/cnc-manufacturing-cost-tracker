import uuid

from PySide6.QtWidgets import QMessageBox

from app.core.database import get_session
from app.models import Tool
from app.ui.pages.admin.tool_page import ToolPage


def _delete_tool_if_exists(tool_id: int) -> None:
    session = get_session()
    try:
        session.query(Tool).filter_by(id=tool_id).delete()
        session.commit()
    finally:
        session.close()


def test_add_edit_delete_tool_via_page(qapp, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    page = ToolPage()
    name = f"Page Tool {uuid.uuid4().hex[:8]}"

    page.name_input.setText(name)
    page.corner_count_input.setValue(4)
    page.price_input.setText("1000")

    assert page.price_per_corner_label.text() == "$250.00"

    page._on_submit()

    assert page.table.model.item(0, 0).text() == name
    assert page.table.model.item(0, 3).text() == "$250.00"

    tool_id = page._items[0].id
    try:
        page._on_edit_requested(0)
        page.corner_count_input.setValue(5)
        page._on_submit()

        row_index = next(i for i, item in enumerate(page._items) if item.id == tool_id)
        assert page.table.model.item(row_index, 3).text() == "$200.00"

        page._on_delete_requested(row_index)
        assert all(item.id != tool_id for item in page._items)
        tool_id = None
    finally:
        if tool_id is not None:
            _delete_tool_if_exists(tool_id)
