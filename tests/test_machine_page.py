import uuid

from PySide6.QtWidgets import QMessageBox

from app.core.database import get_session
from app.models import Machine, MachineCost
from app.ui.pages.admin.machine_page import MachinePage


def _delete_machine(machine_id: int) -> None:
    session = get_session()
    try:
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.commit()
    finally:
        session.close()


def test_add_edit_delete_machine_via_page(qapp, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    page = MachinePage()
    name = f"Page Machine {uuid.uuid4().hex[:8]}"

    page.name_input.setText(name)
    page.hourly_cost_input.setText("300")
    page._on_submit()

    assert page.table.model.item(0, 0).text() == name
    assert page.table.model.item(0, 1).text() == "$300.00"

    machine_id = page._items[0].id
    try:
        page._on_edit_requested(0)
        assert page.submit_button.text() == "Update"

        page.hourly_cost_input.setText("350")
        page._on_submit()

        row_index = next(i for i, item in enumerate(page._items) if item.id == machine_id)
        assert page.table.model.item(row_index, 1).text() == "$350.00"

        page._on_delete_requested(row_index)
        assert all(item.id != machine_id for item in page._items)
    finally:
        _delete_machine(machine_id)
