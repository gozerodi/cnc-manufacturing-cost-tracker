from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services import personnel_service, production_service
from app.ui.widgets import DatePicker, StandardTableWidget, create_full_width_button, format_money
from app.ui.widgets.time_input import TimeLineEdit

TABLE_HEADERS = ["Work Order", "Step", "Actual Time", "Quantity", "Price Contribution", "Personnel"]

FIELD_MIN_WIDTH = 320
VISIBLE_PERSONNEL_ROWS = 10
PERSONNEL_ROW_HEIGHT = 28


class DailyProductionPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._work_orders: list[production_service.WorkOrderOption] = []
        self._steps: list[production_service.StepOption] = []
        self._entries: list[production_service.DailyProductionListItem] = []

        self.date_input = DatePicker()
        self.date_input.dateChanged.connect(self._refresh_entries)

        self.work_order_combo = QComboBox()
        self.work_order_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.work_order_combo.setMinimumContentsLength(20)
        self.work_order_combo.setMinimumWidth(FIELD_MIN_WIDTH)
        self.work_order_combo.currentIndexChanged.connect(self._on_work_order_changed)

        self.step_combo = QComboBox()
        self.step_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.step_combo.setMinimumContentsLength(20)
        self.step_combo.setMinimumWidth(FIELD_MIN_WIDTH)

        self.seconds_input = TimeLineEdit()
        self.seconds_input.setMinimumWidth(FIELD_MIN_WIDTH)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 1_000_000)
        self.quantity_input.setMinimumWidth(FIELD_MIN_WIDTH)

        self.personnel_list = QListWidget()
        self.personnel_list.setFixedHeight(VISIBLE_PERSONNEL_ROWS * PERSONNEL_ROW_HEIGHT)

        form_layout = QFormLayout()
        form_layout.addRow("Date:", self.date_input)
        form_layout.addRow("Work Order:", self.work_order_combo)
        form_layout.addRow("Processing Step:", self.step_combo)
        form_layout.addRow("Actual Unit Time:", self.seconds_input)
        form_layout.addRow("Quantity:", self.quantity_input)
        form_layout.addRow("Personnel:", self.personnel_list)

        save_button = create_full_width_button("Save")
        save_button.clicked.connect(self._on_save)

        self.entries_table = StandardTableWidget(headers=TABLE_HEADERS, stretch_column=0)
        self.entries_table.delete_requested.connect(self._on_delete_requested)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(save_button)
        layout.addWidget(self.entries_table)

        self.refresh()

    def refresh(self) -> None:
        self._load_personnel_list()
        self._load_work_orders()
        self._refresh_entries()

    def _load_personnel_list(self) -> None:
        self.personnel_list.clear()
        for person in personnel_service.list_production_personnel():
            item = QListWidgetItem(f"{person.name} ({personnel_service.TYPE_LABELS[person.type]})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, person.id)
            self.personnel_list.addItem(item)

    def _load_work_orders(self) -> None:
        self._work_orders = production_service.list_active_work_orders()
        self.work_order_combo.clear()
        for work_order in self._work_orders:
            label = f"{work_order.customer_name} — {work_order.product_name} (qty: {work_order.quantity})"
            self.work_order_combo.addItem(label, work_order.id)
        self._on_work_order_changed()

    def _on_work_order_changed(self, *_args) -> None:
        work_order_id = self.work_order_combo.currentData()
        self.step_combo.clear()
        self._steps = []
        if work_order_id is None:
            return
        self._steps = production_service.list_steps_for_work_order(work_order_id)
        for step in self._steps:
            self.step_combo.addItem(f"Step {step.step_no} — {step.machine_name}", step.id)

    def _refresh_entries(self, *_args) -> None:
        production_date = self.date_input.date().toPython()
        entries = production_service.list_daily_productions_for_date(production_date)
        self._entries = entries
        self.entries_table.set_rows(
            [
                [
                    f"{entry.customer_name} — {entry.product_name}",
                    f"Step {entry.step_no} — {entry.machine_name}",
                    f"{entry.actual_unit_seconds} s",
                    entry.quantity,
                    format_money(entry.price_contribution),
                    ", ".join(entry.personnel_names),
                ]
                for entry in entries
            ]
        )

    def _on_save(self) -> None:
        work_order_id = self.work_order_combo.currentData()
        step_id = self.step_combo.currentData()

        if work_order_id is None or step_id is None:
            QMessageBox.warning(self, "Missing Information", "Please select a work order and a processing step.")
            return

        if not self.seconds_input.is_valid() or self.seconds_input.seconds() is None:
            QMessageBox.warning(self, "Missing Information", "Enter a valid actual time.")
            return

        personnel_ids = []
        for i in range(self.personnel_list.count()):
            item = self.personnel_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                personnel_ids.append(item.data(Qt.ItemDataRole.UserRole))

        production_service.create_daily_production(
            production_date=self.date_input.date().toPython(),
            work_order_id=work_order_id,
            step_id=step_id,
            actual_unit_seconds=self.seconds_input.seconds(),
            quantity=self.quantity_input.value(),
            personnel_ids=personnel_ids,
        )

        self.seconds_input.clear()
        self.quantity_input.setValue(1)
        for i in range(self.personnel_list.count()):
            self.personnel_list.item(i).setCheckState(Qt.CheckState.Unchecked)

        self.refresh()

    def _on_delete_requested(self, row: int) -> None:
        entry = self._entries[row]
        confirm = QMessageBox.question(
            self,
            "Delete Record",
            "Are you sure you want to delete this daily production record?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        production_service.delete_daily_production(entry.id)
        self.refresh()
