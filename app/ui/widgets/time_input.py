from PySide6.QtWidgets import QLineEdit

from app.core.time_parser import TimeParseError, format_seconds, is_valid_time_input, parse_time_to_seconds

INVALID_STYLE = "border: 1px solid #e53935;"


class TimeLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("e.g. 1.30 (mm.ss) or 01.15.00 (hh.mm.ss)")
        self.textChanged.connect(self._update_style)

    def _update_style(self, text: str) -> None:
        if text == "" or is_valid_time_input(text):
            self.setStyleSheet("")
        else:
            self.setStyleSheet(INVALID_STYLE)

    def is_valid(self) -> bool:
        return is_valid_time_input(self.text())

    def seconds(self) -> int | None:
        try:
            return parse_time_to_seconds(self.text())
        except TimeParseError:
            return None

    def set_seconds(self, seconds: int) -> None:
        self.setText(format_seconds(seconds))
