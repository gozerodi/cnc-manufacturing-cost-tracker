import decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCompleter,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services import customer_service, machine_service, personnel_service, planning_service, tool_service
from app.ui.pages.staff.work_order_step_dialog import StepDialogResult, WorkOrderStepDialog
from app.ui.widgets import DatePicker, StandardTableWidget, create_full_width_button, format_money
from app.ui.widgets.money_input import MoneyLineEdit, parse_decimal_input

WORK_ORDER_TABLE_HEADERS = ["Date", "Customer", "Product", "Quantity", "Unit Sale Price", "Total Price"]


class PlanningPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps: list[StepDialogResult] = []

        self._machines = []
        self._personnel = []
        self._tools = []
        self._customers = []
        self._machine_cost_by_id: dict[int, decimal.Decimal] = {}
        self._personnel_cost_by_id: dict[int, decimal.Decimal] = {}
        self._tool_price_by_id: dict[int, decimal.Decimal] = {}

        self.date_input = DatePicker()

        self.customer_input = QLineEdit()
        self._customer_completer = QCompleter([])
        self._customer_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.customer_input.setCompleter(self._customer_completer)

        self.product_name_input = QLineEdit()

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 1_000_000)
        self.quantity_input.setSpecialValueText(" ")
        self.quantity_input.valueChanged.connect(self._recalculate)

        self.raw_material_input = MoneyLineEdit()
        self.raw_material_input.textChanged.connect(self._recalculate)

        part1_layout = QFormLayout()
        part1_layout.addRow("Date:", self.date_input)
        part1_layout.addRow("Customer:", self.customer_input)
        part1_layout.addRow("Product Name:", self.product_name_input)
        part1_layout.addRow("Quantity:", self.quantity_input)
        part1_layout.addRow("Unit Raw Material Cost:", self.raw_material_input)

        add_step_button = create_full_width_button("Add Step")
        add_step_button.clicked.connect(self._on_add_step_clicked)

        self.steps_list = QListWidget()
        self.steps_list.itemDoubleClicked.connect(self._on_edit_step)
        self.steps_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.steps_list.customContextMenuRequested.connect(self._show_step_context_menu)
        self.steps_list.setFixedHeight(6 * 30)

        self.profit_percent_input = QLineEdit()
        self.profit_percent_input.setPlaceholderText("e.g. 20")
        self.profit_percent_input.textChanged.connect(self._recalculate)

        self.extra_cost_input = MoneyLineEdit()
        self.extra_cost_input.setText(format_money(decimal.Decimal(0)))
        self.extra_cost_input.textChanged.connect(self._recalculate)

        self.unit_production_cost_label = QLabel(format_money(decimal.Decimal(0)))
        self.unit_sale_price_label = QLabel(format_money(decimal.Decimal(0)))
        self.total_price_label = QLabel(format_money(decimal.Decimal(0)))

        pricing_group = QGroupBox("Pricing")
        pricing_layout = QFormLayout(pricing_group)
        pricing_layout.addRow("Profit Percentage (%):", self.profit_percent_input)
        pricing_layout.addRow("Extra Cost:", self.extra_cost_input)
        pricing_layout.addRow("Unit Production Cost:", self.unit_production_cost_label)
        pricing_layout.addRow("Unit Sale Price:", self.unit_sale_price_label)
        pricing_layout.addRow("Grand Total:", self.total_price_label)

        create_button = create_full_width_button("Create Order")
        create_button.clicked.connect(self._on_create_work_order)

        self.work_orders_table = StandardTableWidget(headers=WORK_ORDER_TABLE_HEADERS, stretch_column=2)
        self.work_orders_table.delete_requested.connect(self._on_delete_work_order)
        self.work_orders_table.edit_requested.connect(self._on_edit_work_order_requested)

        layout = QVBoxLayout(self)
        layout.addLayout(part1_layout)
        layout.addWidget(add_step_button)
        layout.addWidget(self.steps_list)
        layout.addWidget(pricing_group)
        layout.addWidget(create_button)
        layout.addWidget(self.work_orders_table)

        self.refresh()

    def refresh(self) -> None:
        self._machines = machine_service.list_machines()
        self._personnel = personnel_service.list_production_personnel()
        self._tools = tool_service.list_tools()
        self._customers = customer_service.list_customers()

        self._machine_cost_by_id = {m.id: m.hourly_cost for m in self._machines}
        self._personnel_cost_by_id = {p.id: p.hourly_cost for p in self._personnel}
        self._tool_price_by_id = {t.id: t.price_per_corner for t in self._tools}

        self._customer_completer = QCompleter([c.name for c in self._customers])
        self._customer_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.customer_input.setCompleter(self._customer_completer)

        self._work_orders = planning_service.list_work_orders()
        work_orders = self._work_orders
        self.work_orders_table.set_rows(
            [
                [
                    item.order_date.strftime("%d.%m.%Y"),
                    item.customer_name,
                    item.product_name,
                    item.quantity,
                    format_money(item.unit_sale_price),
                    format_money(item.total_price),
                ]
                for item in work_orders
            ],
            row_tooltips=[self._build_work_order_tooltip(item.id) for item in work_orders],
            tooltip_column=2,
        )

        self._recalculate()

    def _build_work_order_tooltip(self, work_order_id: int) -> str:
        details = planning_service.get_work_order_step_details(work_order_id)
        if not details:
            return "No processing steps"
        lines = []
        for detail in details:
            personnel_text = ", ".join(detail.personnel_names) if detail.personnel_names else "—"
            lines.append(f"Step {detail.step_no} — {detail.machine_name}\nPersonnel: {personnel_text}")
        return "\n".join(lines)

    def _on_edit_work_order_requested(self, _row: int) -> None:
        QMessageBox.information(
            self,
            "No Editing",
            "Created work orders cannot be edited (cost/price records are locked). "
            "You can delete an incorrectly entered work order and recreate it.",
        )

    def _on_delete_work_order(self, row: int) -> None:
        work_order = self._work_orders[row]
        confirm = QMessageBox.question(
            self,
            "Delete Work Order",
            f"Are you sure you want to delete the work order '{work_order.product_name}' "
            f"({work_order.customer_name})?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            planning_service.delete_work_order(work_order.id)
        except planning_service.WorkOrderHasProductionRecordsError as exc:
            QMessageBox.warning(self, "Cannot Delete", str(exc))
            return

        self.refresh()

    def _resolve_customer_id(self) -> int | None:
        typed_name = self.customer_input.text().strip()
        if not typed_name:
            return None
        for customer in self._customers:
            if customer.name == typed_name:
                return customer.id
        for customer in self._customers:
            if customer.name.lower() == typed_name.lower():
                return customer.id
        return None

    def _on_add_step_clicked(self) -> None:
        if self.quantity_input.value() < 1:
            QMessageBox.warning(self, "Missing Information", "Please enter a quantity first.")
            return
        if self._resolve_customer_id() is None:
            QMessageBox.warning(self, "Missing Information", "Please select a valid customer from the list.")
            return
        if not self._machines:
            QMessageBox.warning(self, "Missing Information", "You must define at least one machine first.")
            return

        dialog = WorkOrderStepDialog(self._machines, self._personnel, self._tools, parent=self)
        if dialog.exec() and dialog.result_step is not None:
            self._steps.append(dialog.result_step)
            self._refresh_steps_list()
            self._recalculate()

    def _on_edit_step(self, item) -> None:
        row = self.steps_list.row(item)
        existing = self._steps[row]
        dialog = WorkOrderStepDialog(
            self._machines, self._personnel, self._tools, initial=existing, parent=self
        )
        if dialog.exec() and dialog.result_step is not None:
            self._steps[row] = dialog.result_step
            self._refresh_steps_list()
            self._recalculate()

    def _show_step_context_menu(self, position) -> None:
        item = self.steps_list.itemAt(position)
        if item is None:
            return
        menu = QMenu(self)
        edit_action = menu.addAction("Update")
        delete_action = menu.addAction("Delete")
        chosen = menu.exec(self.steps_list.viewport().mapToGlobal(position))
        if chosen == edit_action:
            self._on_edit_step(item)
        elif chosen == delete_action:
            row = self.steps_list.row(item)
            del self._steps[row]
            self._refresh_steps_list()
            self._recalculate()

    def _refresh_steps_list(self) -> None:
        self.steps_list.clear()
        for step_no, step in enumerate(self._steps, start=1):
            self.steps_list.addItem(f"Step {step_no} — {step.machine_name}")

    def _recalculate(self, *_args) -> None:
        quantity = self.quantity_input.value()
        raw_material_cost = self.raw_material_input.value()
        profit_percent = parse_decimal_input(self.profit_percent_input.text())
        extra_cost = self.extra_cost_input.value()

        if quantity < 1 or raw_material_cost is None or profit_percent is None or not self._steps:
            self.unit_production_cost_label.setText(format_money(decimal.Decimal(0)))
            self.unit_sale_price_label.setText(format_money(decimal.Decimal(0)))
            self.total_price_label.setText(format_money(decimal.Decimal(0)))
            return

        if extra_cost is None:
            extra_cost = decimal.Decimal(0)

        step_unit_costs = []
        for step in self._steps:
            machine_hourly = self._machine_cost_by_id.get(step.machine_id, decimal.Decimal(0))
            personnel_hourly_costs = [
                self._personnel_cost_by_id.get(pid, decimal.Decimal(0)) for pid in step.personnel_ids
            ]
            tool_costs = [
                (self._tool_price_by_id.get(t.tool_id, decimal.Decimal(0)), t.corners_used)
                for t in step.tools
            ]
            step_unit_costs.append(
                planning_service.calculate_step_unit_cost(
                    machine_hourly,
                    personnel_hourly_costs,
                    step.unit_process_seconds,
                    tool_costs,
                    quantity,
                    setup_seconds=step.setup_seconds,
                )
            )

        unit_production_cost = planning_service.calculate_unit_production_cost(
            step_unit_costs, raw_material_cost
        )
        unit_sale_price = planning_service.calculate_unit_sale_price(unit_production_cost, profit_percent)
        total_price = planning_service.calculate_total_price(unit_sale_price, quantity, extra_cost)

        self.unit_production_cost_label.setText(format_money(unit_production_cost))
        self.unit_sale_price_label.setText(format_money(unit_sale_price))
        self.total_price_label.setText(format_money(total_price))

    def _on_create_work_order(self) -> None:
        product_name = self.product_name_input.text().strip()
        quantity = self.quantity_input.value()
        raw_material_cost = self.raw_material_input.value()
        profit_percent = parse_decimal_input(self.profit_percent_input.text())
        extra_cost = self.extra_cost_input.value() or decimal.Decimal(0)
        customer_id = self._resolve_customer_id()

        if not product_name:
            QMessageBox.warning(self, "Missing Information", "Product name cannot be empty.")
            return
        if quantity < 1:
            QMessageBox.warning(self, "Missing Information", "Please enter a quantity.")
            return
        if customer_id is None:
            QMessageBox.warning(self, "Missing Information", "Please select a valid customer from the list.")
            return
        if raw_material_cost is None:
            QMessageBox.warning(self, "Missing Information", "Unit raw material cost must be a valid number.")
            return
        if profit_percent is None:
            QMessageBox.warning(self, "Missing Information", "Profit percentage must be a valid number.")
            return
        if not self._steps:
            QMessageBox.warning(self, "Missing Information", "You must add at least one processing step.")
            return

        draft_steps = [
            planning_service.DraftStep(
                machine_id=step.machine_id,
                unit_process_seconds=step.unit_process_seconds,
                setup_seconds=step.setup_seconds,
                personnel_ids=list(step.personnel_ids),
                tools=[
                    planning_service.DraftStepTool(tool_id=t.tool_id, corners_used=t.corners_used)
                    for t in step.tools
                ],
            )
            for step in self._steps
        ]

        planning_service.create_work_order(
            order_date=self.date_input.date().toPython(),
            customer_id=customer_id,
            product_name=product_name,
            quantity=quantity,
            raw_material_cost=raw_material_cost,
            profit_percent=profit_percent,
            extra_cost=extra_cost,
            steps=draft_steps,
        )

        self.product_name_input.clear()
        self.customer_input.clear()
        self.quantity_input.setValue(0)
        self.raw_material_input.clear()
        self.profit_percent_input.clear()
        self.extra_cost_input.setText(format_money(decimal.Decimal(0)))
        self._steps = []
        self._refresh_steps_list()
        self.refresh()
