import datetime
import decimal
import uuid

import pytest

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
from app.ui.pages.admin.order_tracking_page import OrderTrackingPage

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    personnel_id = personnel_service.create_personnel(
        f"Page Analytics Staff {suffix}", "production", D("30000"), 20, 9
    )
    machine_id = machine_service.create_machine(f"Page Analytics Machine {suffix}", D("300"))
    customer_id = customer_service.create_customer(f"Page Analytics Customer {suffix}")

    steps = [
        planning_service.DraftStep(
            machine_id=machine_id, unit_process_seconds=60, personnel_ids=[personnel_id], tools=[]
        )
    ]
    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=customer_id,
        product_name=f"Page Analytics Product {suffix}",
        quantity=10,
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
        "product_name": f"Page Analytics Product {suffix}",
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


def _find_row_for_product(page: OrderTrackingPage, product_name: str) -> int:
    for row in range(page.active_table.rowCount()):
        if product_name in page.active_table.item(row, 0).text():
            return row
    raise AssertionError(f"No row found for {product_name}")


def test_segment_switches_between_active_and_completed(qapp, scenario):
    page = OrderTrackingPage()
    assert page.pages.currentIndex() == 0

    page.segmented_control.set_current_index(1)
    page._on_segment_changed(1)
    assert page.pages.currentIndex() == 1


def test_active_progress_shown_with_progress_bar(qapp, scenario):
    work_order_id = scenario["work_order_id"]
    step = production_service.list_steps_for_work_order(work_order_id)[0]
    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step.id,
        actual_unit_seconds=60,
        quantity=4,
        personnel_ids=[],
    )

    page = OrderTrackingPage()
    row = _find_row_for_product(page, scenario["product_name"])

    assert page.active_table.item(row, 2).text() == "4/10"
    progress_bar = page.active_table.cellWidget(row, 3)
    assert progress_bar is not None
    assert progress_bar.value() == 4
    assert progress_bar.maximum() == 10


def test_completed_order_appears_only_in_completed_tab(qapp, scenario):
    work_order_id = scenario["work_order_id"]
    step = production_service.list_steps_for_work_order(work_order_id)[0]
    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step.id,
        actual_unit_seconds=60,
        quantity=10,
        personnel_ids=[],
    )

    page = OrderTrackingPage()

    for row in range(page.active_table.rowCount()):
        assert scenario["product_name"] not in page.active_table.item(row, 0).text()

    matching = [
        row
        for row in range(page.completed_table.row_count())
        if page.completed_table.model.item(row, 1).text() == scenario["product_name"]
    ]
    assert len(matching) == 1
    assert page.completed_table.model.item(matching[0], 3).text() != ""
