import datetime
import decimal
import uuid

import pytest
from PySide6.QtGui import QColor

from app.core.database import get_session
from app.models import (
    Customer,
    DailyProduction,
    DailyProductionPersonnel,
    Machine,
    MachineCost,
    Personnel,
    PersonnelCost,
    WorkOrder,
    WorkOrderStep,
    WorkOrderStepPersonnel,
    WorkOrderStepTool,
)
from app.services import customer_service, machine_service, personnel_service, planning_service, production_service
from app.ui.pages.admin.plan_deviation_page import FASTER_COLOR, SLOWER_COLOR, PlanDeviationPage

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    personnel_id = personnel_service.create_personnel(
        f"Deviation Staff {suffix}", "production", D("30000"), 20, 9
    )
    machine_id = machine_service.create_machine(f"Deviation Machine {suffix}", D("300"))
    customer_id = customer_service.create_customer(f"Deviation Customer {suffix}")

    steps = [
        planning_service.DraftStep(
            machine_id=machine_id, unit_process_seconds=60, personnel_ids=[personnel_id], tools=[]
        )
    ]
    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=customer_id,
        product_name=f"Deviation Product {suffix}",
        quantity=100,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=steps,
    )

    yield {
        "personnel_id": personnel_id,
        "machine_id": machine_id,
        "customer_id": customer_id,
        "work_order_id": work_order_id,
        "product_name": f"Deviation Product {suffix}",
    }

    session = get_session()
    try:
        step_ids = [
            s.id for s in session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).all()
        ]
        daily_production_ids = [
            dp.id for dp in session.query(DailyProduction).filter_by(work_order_id=work_order_id).all()
        ]
        session.query(DailyProductionPersonnel).filter(
            DailyProductionPersonnel.daily_production_id.in_(daily_production_ids)
        ).delete(synchronize_session=False)
        session.query(DailyProduction).filter_by(work_order_id=work_order_id).delete()
        session.query(WorkOrderStepPersonnel).filter(
            WorkOrderStepPersonnel.step_id.in_(step_ids)
        ).delete(synchronize_session=False)
        session.query(WorkOrderStepTool).filter(
            WorkOrderStepTool.step_id.in_(step_ids)
        ).delete(synchronize_session=False)
        session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).delete()
        session.query(WorkOrder).filter_by(id=work_order_id).delete()
        session.query(PersonnelCost).filter_by(personnel_id=personnel_id).delete()
        session.query(Personnel).filter_by(id=personnel_id).delete()
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.query(Customer).filter_by(id=customer_id).delete()
        session.commit()
    finally:
        session.close()


def _find_row(page: PlanDeviationPage, product_name: str) -> int:
    for row in range(page.table.rowCount()):
        if product_name in page.table.item(row, 0).text():
            return row
    raise AssertionError(f"No deviation row found for {product_name}")


def test_slower_than_plan_shown_in_red(qapp, scenario):
    work_order_id = scenario["work_order_id"]
    step = production_service.list_steps_for_work_order(work_order_id)[0]

    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step.id,
        actual_unit_seconds=120,
        quantity=5,
        personnel_ids=[],
    )

    page = PlanDeviationPage()
    row = _find_row(page, scenario["product_name"])

    assert page.table.item(row, 2).text() == "60 s"
    assert page.table.item(row, 3).text() == "120 s"
    cost_item = page.table.item(row, 5)
    assert cost_item.foreground().color() == SLOWER_COLOR
    assert cost_item.text().strip().startswith("-")


def test_faster_than_plan_shown_in_green(qapp, scenario):
    work_order_id = scenario["work_order_id"]
    step = production_service.list_steps_for_work_order(work_order_id)[0]

    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step.id,
        actual_unit_seconds=30,
        quantity=5,
        personnel_ids=[],
    )

    page = PlanDeviationPage()
    row = _find_row(page, scenario["product_name"])

    cost_item = page.table.item(row, 5)
    assert cost_item.foreground().color() == FASTER_COLOR
    assert cost_item.text().strip().startswith("+")


def test_on_plan_entry_not_listed(qapp, scenario):
    work_order_id = scenario["work_order_id"]
    step = production_service.list_steps_for_work_order(work_order_id)[0]

    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step.id,
        actual_unit_seconds=60,
        quantity=5,
        personnel_ids=[],
    )

    page = PlanDeviationPage()
    for row in range(page.table.rowCount()):
        assert scenario["product_name"] not in page.table.item(row, 0).text()
