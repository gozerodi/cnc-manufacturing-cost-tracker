import decimal

from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services import analytics_service, cost_service, machine_service
from app.ui.widgets import (
    DateRangeFilter,
    MonthYearSelector,
    SegmentedControl,
    StandardTableWidget,
    create_stat_card,
    format_money,
)

GENERAL_TABLE_HEADERS = ["Category", "Amount"]
ALL_MACHINES_LABEL = "All"

# Visual weight exponent so small slices don't become too thin to select in the pie chart:
# wedges are drawn using amount^POWER instead of the real amount. Percentage labels are
# still computed from the real amounts; only the wedge area is exaggerated this way.
_WEDGE_VISUAL_WEIGHT_POWER = 0.6


def _pastel_colors(count: int) -> list:
    if count == 0:
        return []
    cmap = colormaps["Pastel1"]
    return [cmap(i % cmap.N) for i in range(count)]


class DetailedCostPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.segmented_control = SegmentedControl(["General", "Machine"])
        self.segmented_control.current_changed.connect(self._on_segment_changed)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_general_module())
        self.pages.addWidget(self._build_machine_module())

        layout = QVBoxLayout(self)
        layout.addWidget(self.segmented_control)
        layout.addWidget(self.pages)

        self.refresh()

    def _build_general_module(self) -> QWidget:
        widget = QWidget()

        self.general_month_selector = MonthYearSelector()
        self.general_month_selector.month_changed.connect(self._refresh_general)

        form_layout = QFormLayout()
        form_layout.addRow("Month:", self.general_month_selector)

        self.general_figure = Figure(figsize=(7.2, 4.4))
        self.general_canvas = FigureCanvasQTAgg(self.general_figure)
        self.general_canvas.setFixedSize(720, 440)

        self.general_table = StandardTableWidget(headers=GENERAL_TABLE_HEADERS, stretch_column=0)

        chart_layout = QHBoxLayout()
        chart_layout.addStretch(1)
        chart_layout.addWidget(self.general_canvas)
        chart_layout.addStretch(1)

        layout = QVBoxLayout(widget)
        layout.addLayout(form_layout)
        layout.addLayout(chart_layout)
        layout.addWidget(self.general_table)
        return widget

    def _build_machine_module(self) -> QWidget:
        widget = QWidget()

        self.machine_date_filter = DateRangeFilter()
        self.machine_date_filter.range_changed.connect(self._refresh_machine)

        self.machine_combo = QComboBox()
        self.machine_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.machine_combo.setMinimumContentsLength(16)
        self.machine_combo.currentIndexChanged.connect(self._refresh_machine)

        machine_filter_layout = QFormLayout()
        machine_filter_layout.addRow("Machine:", self.machine_combo)

        self.working_cost_card = create_stat_card(
            "Working Cost", format_money(decimal.Decimal(0))
        )
        self.special_cost_card = create_stat_card(
            "Linked Special Expenses", format_money(decimal.Decimal(0))
        )
        self.total_cost_card = create_stat_card(
            "Total Machine Cost", format_money(decimal.Decimal(0))
        )

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)
        for card in (self.working_cost_card, self.special_cost_card, self.total_cost_card):
            cards_layout.addWidget(card)

        layout = QVBoxLayout(widget)
        layout.addWidget(self.machine_date_filter)
        layout.addLayout(machine_filter_layout)
        # About 5 rows of spacing so the dropdown has room to open over the cards
        # comfortably as it grows (e.g. once there are 15 machines).
        layout.addSpacing(130)
        layout.addLayout(cards_layout)
        layout.addStretch(1)
        return widget

    def _on_segment_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def refresh(self) -> None:
        self._refresh_general()
        self._refresh_machine_combo()
        self._refresh_machine()

    def _refresh_machine_combo(self) -> None:
        current_id = self.machine_combo.currentData()
        self.machine_combo.blockSignals(True)
        self.machine_combo.clear()
        self.machine_combo.addItem(ALL_MACHINES_LABEL, None)
        for machine in machine_service.list_machines():
            self.machine_combo.addItem(machine.name, machine.id)
        if current_id is not None:
            index = self.machine_combo.findData(current_id)
            if index >= 0:
                self.machine_combo.setCurrentIndex(index)
        self.machine_combo.blockSignals(False)

    def _refresh_general(self, *_args) -> None:
        year, month = self.general_month_selector.selected_year_month()
        breakdown = cost_service.get_general_cost_breakdown(year, month)

        self.general_table.set_rows(
            [
                [category.label, format_money(category.amount)]
                for category in breakdown.categories
            ]
        )
        self._draw_general_pie_chart(breakdown)

    def _draw_general_pie_chart(self, breakdown: cost_service.GeneralCostBreakdown) -> None:
        self.general_figure.clear()
        self.general_figure.patch.set_alpha(0)

        categories = [c for c in breakdown.categories if c.amount > 0]
        if not categories:
            self.general_canvas.draw()
            return

        text_color = self.palette().color(self.foregroundRole()).name()

        axes = self.general_figure.add_subplot(111)
        axes.set_facecolor("none")

        labels = [category.label for category in categories]
        values = [float(category.amount) for category in categories]
        colors = _pastel_colors(len(values))

        total = sum(values)
        real_percentages = [value / total * 100 for value in values]
        wedge_sizes = [value**_WEDGE_VISUAL_WEIGHT_POWER for value in values]

        percent_iter = iter(real_percentages)

        def _autopct(_pct: float) -> str:
            return f"{next(percent_iter):.1f}%"

        wedges, _texts, _autotexts = axes.pie(
            wedge_sizes,
            autopct=_autopct,
            colors=colors,
            pctdistance=0.7,
            # Pastel wedge colors are always light, so the percentage labels are drawn with
            # a fixed dark color instead of the theme color (otherwise white text is
            # unreadable on a light pastel background in dark mode).
            textprops={"color": "#2b2b2b", "fontsize": 9},
            wedgeprops={"linewidth": 0},
        )
        axes.axis("equal")
        axes.legend(
            wedges,
            labels,
            loc="upper left",
            bbox_to_anchor=(1.02, 1.0),
            fontsize=9,
            frameon=False,
            labelcolor=text_color,
        )
        self.general_figure.subplots_adjust(top=0.95, bottom=0.05, left=0.05, right=0.62)
        self.general_canvas.draw()

    def _refresh_machine(self, *_args) -> None:
        machine_id = self.machine_combo.currentData()
        start_date, end_date = self._machine_date_range()
        detail = cost_service.get_machine_cost_detail(machine_id, start_date, end_date)

        self.working_cost_card.value_label.setText(format_money(detail.working_cost))
        self.special_cost_card.value_label.setText(
            format_money(detail.special_expenses_total)
        )
        self.total_cost_card.value_label.setText(format_money(detail.total))

    def _machine_date_range(self):
        if self.machine_date_filter.source == "month":
            return self.machine_date_filter.month_selector.date_range()
        end_date = self.machine_date_filter.date_input.date().toPython()
        start_date = analytics_service.period_start_date(
            end_date, self.machine_date_filter.period_selector.current_period()
        )
        return start_date, end_date
