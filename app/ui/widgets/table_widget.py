from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHeaderView, QMenu, QSizePolicy, QTableView, QVBoxLayout, QWidget

VISIBLE_ROWS_DEFAULT = 15


class StandardTableWidget(QWidget):
    """Rows are provided by the caller already sorted newest-first."""

    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(
        self,
        headers: list[str],
        stretch_column: int | None = None,
        visible_rows: int = VISIBLE_ROWS_DEFAULT,
        parent=None,
    ):
        super().__init__(parent)

        self.model = QStandardItemModel(0, len(headers))
        self.model.setHorizontalHeaderLabels(headers)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_double_clicked)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        row_height = self.table.verticalHeader().defaultSectionSize()
        header_height = self.table.horizontalHeader().sizeHint().height()
        self.table.setMinimumHeight(header_height + row_height * visible_rows)

        header = self.table.horizontalHeader()
        for column in range(len(headers)):
            if stretch_column is not None and column == stretch_column:
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)

    def set_rows(
        self,
        rows: list[list[str]],
        row_tooltips: list[str] | None = None,
        tooltip_column: int = 0,
    ) -> None:
        self.model.setRowCount(0)
        for row_index, row_values in enumerate(rows):
            items = []
            for column_index, value in enumerate(row_values):
                text = str(value)
                item = QStandardItem(text)
                item.setEditable(False)
                if row_tooltips is not None and column_index == tooltip_column:
                    item.setToolTip(row_tooltips[row_index])
                else:
                    item.setToolTip(text)
                items.append(item)
            self.model.appendRow(items)

    def row_count(self) -> int:
        return self.model.rowCount()

    def _on_double_clicked(self, index) -> None:
        self.edit_requested.emit(index.row())

    def _show_context_menu(self, position) -> None:
        index = self.table.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        chosen_action = menu.exec(self.table.viewport().mapToGlobal(position))

        if chosen_action == edit_action:
            self.edit_requested.emit(index.row())
        elif chosen_action == delete_action:
            self.delete_requested.emit(index.row())
