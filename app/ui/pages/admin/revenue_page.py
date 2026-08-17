import decimal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from app.services import analytics_service
from app.ui.widgets import DateRangeFilter, create_stat_card, format_money


def _format_hours_minutes(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours}:{minutes:02d}"


class RevenuePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.date_filter = DateRangeFilter()
        self.date_filter.range_changed.connect(self.refresh)

        self.quantity_card = create_stat_card("Total Quantity Produced", "0")
        self.contribution_card = create_stat_card(
            "Total Net Price Contribution", format_money(decimal.Decimal(0))
        )
        self.machine_card = create_stat_card("Distinct Machines Used", "0")
        self.duration_card = create_stat_card("Total Processing Time (h:mm)", "0:00")

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)
        for card in (
            self.quantity_card,
            self.contribution_card,
            self.machine_card,
            self.duration_card,
        ):
            cards_layout.addWidget(card)

        self.figure = Figure(figsize=(6, 3))
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout = QVBoxLayout(self)
        layout.addWidget(self.date_filter)
        layout.addLayout(cards_layout)
        layout.addWidget(self.canvas)

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
        summary = analytics_service.get_revenue_summary(start_date, end_date)

        self.quantity_card.value_label.setText(str(summary.total_quantity))
        self.contribution_card.value_label.setText(
            format_money(summary.total_price_contribution)
        )
        self.machine_card.value_label.setText(str(summary.distinct_machine_count))
        self.duration_card.value_label.setText(_format_hours_minutes(summary.total_work_seconds))

        self._draw_chart(start_date, end_date)

    def _draw_chart(self, start_date, end_date) -> None:
        self.figure.clear()
        self.figure.patch.set_alpha(0)

        if start_date == end_date:
            self.canvas.draw()
            return

        daily = analytics_service.list_daily_contribution(start_date, end_date)
        if not daily:
            self.canvas.draw()
            return

        text_color = self.palette().color(self.foregroundRole()).name()

        axes = self.figure.add_subplot(111)
        axes.set_facecolor("none")

        dates = [item.production_date.strftime("%d.%m") for item in daily]
        values = [float(item.total_price_contribution) for item in daily]

        x_positions = range(len(values))
        axes.bar(x_positions, values, color="#a8d5ba", width=0.5)
        axes.set_xticks(list(x_positions))
        axes.set_xticklabels(dates)

        min_slots = 5
        axes.set_xlim(-0.5, max(len(values), min_slots) - 0.5)

        axes.tick_params(colors=text_color)
        for spine in axes.spines.values():
            spine.set_color(text_color)
        axes.set_ylabel("Net Price Contribution", color=text_color)
        self.figure.tight_layout()
        self.canvas.draw()
