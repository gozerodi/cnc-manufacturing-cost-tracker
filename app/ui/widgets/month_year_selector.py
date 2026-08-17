import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

YEARS_BEFORE = 5
YEARS_AFTER = 1


class MonthYearSelector(QWidget):
    month_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.month_combo = QComboBox()
        self.month_combo.addItems(MONTH_NAMES)
        self.month_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.month_combo.setMinimumContentsLength(9)

        self.year_combo = QComboBox()
        current_year = datetime.date.today().year
        for year in range(current_year - YEARS_BEFORE, current_year + YEARS_AFTER + 1):
            self.year_combo.addItem(str(year))
        self.year_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.year_combo.setMinimumContentsLength(6)

        today = datetime.date.today()
        self.month_combo.setCurrentIndex(today.month - 1)
        self.year_combo.setCurrentText(str(today.year))

        self.month_combo.currentIndexChanged.connect(lambda _index: self.month_changed.emit())
        self.year_combo.currentIndexChanged.connect(lambda _index: self.month_changed.emit())

        layout.addWidget(self.month_combo)
        layout.addWidget(self.year_combo)

    def selected_year_month(self) -> tuple[int, int]:
        return int(self.year_combo.currentText()), self.month_combo.currentIndex() + 1

    def date_range(self) -> tuple[datetime.date, datetime.date]:
        year, month = self.selected_year_month()
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year, 12, 31)
        else:
            end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        return start_date, end_date

    def set_year_month(self, year: int, month: int) -> None:
        self.year_combo.setCurrentText(str(year))
        self.month_combo.setCurrentIndex(month - 1)
