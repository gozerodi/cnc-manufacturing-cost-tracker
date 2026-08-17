from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services import cost_service, machine_service
from app.ui.widgets import (
    MonthYearSelector,
    SegmentedControl,
    StandardTableWidget,
    create_full_width_button,
    format_money,
)
from app.ui.widgets.money_input import MoneyLineEdit

PERIOD_LABELS = {"daily": "Daily", "monthly": "Monthly"}
PERIOD_VALUES = {label: value for value, label in PERIOD_LABELS.items()}

NO_MACHINE_LABEL = "No Machine"

FIXED_HEADERS = ["Name", "Amount", "Period"]
SPECIAL_HEADERS = ["Month/Year", "Name", "Amount", "Machine"]


class ExtraExpensePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fixed_items: list[cost_service.FixedExpenseListItem] = []
        self._special_items: list[cost_service.SpecialExpenseListItem] = []
        self._editing_fixed_id: int | None = None
        self._editing_special_id: int | None = None

        self.segmented_control = SegmentedControl(["Month-Specific Expense", "Fixed Expense"])
        self.segmented_control.current_changed.connect(self._on_segment_changed)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_special_expense_page())
        self.pages.addWidget(self._build_fixed_expense_page())

        layout = QVBoxLayout(self)
        layout.addWidget(self.segmented_control)
        layout.addWidget(self.pages)

        self.refresh()

    def _on_segment_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def _build_special_expense_page(self) -> QWidget:
        widget = QWidget()

        self.special_name_input = QLineEdit()
        self.special_amount_input = MoneyLineEdit()
        self.special_month_selector = MonthYearSelector()
        self.special_machine_combo = QComboBox()
        self.special_machine_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.special_machine_combo.setMinimumContentsLength(16)

        form_layout = QFormLayout()
        form_layout.addRow("Name / Note:", self.special_name_input)
        form_layout.addRow("Amount:", self.special_amount_input)
        form_layout.addRow("Month:", self.special_month_selector)
        form_layout.addRow("Machine:", self.special_machine_combo)

        self.special_submit_button = create_full_width_button("Add")
        self.special_submit_button.clicked.connect(self._on_special_submit)
        self.special_cancel_button = create_full_width_button("Cancel")
        self.special_cancel_button.clicked.connect(self._reset_special_form)
        self.special_cancel_button.setVisible(False)

        self.special_list_month_selector = MonthYearSelector()
        self.special_list_month_selector.month_changed.connect(self._refresh_special_list)

        list_filter_layout = QFormLayout()
        list_filter_layout.addRow("List Month:", self.special_list_month_selector)

        self.special_table = StandardTableWidget(headers=SPECIAL_HEADERS, stretch_column=1)
        self.special_table.edit_requested.connect(self._on_special_edit_requested)
        self.special_table.delete_requested.connect(self._on_special_delete_requested)

        layout = QVBoxLayout(widget)
        layout.addLayout(form_layout)
        layout.addWidget(self.special_submit_button)
        layout.addWidget(self.special_cancel_button)
        layout.addLayout(list_filter_layout)
        layout.addWidget(self.special_table)
        return widget

    def _build_fixed_expense_page(self) -> QWidget:
        widget = QWidget()

        self.fixed_name_input = QLineEdit()
        self.fixed_amount_input = MoneyLineEdit()
        self.fixed_period_combo = QComboBox()
        self.fixed_period_combo.addItems(PERIOD_LABELS.values())

        form_layout = QFormLayout()
        form_layout.addRow("Name:", self.fixed_name_input)
        form_layout.addRow("Amount:", self.fixed_amount_input)
        form_layout.addRow("Period:", self.fixed_period_combo)

        self.fixed_submit_button = create_full_width_button("Add")
        self.fixed_submit_button.clicked.connect(self._on_fixed_submit)
        self.fixed_cancel_button = create_full_width_button("Cancel")
        self.fixed_cancel_button.clicked.connect(self._reset_fixed_form)
        self.fixed_cancel_button.setVisible(False)

        self.fixed_table = StandardTableWidget(headers=FIXED_HEADERS, stretch_column=0)
        self.fixed_table.edit_requested.connect(self._on_fixed_edit_requested)
        self.fixed_table.delete_requested.connect(self._on_fixed_delete_requested)

        layout = QVBoxLayout(widget)
        layout.addLayout(form_layout)
        layout.addWidget(self.fixed_submit_button)
        layout.addWidget(self.fixed_cancel_button)
        layout.addWidget(self.fixed_table)
        return widget

    def refresh(self) -> None:
        self._fixed_items = cost_service.list_fixed_expenses()
        self.fixed_table.set_rows(
            [
                [item.name, format_money(item.amount), PERIOD_LABELS[item.period]]
                for item in self._fixed_items
            ]
        )

        self._refresh_machine_combo()
        self._refresh_special_list()

    def _refresh_machine_combo(self) -> None:
        current_id = self.special_machine_combo.currentData()
        self.special_machine_combo.blockSignals(True)
        self.special_machine_combo.clear()
        self.special_machine_combo.addItem(NO_MACHINE_LABEL, None)
        for machine in machine_service.list_machines():
            self.special_machine_combo.addItem(machine.name, machine.id)
        if current_id is not None:
            index = self.special_machine_combo.findData(current_id)
            if index >= 0:
                self.special_machine_combo.setCurrentIndex(index)
        self.special_machine_combo.blockSignals(False)

    def _refresh_special_list(self, *_args) -> None:
        year, month = self.special_list_month_selector.selected_year_month()
        self._special_items = cost_service.list_special_expenses_for_month(year, month)
        self.special_table.set_rows(
            [
                [
                    cost_service.month_label(item.year, item.month),
                    item.name,
                    format_money(item.amount),
                    item.machine_name or NO_MACHINE_LABEL,
                ]
                for item in self._special_items
            ]
        )

    def _reset_fixed_form(self) -> None:
        self._editing_fixed_id = None
        self.fixed_name_input.clear()
        self.fixed_amount_input.clear()
        self.fixed_period_combo.setCurrentIndex(0)
        self.fixed_submit_button.setText("Add")
        self.fixed_cancel_button.setVisible(False)

    def _on_fixed_submit(self) -> None:
        name = self.fixed_name_input.text().strip()
        amount = self.fixed_amount_input.value()

        if not name:
            QMessageBox.warning(self, "Missing Information", "Expense name cannot be empty.")
            return
        if amount is None:
            QMessageBox.warning(self, "Missing Information", "Amount must be a valid number.")
            return

        period = PERIOD_VALUES[self.fixed_period_combo.currentText()]

        if self._editing_fixed_id is None:
            cost_service.create_fixed_expense(name, amount, period)
        else:
            cost_service.update_fixed_expense(self._editing_fixed_id, name, amount, period)

        self._reset_fixed_form()
        self.refresh()

    def _on_fixed_edit_requested(self, row: int) -> None:
        item = self._fixed_items[row]
        self._editing_fixed_id = item.id
        self.fixed_name_input.setText(item.name)
        self.fixed_amount_input.set_value(item.amount)
        self.fixed_period_combo.setCurrentText(PERIOD_LABELS[item.period])
        self.fixed_submit_button.setText("Update")
        self.fixed_cancel_button.setVisible(True)

    def _on_fixed_delete_requested(self, row: int) -> None:
        item = self._fixed_items[row]
        confirm = QMessageBox.question(
            self, "Delete Fixed Expense", f"Are you sure you want to delete '{item.name}'?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        cost_service.soft_delete_fixed_expense(item.id)
        if self._editing_fixed_id == item.id:
            self._reset_fixed_form()
        self.refresh()

    def _reset_special_form(self) -> None:
        self._editing_special_id = None
        self.special_name_input.clear()
        self.special_amount_input.clear()
        self.special_machine_combo.setCurrentIndex(0)
        self.special_submit_button.setText("Add")
        self.special_cancel_button.setVisible(False)

    def _on_special_submit(self) -> None:
        name = self.special_name_input.text().strip()
        amount = self.special_amount_input.value()

        if not name:
            QMessageBox.warning(self, "Missing Information", "Expense name/note cannot be empty.")
            return
        if amount is None:
            QMessageBox.warning(self, "Missing Information", "Amount must be a valid number.")
            return

        year, month = self.special_month_selector.selected_year_month()
        machine_id = self.special_machine_combo.currentData()

        if self._editing_special_id is None:
            cost_service.create_special_expense(name, amount, year, month, machine_id)
        else:
            cost_service.update_special_expense(
                self._editing_special_id, name, amount, year, month, machine_id
            )

        self._reset_special_form()
        self.refresh()

    def _on_special_edit_requested(self, row: int) -> None:
        item = self._special_items[row]
        self._editing_special_id = item.id
        self.special_name_input.setText(item.name)
        self.special_amount_input.set_value(item.amount)
        self.special_month_selector.set_year_month(item.year, item.month)
        index = self.special_machine_combo.findData(item.machine_id)
        if index >= 0:
            self.special_machine_combo.setCurrentIndex(index)
        self.special_submit_button.setText("Update")
        self.special_cancel_button.setVisible(True)

    def _on_special_delete_requested(self, row: int) -> None:
        item = self._special_items[row]
        confirm = QMessageBox.question(
            self, "Delete Month-Specific Expense", f"Are you sure you want to delete '{item.name}'?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        cost_service.delete_special_expense(item.id)
        if self._editing_special_id == item.id:
            self._reset_special_form()
        self.refresh()
