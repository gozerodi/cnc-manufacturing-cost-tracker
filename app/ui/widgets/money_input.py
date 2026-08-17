import decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit

INVALID_STYLE = "border: 1px solid #e53935;"


def parse_decimal_input(text: str) -> decimal.Decimal | None:
    cleaned = text.strip().replace("$", "").replace(",", "").strip()
    if cleaned == "":
        return None
    try:
        return decimal.Decimal(cleaned)
    except decimal.InvalidOperation:
        return None


def format_decimal(value: decimal.Decimal) -> str:
    quantized = value.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)
    return f"{quantized:,.2f}"


def format_money(value: decimal.Decimal) -> str:
    return f"${format_decimal(value)}"


class MoneyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("0.00")
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.textChanged.connect(self._update_style)
        self.editingFinished.connect(self._reformat)

    def _update_style(self, text: str) -> None:
        if text == "" or parse_decimal_input(text) is not None:
            self.setStyleSheet("")
        else:
            self.setStyleSheet(INVALID_STYLE)

    def _reformat(self) -> None:
        value = self.value()
        if value is not None:
            self.set_value(value)

    def is_valid(self) -> bool:
        return self.text() == "" or parse_decimal_input(self.text()) is not None

    def value(self) -> decimal.Decimal | None:
        return parse_decimal_input(self.text())

    def set_value(self, value: decimal.Decimal) -> None:
        self.setText(format_money(value))
