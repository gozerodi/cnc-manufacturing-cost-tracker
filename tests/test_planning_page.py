import decimal
import uuid

import pytest

from app.core.database import get_session
from app.models import (
    Customer,
    DailyProduction,
    Machine,
    MachineCost,
    Personnel,
    PersonnelCost,
    Tool,
    WorkOrder,
    WorkOrderStep,
    WorkOrderStepPersonnel,
    WorkOrderStepTool,
)
from app.services import customer_service, machine_service, personnel_service, tool_service
from app.ui.pages.staff.planning_page import PlanningPage
from app.ui.pages.staff.work_order_step_dialog import SelectedTool, StepDialogResult

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    personnel_id = personnel_service.create_personnel(
        f"Page Staff {suffix}", "production", D("30000"), 20, 9
    )
    machine_id = machine_service.create_machine(f"Page Machine {suffix}", D("300"))
    tool_id = tool_service.create_tool(f"Page Tool {suffix}", 1, D("100"))
    customer_id = customer_service.create_customer(f"Page Customer {suffix}")

    yield {
        "personnel_id": personnel_id,
        "personnel_name": f"Page Staff {suffix}",
        "machine_id": machine_id,
        "tool_id": tool_id,
        "customer_id": customer_id,
        "customer_name": f"Page Customer {suffix}",
    }

    session = get_session()
    try:
        work_order_ids = [
            wo.id for wo in session.query(WorkOrder).filter_by(customer_id=customer_id).all()
        ]
        step_ids = [
            s.id
            for s in session.query(WorkOrderStep)
            .filter(WorkOrderStep.work_order_id.in_(work_order_ids))
            .all()
        ]
        session.query(DailyProduction).filter(
            DailyProduction.work_order_id.in_(work_order_ids)
        ).delete(synchronize_session=False)
        session.query(WorkOrderStepPersonnel).filter(
            WorkOrderStepPersonnel.step_id.in_(step_ids)
        ).delete(synchronize_session=False)
        session.query(WorkOrderStepTool).filter(
            WorkOrderStepTool.step_id.in_(step_ids)
        ).delete(synchronize_session=False)
        session.query(WorkOrderStep).filter(WorkOrderStep.id.in_(step_ids)).delete(
            synchronize_session=False
        )
        session.query(WorkOrder).filter(WorkOrder.id.in_(work_order_ids)).delete(
            synchronize_session=False
        )
        session.query(PersonnelCost).filter_by(personnel_id=personnel_id).delete()
        session.query(Personnel).filter_by(id=personnel_id).delete()
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.query(Tool).filter_by(id=tool_id).delete()
        session.query(Customer).filter_by(id=customer_id).delete()
        session.commit()
    finally:
        session.close()


def test_live_panel_matches_manual_calculation(qapp, scenario):
    page = PlanningPage()

    page.quantity_input.setValue(40)
    page.raw_material_input.setText("100")
    page.profit_percent_input.setText("20")

    step = StepDialogResult(
        machine_id=scenario["machine_id"],
        machine_name="Page Machine",
        unit_process_seconds=60,
        personnel_ids=[scenario["personnel_id"]],
        tools=[SelectedTool(tool_id=scenario["tool_id"], tool_name="Page Tool", corners_used=2)],
    )
    page._steps.append(step)
    page._refresh_steps_list()
    page._recalculate()

    assert page.steps_list.item(0).text() == "Step 1 — Page Machine"
    assert page.unit_production_cost_label.text() == "$112.78"
    assert page.unit_sale_price_label.text() == "$135.33"


def test_quantity_change_updates_tool_cost_live(qapp, scenario):
    page = PlanningPage()
    page.quantity_input.setValue(40)
    page.raw_material_input.setText("0")
    page.profit_percent_input.setText("0")

    step = StepDialogResult(
        machine_id=scenario["machine_id"],
        machine_name="Page Machine",
        unit_process_seconds=0,
        personnel_ids=[],
        tools=[SelectedTool(tool_id=scenario["tool_id"], tool_name="Page Tool", corners_used=2)],
    )
    page._steps.append(step)
    page._refresh_steps_list()
    page._recalculate()
    cost_at_40 = page.unit_production_cost_label.text()

    page.quantity_input.setValue(50)
    cost_at_50 = page.unit_production_cost_label.text()

    assert cost_at_40 == "$5.00"
    assert cost_at_50 == "$4.00"


def test_create_work_order_via_page(qapp, scenario):
    page = PlanningPage()

    page.customer_input.setText(scenario["customer_name"])
    page.product_name_input.setText("Page Product")
    page.quantity_input.setValue(40)
    page.raw_material_input.setText("100")
    page.profit_percent_input.setText("20")

    step = StepDialogResult(
        machine_id=scenario["machine_id"],
        machine_name="Page Machine",
        unit_process_seconds=60,
        personnel_ids=[scenario["personnel_id"]],
        tools=[SelectedTool(tool_id=scenario["tool_id"], tool_name="Page Tool", corners_used=2)],
    )
    page._steps.append(step)
    page._refresh_steps_list()

    page._on_create_work_order()

    assert page.work_orders_table.row_count() >= 1
    assert page.work_orders_table.model.item(0, 2).text() == "Page Product"
    assert page.work_orders_table.model.item(0, 3).text() == "40"
    assert len(page._steps) == 0
    assert page.product_name_input.text() == ""

    tooltip = page.work_orders_table.model.item(0, 2).toolTip()
    assert "Step 1 — Page Machine" in tooltip
    assert scenario["personnel_name"] in tooltip
    assert "Page Tool" not in tooltip


