import dataclasses

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.services import personnel_service
from app.ui.widgets.time_input import TimeLineEdit

FIELD_MIN_WIDTH = 320
VISIBLE_PERSONNEL_ROWS = 10
PERSONNEL_ROW_HEIGHT = 28


@dataclasses.dataclass
class SelectedTool:
    tool_id: int
    tool_name: str
    corners_used: int


@dataclasses.dataclass
class StepDialogResult:
    machine_id: int
    machine_name: str
    unit_process_seconds: int
    personnel_ids: list[int]
    tools: list[SelectedTool]
    setup_seconds: int = 0


class WorkOrderStepDialog(QDialog):
    def __init__(self, machines, personnel_list, tools, initial: StepDialogResult | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Step")
        self._tools_catalog = tools
        self._selected_tools: list[SelectedTool] = list(initial.tools) if initial else []

        self.machine_combo = QComboBox()
        self.machine_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.machine_combo.setMinimumContentsLength(12)
        self.machine_combo.setMinimumWidth(FIELD_MIN_WIDTH)
        for machine in machines:
            self.machine_combo.addItem(machine.name, machine.id)
        if initial is not None:
            index = self.machine_combo.findData(initial.machine_id)
            if index >= 0:
                self.machine_combo.setCurrentIndex(index)

        initial_personnel_ids = set(initial.personnel_ids) if initial else set()
        self.personnel_list = QListWidget()
        self.personnel_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.personnel_list.setFixedHeight(VISIBLE_PERSONNEL_ROWS * PERSONNEL_ROW_HEIGHT)
        for person in personnel_list:
            item = QListWidgetItem(f"{person.name} ({personnel_service.TYPE_LABELS[person.type]})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if person.id in initial_personnel_ids else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, person.id)
            self.personnel_list.addItem(item)

        self.seconds_input = TimeLineEdit()
        self.seconds_input.setMinimumWidth(FIELD_MIN_WIDTH)
        if initial is not None:
            self.seconds_input.set_seconds(initial.unit_process_seconds)

        self.setup_seconds_input = TimeLineEdit()
        self.setup_seconds_input.setMinimumWidth(FIELD_MIN_WIDTH)
        self.setup_seconds_input.setPlaceholderText(
            "e.g. 1.00.00 (optional, one-time setup time for the entire order)"
        )
        if initial is not None and initial.setup_seconds:
            self.setup_seconds_input.set_seconds(initial.setup_seconds)

        self.tool_combo = QComboBox()
        self.tool_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.tool_combo.setMinimumContentsLength(12)
        for tool in tools:
            self.tool_combo.addItem(tool.name, tool.id)
        self.corners_input = QSpinBox()
        self.corners_input.setRange(1, 1_000_000)

        add_tool_button = QPushButton("Add Tool")
        add_tool_button.clicked.connect(self._on_add_tool)
        remove_tool_button = QPushButton("Remove Selected Tool")
        remove_tool_button.clicked.connect(self._on_remove_tool)

        self.tools_list = QListWidget()
        for selected_tool in self._selected_tools:
            self.tools_list.addItem(f"{selected_tool.tool_name} — {selected_tool.corners_used} corners")

        tool_row_layout = QHBoxLayout()
        tool_row_layout.addWidget(self.tool_combo)
        tool_row_layout.addWidget(self.corners_input)
        tool_row_layout.addWidget(add_tool_button)

        form_layout = QFormLayout()
        form_layout.addRow("Machine:", self.machine_combo)
        form_layout.addRow("Unit Processing Time:", self.seconds_input)
        form_layout.addRow("Setup Time (one-time):", self.setup_seconds_input)
        form_layout.addRow("Personnel:", self.personnel_list)
        form_layout.addRow("Add Tool:", tool_row_layout)
        form_layout.addRow("Added Tools:", self.tools_list)
        form_layout.addRow(remove_tool_button)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

        self.result_step: StepDialogResult | None = None

    def _on_add_tool(self) -> None:
        tool_id = self.tool_combo.currentData()
        if tool_id is None:
            return
        tool_name = self.tool_combo.currentText()
        corners_used = self.corners_input.value()

        self._selected_tools.append(SelectedTool(tool_id, tool_name, corners_used))
        self.tools_list.addItem(f"{tool_name} — {corners_used} corners")

    def _on_remove_tool(self) -> None:
        row = self.tools_list.currentRow()
        if row < 0:
            return
        self.tools_list.takeItem(row)
        del self._selected_tools[row]

    def _on_accept(self) -> None:
        machine_id = self.machine_combo.currentData()
        if machine_id is None:
            QMessageBox.warning(self, "Missing Information", "You must define a machine first.")
            return

        if not self.seconds_input.is_valid() or self.seconds_input.seconds() is None:
            QMessageBox.warning(self, "Missing Information", "Enter a valid unit processing time.")
            return

        setup_text = self.setup_seconds_input.text().strip()
        if not setup_text:
            setup_seconds = 0
        elif self.setup_seconds_input.is_valid():
            setup_seconds = self.setup_seconds_input.seconds()
        else:
            QMessageBox.warning(self, "Missing Information", "Enter a valid setup time.")
            return

        personnel_ids = []
        for i in range(self.personnel_list.count()):
            item = self.personnel_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                personnel_ids.append(item.data(Qt.ItemDataRole.UserRole))

        self.result_step = StepDialogResult(
            machine_id=machine_id,
            machine_name=self.machine_combo.currentText(),
            unit_process_seconds=self.seconds_input.seconds(),
            personnel_ids=personnel_ids,
            tools=list(self._selected_tools),
            setup_seconds=setup_seconds,
        )
        self.accept()
