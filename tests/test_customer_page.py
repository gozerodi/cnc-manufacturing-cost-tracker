import uuid

from PySide6.QtWidgets import QMessageBox

from app.core.database import get_session
from app.models import Customer
from app.ui.pages.staff.customer_page import CustomerPage


def _delete_customer(customer_id: int) -> None:
    session = get_session()
    try:
        session.query(Customer).filter_by(id=customer_id).delete()
        session.commit()
    finally:
        session.close()


def test_add_customer_and_reject_duplicate_via_page(qapp, monkeypatch):
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a))
    )

    page = CustomerPage()
    name = f"Page Customer {uuid.uuid4().hex[:8]}"

    page.name_input.setText(name)
    page._on_submit()

    assert page.table.model.item(0, 0).text() == name

    session = get_session()
    try:
        customer = session.query(Customer).filter_by(name=name).first()
        customer_id = customer.id
    finally:
        session.close()

    try:
        page.name_input.setText(name)
        page._on_submit()
        assert len(warnings) == 1

        matching_rows = sum(
            1
            for row in range(page.table.row_count())
            if page.table.model.item(row, 0).text() == name
        )
        assert matching_rows == 1
    finally:
        _delete_customer(customer_id)
