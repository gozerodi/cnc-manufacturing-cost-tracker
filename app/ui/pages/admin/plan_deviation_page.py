import decimal

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.services import analytics_service
from app.ui.widgets import format_money

HEADERS = ["Order", "Step", "Planned Time", "Actual Time", "Deviated Quantity", "Deviation Cost"]

FASTER_COLOR = QColor("#2e7d32")
SLOWER_COLOR = QColor("#c62828")


def _gain_from_deviation_cost(deviation_cost: decimal.Decimal) -> decimal.Decimal:
    # deviation_cost comes out negative for faster-than-planned production; on screen we
    # show the inverse (gain/loss): faster=gain=+, slower=loss=-.
    return -deviation_cost


def _format_signed_gain(gain: decimal.Decimal) -> str:
    formatted = format_money(abs(gain))
    sign = "-" if gain < 0 else "+"
    return f"{sign}{formatted}"


class PlanDeviationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        for column in range(len(HEADERS) - 1):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(len(HEADERS) - 1, QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        records = analytics_service.list_deviation_records()
        self.table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            self.table.setItem(
                row_index, 0, QTableWidgetItem(f"{record.customer_name} — {record.product_name}")
            )
            self.table.setItem(
                row_index, 1, QTableWidgetItem(f"Step {record.step_no} — {record.machine_name}")
            )
            self.table.setItem(row_index, 2, QTableWidgetItem(f"{record.planned_unit_seconds} s"))
            self.table.setItem(row_index, 3, QTableWidgetItem(f"{record.actual_unit_seconds} s"))
            self.table.setItem(row_index, 4, QTableWidgetItem(str(record.quantity)))

            gain = _gain_from_deviation_cost(record.deviation_cost)
            cost_item = QTableWidgetItem(_format_signed_gain(gain))
            cost_item.setForeground(FASTER_COLOR if gain >= 0 else SLOWER_COLOR)
            self.table.setItem(row_index, 5, cost_item)
