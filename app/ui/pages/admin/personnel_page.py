import decimal

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services import personnel_service, settings_service
from app.ui.widgets import StandardTableWidget, create_full_width_button, format_money
from app.ui.widgets.money_input import MoneyLineEdit

TYPE_LABELS = personnel_service.TYPE_LABELS
TYPE_VALUES = {label: value for value, label in TYPE_LABELS.items()}

TABLE_HEADERS = ["Name", "Type", "Monthly Salary", "Days/Month", "Hours/Day", "Hourly Cost"]


class PersonnelPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._editing_personnel_id: int | None = None
        self._items: list[personnel_service.PersonnelListItem] = []

        self.name_input = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(TYPE_LABELS.values())
        self.type_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.type_combo.setMinimumContentsLength(max(len(label) for label in TYPE_LABELS.values()))
        self.salary_input = MoneyLineEdit()
        self.days_input = QSpinBox()
        self.days_input.setRange(1, 31)
        self.days_input.setValue(20)
        self.hours_input = QSpinBox()
        self.hours_input.setRange(1, 24)
        self.hours_input.setValue(9)
        self.hourly_cost_label = QLabel(format_money(decimal.Decimal(0)))

        self.salary_input.textChanged.connect(self._update_hourly_cost_preview)
        self.days_input.valueChanged.connect(self._update_hourly_cost_preview)
        self.hours_input.valueChanged.connect(self._update_hourly_cost_preview)

        form_layout = QFormLayout()
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Type:", self.type_combo)
        form_layout.addRow("Monthly Salary:", self.salary_input)
        form_layout.addRow("Days per Month:", self.days_input)
        form_layout.addRow("Hours per Day:", self.hours_input)
        form_layout.addRow("Hourly Cost:", self.hourly_cost_label)

        self.submit_button = create_full_width_button("Add")
        self.submit_button.clicked.connect(self._on_submit)
        self.cancel_edit_button = create_full_width_button("Cancel")
        self.cancel_edit_button.clicked.connect(self._reset_form)
        self.cancel_edit_button.setVisible(False)

        self.table = StandardTableWidget(headers=TABLE_HEADERS, stretch_column=0)
        self.table.edit_requested.connect(self._on_edit_requested)
        self.table.delete_requested.connect(self._on_delete_requested)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.cancel_edit_button)
        layout.addWidget(self.table)
        layout.addWidget(self._build_password_change_group())

        self._update_hourly_cost_preview()
        self.refresh()

    def _build_password_change_group(self) -> QGroupBox:
        group = QGroupBox("Change Page Password")

        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_confirm_input = QLineEdit()
        self.new_password_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)

        change_button = create_full_width_button("Change Password")
        change_button.clicked.connect(self._on_change_password)

        layout = QFormLayout(group)
        layout.addRow("Current Password:", self.current_password_input)
        layout.addRow("New Password:", self.new_password_input)
        layout.addRow("New Password (Confirm):", self.new_password_confirm_input)
        layout.addRow(change_button)
        return group

    def _update_hourly_cost_preview(self, *_args) -> None:
        salary = self.salary_input.value()
        days = self.days_input.value()
        hours = self.hours_input.value()
        if salary is not None and days and hours:
            hourly_cost = personnel_service.calculate_hourly_cost(salary, days, hours)
        else:
            hourly_cost = decimal.Decimal(0)
        self.hourly_cost_label.setText(format_money(hourly_cost))

    def refresh(self) -> None:
        items = personnel_service.list_personnel()
        self._items = items
        self.table.set_rows(
            [
                [
                    item.name,
                    TYPE_LABELS[item.type],
                    format_money(item.monthly_salary),
                    item.days_per_month,
                    item.hours_per_day,
                    format_money(item.hourly_cost),
                ]
                for item in items
            ]
        )

    def _reset_form(self) -> None:
        self._editing_personnel_id = None
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.salary_input.clear()
        self.days_input.setValue(20)
        self.hours_input.setValue(9)
        self.submit_button.setText("Add")
        self.cancel_edit_button.setVisible(False)

    def _on_submit(self) -> None:
        name = self.name_input.text().strip()
        salary = self.salary_input.value()

        if not name:
            QMessageBox.warning(self, "Missing Information", "Personnel name cannot be empty.")
            return
        if salary is None:
            QMessageBox.warning(self, "Missing Information", "Monthly salary must be a valid number.")
            return

        type_ = TYPE_VALUES[self.type_combo.currentText()]
        days = self.days_input.value()
        hours = self.hours_input.value()

        if self._editing_personnel_id is None:
            personnel_service.create_personnel(name, type_, salary, days, hours)
        else:
            personnel_service.update_personnel(
                self._editing_personnel_id, name, type_, salary, days, hours
            )

        self._reset_form()
        self.refresh()

    def _on_edit_requested(self, row: int) -> None:
        item = self._items[row]
        self._editing_personnel_id = item.id
        self.name_input.setText(item.name)
        self.type_combo.setCurrentText(TYPE_LABELS[item.type])
        self.salary_input.set_value(item.monthly_salary)
        self.days_input.setValue(item.days_per_month)
        self.hours_input.setValue(item.hours_per_day)
        self.submit_button.setText("Update")
        self.cancel_edit_button.setVisible(True)

    def _on_delete_requested(self, row: int) -> None:
        item = self._items[row]
        confirm = QMessageBox.question(
            self,
            "Delete Personnel",
            f"Are you sure you want to delete '{item.name}'?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        personnel_service.soft_delete_personnel(item.id)
        if self._editing_personnel_id == item.id:
            self._reset_form()
        self.refresh()

    def _on_change_password(self) -> None:
        current = self.current_password_input.text()
        new = self.new_password_input.text()
        confirm = self.new_password_confirm_input.text()

        if not new or new != confirm:
            QMessageBox.warning(self, "Password Error", "New passwords do not match.")
            return

        try:
            settings_service.change_personnel_page_password(current, new)
        except settings_service.InvalidPasswordError:
            QMessageBox.warning(self, "Password Error", "Current password is incorrect.")
            return

        self.current_password_input.clear()
        self.new_password_input.clear()
        self.new_password_confirm_input.clear()
        QMessageBox.information(self, "Success", "Page password updated.")
