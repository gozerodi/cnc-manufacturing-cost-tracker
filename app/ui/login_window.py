import qdarktheme
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.database import get_session
from app.core.security import verify_password
from app.models import User
from app.ui.main_window import MainWindow

THEME_OPTIONS = {
    "System": "auto",
    "Dark": "dark",
    "Light": "light",
}


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNC Manufacturing Cost Tracker - Login")
        self.setMinimumWidth(360)
        self._main_window = None

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self._on_login_clicked)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_OPTIONS.keys())
        self.theme_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.theme_combo.setMinimumContentsLength(10)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        self.login_button = QPushButton("Log In")
        self.login_button.clicked.connect(self._on_login_clicked)

        form_layout = QFormLayout()
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        form_layout.addRow("Theme:", self.theme_combo)

        title_label = QLabel("CNC Manufacturing Cost Tracker")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = title_label.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title_label.setFont(title_font)

        button_row = QHBoxLayout()
        button_row.addWidget(self.login_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(title_label)
        main_layout.addSpacing(12)
        main_layout.addLayout(form_layout)
        main_layout.addSpacing(12)
        main_layout.addLayout(button_row)
        self.setLayout(main_layout)

    def _on_theme_changed(self, theme_label: str) -> None:
        qdarktheme.setup_theme(THEME_OPTIONS[theme_label])

    def _on_login_clicked(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Login Error", "Please enter a username and password.")
            return

        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
        finally:
            session.close()

        if user is None or not verify_password(password, user.password_hash):
            QMessageBox.warning(self, "Login Error", "Incorrect username or password.")
            self.password_input.clear()
            return

        self._main_window = MainWindow(role=user.role, username=user.username)
        self._main_window.show()
        self.close()
