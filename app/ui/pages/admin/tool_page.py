import decimal

from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services import tool_service
from app.ui.widgets import StandardTableWidget, create_full_width_button, format_money
from app.ui.widgets.money_input import MoneyLineEdit

TABLE_HEADERS = ["Name", "Corner Count", "Price", "Price per Corner"]


class ToolPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._editing_tool_id: int | None = None
        self._items: list[tool_service.ToolListItem] = []

        self.name_input = QLineEdit()
        self.corner_count_input = QSpinBox()
        self.corner_count_input.setRange(1, 999)
        self.price_input = MoneyLineEdit()
        self.price_per_corner_label = QLabel(format_money(decimal.Decimal(0)))

        self.corner_count_input.valueChanged.connect(self._update_price_per_corner_preview)
        self.price_input.textChanged.connect(self._update_price_per_corner_preview)

        form_layout = QFormLayout()
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Corner Count:", self.corner_count_input)
        form_layout.addRow("Price:", self.price_input)
        form_layout.addRow("Price per Corner:", self.price_per_corner_label)

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

        self._update_price_per_corner_preview()
        self.refresh()

    def _update_price_per_corner_preview(self, *_args) -> None:
        price = self.price_input.value()
        corner_count = self.corner_count_input.value()
        if price is not None and corner_count:
            price_per_corner = tool_service.calculate_price_per_corner(price, corner_count)
        else:
            price_per_corner = decimal.Decimal(0)
        self.price_per_corner_label.setText(format_money(price_per_corner))

    def refresh(self) -> None:
        items = tool_service.list_tools()
        self._items = items
        self.table.set_rows(
            [
                [
                    item.name,
                    item.corner_count,
                    format_money(item.price),
                    format_money(item.price_per_corner),
                ]
                for item in items
            ]
        )

    def _reset_form(self) -> None:
        self._editing_tool_id = None
        self.name_input.clear()
        self.corner_count_input.setValue(1)
        self.price_input.clear()
        self.submit_button.setText("Add")
        self.cancel_edit_button.setVisible(False)

    def _on_submit(self) -> None:
        name = self.name_input.text().strip()
        price = self.price_input.value()

        if not name:
            QMessageBox.warning(self, "Missing Information", "Tool name cannot be empty.")
            return
        if price is None:
            QMessageBox.warning(self, "Missing Information", "Price must be a valid number.")
            return

        corner_count = self.corner_count_input.value()

        if self._editing_tool_id is None:
            tool_service.create_tool(name, corner_count, price)
        else:
            tool_service.update_tool(self._editing_tool_id, name, corner_count, price)

        self._reset_form()
        self.refresh()

    def _on_edit_requested(self, row: int) -> None:
        item = self._items[row]
        self._editing_tool_id = item.id
        self.name_input.setText(item.name)
        self.corner_count_input.setValue(item.corner_count)
        self.price_input.set_value(item.price)
        self.submit_button.setText("Update")
        self.cancel_edit_button.setVisible(True)

    def _on_delete_requested(self, row: int) -> None:
        item = self._items[row]
        confirm = QMessageBox.question(
            self,
            "Delete Tool",
            f"Are you sure you want to delete '{item.name}'?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        tool_service.delete_tool(item.id)
        if self._editing_tool_id == item.id:
            self._reset_form()
        self.refresh()
