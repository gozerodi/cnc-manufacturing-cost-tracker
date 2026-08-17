from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget


def create_full_width_button(text: str, parent: QWidget | None = None) -> QPushButton:
    button = QPushButton(text, parent)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    button.setMinimumHeight(36)
    return button
