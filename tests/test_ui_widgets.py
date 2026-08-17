import decimal

import qdarktheme
from PySide6.QtWidgets import QHeaderView

from app.ui.widgets import (
    DatePicker,
    MoneyLineEdit,
    PeriodSelector,
    SegmentedControl,
    StandardTableWidget,
    TimeLineEdit,
    create_full_width_button,
)


def test_table_widget_renders_sample_data_both_themes(qapp):
    for theme in ("dark", "light"):
        qdarktheme.setup_theme(theme)
        table = StandardTableWidget(headers=["Date", "Customer", "Product", "Quantity"], stretch_column=2)
        rows = [
            ["24.07.2026", "Acme Metal Works", "Part A", "10"],
            ["23.07.2026", "Orion Fabrication", "Part B", "5"],
        ]
        table.set_rows(rows)
        assert table.row_count() == 2

        header = table.table.horizontalHeader()
        assert header.sectionResizeMode(2) == QHeaderView.ResizeMode.Stretch
        assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.ResizeToContents
    qdarktheme.setup_theme("auto")


def test_table_widget_edit_and_delete_signals(qapp):
    table = StandardTableWidget(headers=["Name"])
    table.set_rows([["A"], ["B"]])

    received = {}
    table.edit_requested.connect(lambda row: received.setdefault("edit", row))
    table.delete_requested.connect(lambda row: received.setdefault("delete", row))

    table._on_double_clicked(table.model.index(1, 0))
    assert received["edit"] == 1


def test_full_width_button_expands():
    from PySide6.QtWidgets import QSizePolicy

    button = create_full_width_button("Save")
    assert button.text() == "Save"
    assert button.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding


def test_time_input_accepts_valid_and_rejects_invalid(qapp):
    field = TimeLineEdit()

    field.setText("1.30")
    assert field.is_valid()
    assert field.seconds() == 90
    assert field.styleSheet() == ""

    field.setText("1.99")
    assert not field.is_valid()
    assert field.seconds() is None
    assert "e53935" in field.styleSheet()

    field.set_seconds(4500)
    assert field.text() == "1.15.00"


def test_money_input_accepts_valid_and_rejects_invalid(qapp):
    field = MoneyLineEdit()

    field.setText("12,345.67")
    assert field.is_valid()
    assert field.value() == decimal.Decimal("12345.67")

    field.set_value(decimal.Decimal("1000"))
    assert field.text() == "$1,000.00"

    field.setText("abc")
    assert not field.is_valid()
    assert "e53935" in field.styleSheet()


def test_segmented_control_switches_index(qapp):
    control = SegmentedControl(["Active", "Completed"])
    assert control.current_index() == 0

    control.set_current_index(1)
    assert control.current_index() == 1


def test_date_picker_defaults_to_today(qapp):
    picker = DatePicker()
    assert picker.date().isValid()
    assert picker.displayFormat() == "dd.MM.yyyy"


def test_period_selector_get_set(qapp):
    selector = PeriodSelector()
    assert selector.current_period() == "Day"

    selector.set_current_period("Month")
    assert selector.current_period() == "Month"
