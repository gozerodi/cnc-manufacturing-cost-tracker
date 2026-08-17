from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox

from app.ui.widgets.date_picker import DatePicker
from app.ui.widgets.month_year_selector import MonthYearSelector
from app.ui.widgets.period_selector import PeriodSelector


class DateRangeFilter(QGroupBox):
    """`source` reflects the most recently changed control ('day_period'/'month')."""

    range_changed = Signal()

    def __init__(self, parent=None):
        super().__init__("Filter", parent)

        self.date_input = DatePicker()
        self.period_selector = PeriodSelector()
        self.month_selector = MonthYearSelector()
        self.source = "day_period"

        self.date_input.dateChanged.connect(self._on_day_period_changed)
        self.period_selector.period_changed.connect(self._on_day_period_changed)
        self.month_selector.month_changed.connect(self._on_month_changed)

        layout = QFormLayout(self)
        layout.addRow("Day:", self.date_input)
        layout.addRow("Period:", self.period_selector)
        layout.addRow("Month:", self.month_selector)

    def _on_day_period_changed(self, *_args) -> None:
        self.source = "day_period"
        self.range_changed.emit()

    def _on_month_changed(self) -> None:
        self.source = "month"
        self.range_changed.emit()
