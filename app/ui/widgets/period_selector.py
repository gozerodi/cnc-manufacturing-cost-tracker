from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget

PERIODS = ["Day", "Week", "Month", "3 Months", "6 Months", "1 Year"]


class PeriodSelector(QWidget):
    period_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo = QComboBox()
        self.combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.combo.setMinimumContentsLength(8)
        self.combo.addItems(PERIODS)
        self.combo.currentTextChanged.connect(self.period_changed.emit)
        layout.addWidget(self.combo)

    def current_period(self) -> str:
        return self.combo.currentText()

    def set_current_period(self, period: str) -> None:
        index = self.combo.findText(period)
        if index >= 0:
            self.combo.setCurrentIndex(index)
