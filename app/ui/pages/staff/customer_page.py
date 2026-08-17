from PySide6.QtWidgets import QFormLayout, QLineEdit, QMessageBox, QVBoxLayout, QWidget

from app.services import customer_service
from app.ui.widgets import StandardTableWidget, create_full_width_button

TABLE_HEADERS = ["Customer Name"]


class CustomerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.name_input = QLineEdit()

        form_layout = QFormLayout()
        form_layout.addRow("Customer Name:", self.name_input)

        self.submit_button = create_full_width_button("Add")
        self.submit_button.clicked.connect(self._on_submit)

        self.table = StandardTableWidget(headers=TABLE_HEADERS, stretch_column=0)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        items = customer_service.list_customers()
        self.table.set_rows([[item.name] for item in items])

    def _on_submit(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Information", "Customer name cannot be empty.")
            return

        try:
            customer_service.create_customer(name)
        except customer_service.DuplicateCustomerError:
            QMessageBox.warning(self, "Duplicate Customer", f"'{name}' already exists.")
            return

        self.name_input.clear()
        self.refresh()
