from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCompleter, QFormLayout, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from app.services import analytics_service, customer_service
from app.ui.widgets import DateRangeFilter, StandardTableWidget, format_money

PERFORMANCE_HEADERS = ["Customer", "Hourly Return", "Total Price Contribution"]
DETAIL_HEADERS = ["Date", "Product", "Step", "Duration", "Quantity", "Price Contribution"]


def _pastel_colors(count: int) -> list:
    if count == 0:
        return []
    cmap = colormaps["Pastel1"]
    return [cmap(i % cmap.N) for i in range(count)]


class CustomerPerformancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._performance: list[analytics_service.CustomerPerformance] = []
        self._customers: list[customer_service.CustomerListItem] = []

        self.date_filter = DateRangeFilter()
        self.date_filter.range_changed.connect(self.refresh)

        self.customer_input = QLineEdit()
        self._customer_completer = QCompleter([])
        self._customer_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.customer_input.setCompleter(self._customer_completer)
        self.customer_input.textChanged.connect(self._refresh_detail)

        self.figure = Figure(figsize=(4, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)

        self.performance_table = StandardTableWidget(
            headers=PERFORMANCE_HEADERS, stretch_column=0, visible_rows=10
        )

        module1_layout = QHBoxLayout()
        module1_layout.addWidget(self.canvas, 1)
        module1_layout.addWidget(self.performance_table, 1)

        detail_filter_layout = QFormLayout()
        detail_filter_layout.addRow("Customer:", self.customer_input)

        self.detail_table = StandardTableWidget(headers=DETAIL_HEADERS, stretch_column=1)

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

    def _resolve_customer_id(self):
        typed_name = self.customer_input.text().strip()
        if not typed_name:
            return None
        for customer in self._customers:
            if customer.name == typed_name:
                return customer.id
        for customer in self._customers:
            if customer.name.lower() == typed_name.lower():
                return customer.id
        return None

    def refresh(self, *_args) -> None:
        start_date, end_date = self._date_range()
        self._performance = analytics_service.list_customer_performance(start_date, end_date)

        self.performance_table.set_rows(
            [
                [
                    item.customer_name,
                    format_money(item.hourly_return),
                    format_money(item.total_price_contribution),
                ]
                for item in self._performance
            ]
        )
        self._draw_pie_chart()

        self._customers = customer_service.list_customers()
        self._customer_completer = QCompleter([c.name for c in self._customers])
        self._customer_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.customer_input.setCompleter(self._customer_completer)

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

        labels = [item.customer_name for item in self._performance]
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
        customer_id = self._resolve_customer_id()
        if customer_id is None:
            self.detail_table.set_rows([])
            return

        start_date, end_date = self._date_range()
        entries = analytics_service.list_customer_detail(customer_id, start_date, end_date)
        self.detail_table.set_rows(
            [
                [
                    entry.production_date.strftime("%d.%m.%Y"),
                    entry.product_name,
                    f"Step {entry.step_no} — {entry.machine_name}",
                    f"{entry.actual_unit_seconds} s",
                    entry.quantity,
                    format_money(entry.price_contribution),
                ]
                for entry in entries
            ]
        )
