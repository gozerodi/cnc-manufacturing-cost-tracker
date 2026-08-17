from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit


class DatePicker(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("dd.MM.yyyy")
        self.setDate(QDate.currentDate())
