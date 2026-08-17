from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget


class SegmentedControl(QWidget):
    current_changed = Signal(int)

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._buttons: list[QPushButton] = []

        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setMinimumHeight(32)
            layout.addWidget(button)
            self._button_group.addButton(button, index)
            self._buttons.append(button)

        if self._buttons:
            self._buttons[0].setChecked(True)

        self._button_group.idClicked.connect(self.current_changed.emit)

    def current_index(self) -> int:
        return self._button_group.checkedId()

    def set_current_index(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
