from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QWidget,
)

from app.services import settings_service
from app.ui.pages.admin.customer_performance_page import CustomerPerformancePage
from app.ui.pages.admin.detailed_cost_page import DetailedCostPage
from app.ui.pages.admin.extra_expense_page import ExtraExpensePage
from app.ui.pages.admin.machine_page import MachinePage
from app.ui.pages.admin.machine_performance_page import MachinePerformancePage
from app.ui.pages.admin.order_tracking_page import OrderTrackingPage
from app.ui.pages.admin.personnel_page import PersonnelPage
from app.ui.pages.admin.plan_deviation_page import PlanDeviationPage
from app.ui.pages.admin.report_page import ReportPage
from app.ui.pages.admin.revenue_page import RevenuePage
from app.ui.pages.admin.tool_page import ToolPage
from app.ui.pages.staff.customer_page import CustomerPage
from app.ui.pages.staff.daily_production_page import DailyProductionPage
from app.ui.pages.staff.planning_page import PlanningPage

ADMIN_MENU = [
    ("Setup", ["Personnel Setup 🔒", "Machine Setup", "Tool Setup"]),
    (
        "Analytics",
        [
            "Order Tracking",
            "Planned/Actual",
            "Machine Performance",
            "Customer Performance",
            "Revenue",
        ],
    ),
    ("Costs", ["Add Extra Cost", "Detailed Costs"]),
    ("Report Generation", ["Generate PDF Report"]),
]

STAFF_MENU = [
    ("Setup", ["Customer Setup"]),
    ("Planning", None),
    ("Daily Production Entry", None),
]

PAGE_FACTORIES = {
    "Personnel Setup 🔒": PersonnelPage,
    "Machine Setup": MachinePage,
    "Tool Setup": ToolPage,
    "Customer Setup": CustomerPage,
    "Planning": PlanningPage,
    "Daily Production Entry": DailyProductionPage,
    "Order Tracking": OrderTrackingPage,
    "Planned/Actual": PlanDeviationPage,
    "Machine Performance": MachinePerformancePage,
    "Customer Performance": CustomerPerformancePage,
    "Revenue": RevenuePage,
    "Add Extra Cost": ExtraExpensePage,
    "Detailed Costs": DetailedCostPage,
    "Generate PDF Report": ReportPage,
}

PASSWORD_PROTECTED_LABELS = {"Personnel Setup 🔒"}

PAGE_INDEX_ROLE = Qt.ItemDataRole.UserRole
PROTECTED_ROLE = Qt.ItemDataRole.UserRole + 1
CHILD_INDENT = "    "


def _placeholder_page(title: str) -> QWidget:
    label = QLabel(f"{title}\n\nUnder construction")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    font = label.font()
    font.setPointSize(font.pointSize() + 2)
    label.setFont(font)
    return label


def _welcome_page(username: str, role_label: str) -> QWidget:
    label = QLabel(f"Welcome, {username} ({role_label})\n\nSelect a page from the left menu.")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    font = label.font()
    font.setPointSize(font.pointSize() + 2)
    label.setFont(font)
    return label


def _build_page(label: str) -> QWidget:
    factory = PAGE_FACTORIES.get(label)
    content = _placeholder_page(label) if factory is None else factory()

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setWidget(content)
    return scroll_area


def _page_content(container: QWidget) -> QWidget:
    if isinstance(container, QScrollArea):
        return container.widget()
    return container


class MainWindow(QMainWindow):
    def __init__(self, role: str, username: str):
        super().__init__()
        self.role = role
        self.username = username

        role_label = "Admin" if role == "admin" else "Staff"
        self.setWindowTitle(f"CNC Manufacturing Cost Tracker - {role_label} Panel ({username})")
        self.resize(1000, 650)

        self.menu_list = QListWidget()
        self.menu_list.setMinimumWidth(240)
        self.menu_list.setMaximumWidth(340)
        menu_font = self.menu_list.font()
        menu_font.setPointSize(menu_font.pointSize() + 2)
        self.menu_list.setFont(menu_font)
        self.menu_list.setStyleSheet(
            "QListWidget::item { padding: 8px 6px; margin: 2px 0px; }"
        )

        self.stacked_pages = QStackedWidget()
        self._welcome_page_index = self.stacked_pages.addWidget(
            _welcome_page(username, role_label)
        )

        menu_structure = ADMIN_MENU if role == "admin" else STAFF_MENU
        self._build_menu(menu_structure)
        self.menu_list.itemClicked.connect(self._on_menu_item_clicked)

        splitter = QSplitter()
        splitter.addWidget(self.menu_list)
        splitter.addWidget(self.stacked_pages)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.statusBar().showMessage(f"Logged in as: {username} ({role_label})")

    def _add_header_item(self, label: str) -> None:
        header_item = QListWidgetItem(label)
        header_font = header_item.font()
        header_font.setBold(True)
        header_item.setFont(header_font)
        header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        header_item.setData(PAGE_INDEX_ROLE, None)
        header_item.setBackground(self.palette().alternateBase())
        self.menu_list.addItem(header_item)

    def _add_page_item(self, label: str, display_text: str) -> None:
        page_index = self.stacked_pages.addWidget(_build_page(label))
        item = QListWidgetItem(display_text)
        item.setData(PAGE_INDEX_ROLE, page_index)
        item.setData(PROTECTED_ROLE, label in PASSWORD_PROTECTED_LABELS)
        self.menu_list.addItem(item)

    def _build_menu(self, menu_structure) -> None:
        for label, children in menu_structure:
            if children is None:
                self._add_page_item(label, label)
                continue

            self._add_header_item(label)
            for child_label in children:
                self._add_page_item(child_label, f"{CHILD_INDENT}{child_label}")

        self.stacked_pages.setCurrentIndex(self._welcome_page_index)

    def _on_menu_item_clicked(self, item: QListWidgetItem) -> None:
        page_index = item.data(PAGE_INDEX_ROLE)
        if page_index is None:
            return

        if item.data(PROTECTED_ROLE) and not self._prompt_personnel_page_password():
            return

        content = _page_content(self.stacked_pages.widget(page_index))
        if hasattr(content, "refresh"):
            content.refresh()
        self.stacked_pages.setCurrentIndex(page_index)

    def _prompt_personnel_page_password(self) -> bool:
        password, accepted = QInputDialog.getText(
            self,
            "Password Required",
            "Personnel Setup page password:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return False

        if not settings_service.verify_personnel_page_password(password):
            QMessageBox.warning(self, "Incorrect Password", "The password you entered is incorrect.")
            return False

        return True
