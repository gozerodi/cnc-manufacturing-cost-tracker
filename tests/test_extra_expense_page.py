import decimal
import uuid

from PySide6.QtWidgets import QMessageBox

from app.core.database import get_session
from app.models import FixedExpense, Machine, MachineCost, SpecialExpense
from app.services import machine_service
from app.ui.pages.admin.extra_expense_page import ExtraExpensePage

D = decimal.Decimal


def test_add_edit_delete_fixed_expense_via_page(qapp, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )

    page = ExtraExpensePage()
    name = f"Page Fixed Expense {uuid.uuid4().hex[:8]}"

    page.fixed_name_input.setText(name)
    page.fixed_amount_input.setText("1500")
    page.fixed_period_combo.setCurrentText("Monthly")
    page._on_fixed_submit()

    assert page.fixed_table.model.item(0, 0).text() == name
    assert page.fixed_table.model.item(0, 1).text() == "$1,500.00"
    assert page.fixed_table.model.item(0, 2).text() == "Monthly"

    expense_id = page._fixed_items[0].id
    try:
        page._on_fixed_edit_requested(0)
        assert page.fixed_submit_button.text() == "Update"
        page.fixed_amount_input.setText("2000")
        page.fixed_period_combo.setCurrentText("Daily")
        page._on_fixed_submit()

        row_index = next(i for i, item in enumerate(page._fixed_items) if item.id == expense_id)
        assert page.fixed_table.model.item(row_index, 1).text() == "$2,000.00"
        assert page.fixed_table.model.item(row_index, 2).text() == "Daily"

        page._on_fixed_delete_requested(row_index)
        assert all(item.id != expense_id for item in page._fixed_items)
    finally:
        if expense_id is not None:
            session = get_session()
            try:
                session.query(FixedExpense).filter_by(id=expense_id).delete()
                session.commit()
            finally:
                session.close()


def test_add_edit_delete_special_expense_via_page(qapp, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )

    machine_id = machine_service.create_machine(f"Page Cost Machine {uuid.uuid4().hex[:8]}", D("75"))
    try:
        page = ExtraExpensePage()
        name = f"Page Special Expense {uuid.uuid4().hex[:8]}"

        page.special_name_input.setText(name)
        page.special_amount_input.setText("450")
        page.special_month_selector.set_year_month(2026, 7)
        index = page.special_machine_combo.findData(machine_id)
        assert index >= 0
        page.special_machine_combo.setCurrentIndex(index)
        page._on_special_submit()

        page.special_list_month_selector.set_year_month(2026, 7)
        assert page.special_table.model.item(0, 0).text() == "July 2026"
        assert page.special_table.model.item(0, 1).text() == name
        assert page.special_table.model.item(0, 2).text() == "$450.00"

        expense_id = page._special_items[0].id
        try:
            page._on_special_edit_requested(0)
            assert page.special_submit_button.text() == "Update"
            page.special_amount_input.setText("600")
            page.special_month_selector.set_year_month(2026, 8)
            page._on_special_submit()

            assert all(item.id != expense_id for item in page._special_items)

            page.special_list_month_selector.set_year_month(2026, 8)
            row_index = next(
                i for i, item in enumerate(page._special_items) if item.id == expense_id
            )
            assert page.special_table.model.item(row_index, 0).text() == "August 2026"
            assert page.special_table.model.item(row_index, 2).text() == "$600.00"

            page._on_special_delete_requested(row_index)
            assert all(item.id != expense_id for item in page._special_items)
            expense_id = None
        finally:
            if expense_id is not None:
                session = get_session()
                try:
                    session.query(SpecialExpense).filter_by(id=expense_id).delete()
                    session.commit()
                finally:
                    session.close()
    finally:
        session = get_session()
        try:
            session.query(SpecialExpense).filter_by(machine_id=machine_id).delete()
            session.query(MachineCost).filter_by(machine_id=machine_id).delete()
            session.query(Machine).filter_by(id=machine_id).delete()
            session.commit()
        finally:
            session.close()


def test_special_expense_list_filters_by_selected_month(qapp):
    page = ExtraExpensePage()
    name = f"Page Special Expense Filter {uuid.uuid4().hex[:8]}"

    page.special_name_input.setText(name)
    page.special_amount_input.setText("120")
    page.special_month_selector.set_year_month(2026, 7)
    page._on_special_submit()

    page.special_list_month_selector.set_year_month(2026, 7)
    expense_id = page._special_items[0].id
    try:
        assert any(item.id == expense_id for item in page._special_items)

        page.special_list_month_selector.set_year_month(2026, 6)
        assert all(item.id != expense_id for item in page._special_items)

        page.special_list_month_selector.set_year_month(2026, 7)
        assert any(item.id == expense_id for item in page._special_items)
    finally:
        session = get_session()
        try:
            session.query(SpecialExpense).filter_by(id=expense_id).delete()
            session.commit()
        finally:
            session.close()
