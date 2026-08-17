from PySide6.QtWidgets import QFormLayout, QLineEdit, QMessageBox, QVBoxLayout, QWidget

from app.services import machine_service
from app.ui.widgets import StandardTableWidget, create_full_width_button, format_money
from app.ui.widgets.money_input import MoneyLineEdit

TABLE_HEADERS = ["Name", "Hourly Cost"]


class MachinePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._editing_machine_id: int | None = None
        self._items: list[machine_service.MachineListItem] = []

        self.name_input = QLineEdit()
        self.hourly_cost_input = MoneyLineEdit()

        form_layout = QFormLayout()
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Hourly Cost:", self.hourly_cost_input)

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

        self.refresh()

    def refresh(self) -> None:
        items = machine_service.list_machines()
        self._items = items
        self.table.set_rows(
            [[item.name, format_money(item.hourly_cost)] for item in items]
        )

    def _reset_form(self) -> None:
        self._editing_machine_id = None
        self.name_input.clear()
        self.hourly_cost_input.clear()
        self.submit_button.setText("Add")
        self.cancel_edit_button.setVisible(False)

    def _on_submit(self) -> None:
        name = self.name_input.text().strip()
        hourly_cost = self.hourly_cost_input.value()

        if not name:
            QMessageBox.warning(self, "Missing Information", "Machine name cannot be empty.")
            return
        if hourly_cost is None:
            QMessageBox.warning(self, "Missing Information", "Hourly cost must be a valid number.")
            return

        if self._editing_machine_id is None:
            machine_service.create_machine(name, hourly_cost)
        else:
            machine_service.update_machine(self._editing_machine_id, name, hourly_cost)

        self._reset_form()
        self.refresh()

    def _on_edit_requested(self, row: int) -> None:
        item = self._items[row]
        self._editing_machine_id = item.id
        self.name_input.setText(item.name)
        self.hourly_cost_input.set_value(item.hourly_cost)
        self.submit_button.setText("Update")
        self.cancel_edit_button.setVisible(True)

    def _on_delete_requested(self, row: int) -> None:
        item = self._items[row]
        confirm = QMessageBox.question(
            self,
            "Delete Machine",
            f"Are you sure you want to delete '{item.name}'?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        machine_service.soft_delete_machine(item.id)
        if self._editing_machine_id == item.id:
            self._reset_form()
        self.refresh()
