import decimal
import uuid

import pytest
from PySide6.QtWidgets import QMessageBox

from app.core.database import get_session
from app.models import Personnel, PersonnelCost
from app.ui.pages.admin.personnel_page import PersonnelPage


def _delete_personnel(personnel_id: int) -> None:
    session = get_session()
    try:
        session.query(PersonnelCost).filter_by(personnel_id=personnel_id).delete()
        session.query(Personnel).filter_by(id=personnel_id).delete()
        session.commit()
    finally:
        session.close()


def test_add_edit_delete_personnel_via_page(qapp, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    page = PersonnelPage()
    name = f"Page Test {uuid.uuid4().hex[:8]}"

    page.name_input.setText(name)
    page.type_combo.setCurrentText("Production")
    page.salary_input.setText("30,000")
    page.days_input.setValue(20)
    page.hours_input.setValue(9)

    assert page.hourly_cost_label.text() == "$166.67"

    page._on_submit()

    assert page.table.row_count() >= 1
    first_row_name = page.table.model.item(0, 0).text()
    assert first_row_name == name
    assert page.table.model.item(0, 5).text() == "$166.67"

    personnel_id = page._items[0].id
    try:
        page._on_edit_requested(0)
        assert page.name_input.text() == name
        assert page.submit_button.text() == "Update"

        page.salary_input.setText("36,000")
        page._on_submit()

        updated_row_index = next(
            i for i, item in enumerate(page._items) if item.id == personnel_id
        )
        assert page.table.model.item(updated_row_index, 2).text() == "$36,000.00"

        page._on_delete_requested(updated_row_index)
        assert all(item.id != personnel_id for item in page._items)
    finally:
        _delete_personnel(personnel_id)
