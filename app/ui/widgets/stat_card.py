from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


def create_stat_card(title: str, value: str) -> QFrame:
    card = QFrame()
    card.setObjectName("statCard")
    card.setStyleSheet(
        "#statCard {"
        "  background-color: palette(alternate-base);"
        "  border-radius: 12px;"
        "}"
    )

    title_label = QLabel(title)
    title_label.setWordWrap(True)
    title_label.setStyleSheet("color: palette(mid);")

    value_label = QLabel(value)
    value_font = value_label.font()
    value_font.setPointSize(value_font.pointSize() + 6)
    value_font.setBold(True)
    value_label.setFont(value_font)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(8)
    layout.addWidget(title_label)
    layout.addWidget(value_label)

    card.value_label = value_label
    return card
