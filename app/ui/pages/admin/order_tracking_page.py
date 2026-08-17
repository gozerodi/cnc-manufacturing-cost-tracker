from PySide6.QtWidgets import (
    QHeaderView,
    QProgressBar,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services import analytics_service
from app.ui.widgets import SegmentedControl, StandardTableWidget

ACTIVE_HEADERS = ["Order", "Step", "Produced / Total", "Progress"]
COMPLETED_HEADERS = ["Customer", "Product", "Quantity", "Completion Date"]


class OrderTrackingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.segmented_control = SegmentedControl(["Active Orders", "Completed Orders"])
        self.segmented_control.current_changed.connect(self._on_segment_changed)

        self.active_table = QTableWidget(0, len(ACTIVE_HEADERS))
        self.active_table.setHorizontalHeaderLabels(ACTIVE_HEADERS)
        self.active_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.active_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.active_table.verticalHeader().setVisible(False)
        active_header = self.active_table.horizontalHeader()
        active_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        active_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        active_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        active_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.completed_table = StandardTableWidget(headers=COMPLETED_HEADERS, stretch_column=1)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.active_table)
        self.pages.addWidget(self.completed_table)

        layout = QVBoxLayout(self)
        layout.addWidget(self.segmented_control)
        layout.addWidget(self.pages)

        self.refresh()

    def _on_segment_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def refresh(self) -> None:
        self._load_active()
        self._load_completed()

    def _load_active(self) -> None:
        orders = analytics_service.list_active_order_progress()
        rows = [(order, step) for order in orders for step in order.steps]

        self.active_table.setRowCount(len(rows))
        for row_index, (order, step) in enumerate(rows):
            self.active_table.setItem(
                row_index, 0, QTableWidgetItem(f"{order.customer_name} — {order.product_name}")
            )
            self.active_table.setItem(
                row_index, 1, QTableWidgetItem(f"Step {step.step_no} — {step.machine_name}")
            )
            self.active_table.setItem(
                row_index,
                2,
                QTableWidgetItem(f"{step.produced_quantity}/{step.target_quantity}"),
            )

            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(max(step.target_quantity, 1))
            progress_bar.setValue(min(step.produced_quantity, step.target_quantity))
            progress_bar.setTextVisible(True)
            self.active_table.setCellWidget(row_index, 3, progress_bar)

    def _load_completed(self) -> None:
        orders = analytics_service.list_completed_orders()
        self.completed_table.set_rows(
            [
                [
                    order.customer_name,
                    order.product_name,
                    order.quantity,
                    order.completed_at.strftime("%d.%m.%Y %H:%M") if order.completed_at else "",
                ]
                for order in orders
            ]
        )