def test_add_step_blocked_without_quantity(qapp, monkeypatch, scenario):
    warnings = []
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    page = PlanningPage()
    assert page.quantity_input.value() == 0

    page._on_add_step_clicked()

    assert len(warnings) == 1
    assert len(page._steps) == 0


def test_add_step_blocked_without_valid_customer(qapp, monkeypatch, scenario):
    import app.ui.pages.staff.planning_page as planning_page_module

    warnings = []
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    dialog_opened = []

    class FakeDialog:
        def __init__(self, *a, **k):
            dialog_opened.append(True)

        def exec(self):
            return False

    monkeypatch.setattr(planning_page_module, "WorkOrderStepDialog", FakeDialog)

    page = PlanningPage()
    page.quantity_input.setValue(10)
    page.customer_input.setText("Nonexistent Customer XYZ")

    page._on_add_step_clicked()

    assert len(warnings) == 1
    assert dialog_opened == []
    assert len(page._steps) == 0


def test_add_step_allowed_with_valid_selected_customer(qapp, monkeypatch, scenario):
    import app.ui.pages.staff.planning_page as planning_page_module

    warnings = []
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    dialog_opened = []

    class FakeDialog:
        def __init__(self, *a, **k):
            dialog_opened.append(True)
            self.result_step = None

        def exec(self):
            return False

    monkeypatch.setattr(planning_page_module, "WorkOrderStepDialog", FakeDialog)

    page = PlanningPage()
    page.quantity_input.setValue(10)
    page.customer_input.setText(scenario["customer_name"])

    page._on_add_step_clicked()

    assert len(warnings) == 0
    assert dialog_opened == [True]


def test_create_work_order_requires_at_least_one_step(qapp, monkeypatch, scenario):
    warnings = []
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    page = PlanningPage()
    page.customer_input.setText(scenario["customer_name"])
    page.product_name_input.setText("Stepless Product")
    page.quantity_input.setValue(10)
    page.raw_material_input.setText("10")
    page.profit_percent_input.setText("10")

    page._on_create_work_order()

    assert len(warnings) == 1


def test_delete_work_order_via_page(qapp, monkeypatch, scenario):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )

    page = PlanningPage()
    page.customer_input.setText(scenario["customer_name"])
    page.product_name_input.setText("Page Product To Delete")
    page.quantity_input.setValue(10)
    page.raw_material_input.setText("10")
    page.profit_percent_input.setText("10")

    step = StepDialogResult(
        machine_id=scenario["machine_id"],
        machine_name="Page Machine",
        unit_process_seconds=60,
        personnel_ids=[scenario["personnel_id"]],
        tools=[],
    )
    page._steps.append(step)
    page._refresh_steps_list()
    page._on_create_work_order()

    row_index = next(
        i for i, wo in enumerate(page._work_orders) if wo.product_name == "Page Product To Delete"
    )
    page._on_delete_work_order(row_index)

    assert all(wo.product_name != "Page Product To Delete" for wo in page._work_orders)


def test_edit_work_order_shows_locked_message(qapp, monkeypatch, scenario):
    from PySide6.QtWidgets import QMessageBox

    page = PlanningPage()
    page.customer_input.setText(scenario["customer_name"])
    page.product_name_input.setText("Locked Page Product")
    page.quantity_input.setValue(10)
    page.raw_material_input.setText("10")
    page.profit_percent_input.setText("10")

    step = StepDialogResult(
        machine_id=scenario["machine_id"],
        machine_name="Page Machine",
        unit_process_seconds=60,
        personnel_ids=[scenario["personnel_id"]],
        tools=[],
    )
    page._steps.append(step)
    page._refresh_steps_list()
    page._on_create_work_order()

    row_index = next(
        i for i, wo in enumerate(page._work_orders) if wo.product_name == "Locked Page Product"
    )

    infos = []
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: infos.append(a))
    )
    page._on_edit_work_order_requested(row_index)

    assert len(infos) == 1

    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )
    page._on_delete_work_order(row_index)


def test_only_production_personnel_available_for_steps(qapp, scenario):
    admin_id = personnel_service.create_personnel(
        f"Administrative {uuid.uuid4().hex[:8]}", "administrative", D("20000"), 22, 8
    )
    try:
        page = PlanningPage()
        assert all(p.type == "production" for p in page._personnel)
        assert all(p.id != admin_id for p in page._personnel)
        assert any(p.id == scenario["personnel_id"] for p in page._personnel)
    finally:
        session = get_session()
        try:
            session.query(PersonnelCost).filter_by(personnel_id=admin_id).delete()
            session.query(Personnel).filter_by(id=admin_id).delete()
            session.commit()
        finally:
            session.close()


def test_edit_step_updates_existing_draft_step(qapp, scenario):
    page = PlanningPage()
    step = StepDialogResult(
        machine_id=scenario["machine_id"],
        machine_name="Page Machine",
        unit_process_seconds=60,
        personnel_ids=[scenario["personnel_id"]],
        tools=[],
    )
    page._steps.append(step)
    page._refresh_steps_list()

    item = page.steps_list.item(0)

    class FakeDialog:
        def __init__(self, machines, personnel, tools, initial=None, parent=None):
            self.result_step = StepDialogResult(
                machine_id=initial.machine_id,
                machine_name=initial.machine_name,
                unit_process_seconds=999,
                personnel_ids=initial.personnel_ids,
                tools=initial.tools,
            )

        def exec(self):
            return True

    import app.ui.pages.staff.planning_page as planning_page_module

    original_dialog_cls = planning_page_module.WorkOrderStepDialog
    planning_page_module.WorkOrderStepDialog = FakeDialog
    try:
        page._on_edit_step(item)
    finally:
        planning_page_module.WorkOrderStepDialog = original_dialog_cls

    assert page._steps[0].unit_process_seconds == 999
