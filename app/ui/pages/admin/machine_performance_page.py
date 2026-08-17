from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QVBoxLayout, QWidget

from app.services import analytics_service, machine_service
from app.ui.widgets import DateRangeFilter, StandardTableWidget, format_money

PERFORMANCE_HEADERS = ["Machine", "Hourly Return", "Total Price Contribution"]
DETAIL_HEADERS = ["Date", "Customer", "Product", "Step", "Duration", "Quantity", "Price Contribution"]


def _pastel_colors(count: int) -> list:
    if count == 0:
        return []
    cmap = colormaps["Pastel1"]
    return [cmap(i % cmap.N) for i in range(count)]


class MachinePerformancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._performance: list[analytics_service.MachinePerformance] = []

        self.date_filter = DateRangeFilter()
        self.date_filter.range_changed.connect(self.refresh)

        self.machine_combo = QComboBox()
        self.machine_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.machine_combo.setMinimumContentsLength(20)
        self.machine_combo.currentIndexChanged.connect(self._refresh_detail)

        self.figure = Figure(figsize=(4, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)

        self.performance_table = StandardTableWidget(
            headers=PERFORMANCE_HEADERS, stretch_column=0, visible_rows=10
        )

        module1_layout = QHBoxLayout()
        module1_layout.addWidget(self.canvas, 1)
        module1_layout.addWidget(self.performance_table, 1)

        detail_filter_layout = QFormLayout()
        detail_filter_layout.addRow("Machine:", self.machine_combo)

        self.detail_table = StandardTableWidget(headers=DETAIL_HEADERS, stretch_column=2)

        layout = QVBoxLayout(self)
        layout.addWidget(self.date_filter)
        layout.addLayout(module1_layout)
        layout.addLayout(detail_filter_layout)
        layout.addWidget(self.detail_table)

        self.refresh()

    def _date_range(self):
        if self.date_filter.source == "month":
            return self.date_filter.month_selector.date_range()
        end_date = self.date_filter.date_input.date().toPython()
        start_date = analytics_service.period_start_date(
            end_date, self.date_filter.period_selector.current_period()
        )
        return start_date, end_date

    def refresh(self, *_args) -> None:
        start_date, end_date = self._date_range()
        self._performance = analytics_service.list_machine_performance(start_date, end_date)

        self.performance_table.set_rows(
            [
                [
                    item.machine_name,
                    format_money(item.hourly_return),
                    format_money(item.total_price_contribution),
                ]
                for item in self._performance
            ]
        )
        self._draw_pie_chart()
        self._refresh_machine_combo()

    def _refresh_machine_combo(self) -> None:
        current_id = self.machine_combo.currentData()
        self.machine_combo.blockSignals(True)
        self.machine_combo.clear()
        for machine in machine_service.list_machines():
            self.machine_combo.addItem(machine.name, machine.id)
        if current_id is not None:
            index = self.machine_combo.findData(current_id)
            if index >= 0:
                self.machine_combo.setCurrentIndex(index)
        self.machine_combo.blockSignals(False)
        self._refresh_detail()

    def _draw_pie_chart(self) -> None:
        self.figure.clear()
        self.figure.patch.set_alpha(0)

        if not self._performance:
            self.canvas.draw()
            return

        text_color = self.palette().color(self.foregroundRole()).name()

        axes = self.figure.add_subplot(111)
        axes.set_facecolor("none")

        labels = [item.machine_name for item in self._performance]
        values = [float(item.total_price_contribution) for item in self._performance]
        colors = _pastel_colors(len(values))

        _wedges, _texts, autotexts = axes.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            colors=colors,
            textprops={"color": text_color},
            wedgeprops={"linewidth": 0},
        )
        # Pastel wedge colors are always light, so the percentage labels are drawn with a
        # fixed dark color instead of the theme color (otherwise white text is unreadable
        # on a light pastel background in dark mode).
        for autotext in autotexts:
            autotext.set_color("#2b2b2b")
        axes.axis("equal")
        self.figure.tight_layout()
        self.canvas.draw()

    def _refresh_detail(self, *_args) -> None:
        machine_id = self.machine_combo.currentData()
        if machine_id is None:
            self.detail_table.set_rows([])
            return

        start_date, end_date = self._date_range()
        entries = analytics_service.list_machine_detail(machine_id, start_date, end_date)
        self.detail_table.set_rows(
            [
                [
                    entry.production_date.strftime("%d.%m.%Y"),
                    entry.customer_name,
                    entry.product_name,
                    f"Step {entry.step_no}",
                    f"{entry.actual_unit_seconds} s",
                    entry.quantity,
                    format_money(entry.price_contribution),
                ]
                for entry in entries
            ]
        )
