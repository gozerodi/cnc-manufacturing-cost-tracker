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
    WorkOrder,
    WorkOrderStep,
    WorkOrderStepPersonnel,
    WorkOrderStepTool,
)
from app.services import customer_service, machine_service, planning_service, production_service
from app.ui.pages.admin.revenue_page import RevenuePage

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    machine_id = machine_service.create_machine(f"PageRev M {suffix}", D("100"))
    customer_id = customer_service.create_customer(f"PageRev Customer {suffix}")

    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2099, 2, 8),
        customer_id=customer_id,
        product_name=f"PageRev Product {suffix}",
        quantity=1,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=[
            planning_service.DraftStep(
                machine_id=machine_id, unit_process_seconds=3600, personnel_ids=[], tools=[]
            )
        ],
    )

    yield {
        "machine_id": machine_id,
        "customer_id": customer_id,
        "work_order_id": work_order_id,
    }

    session = get_session()
    try:
        step_ids = [
            s.id for s in session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).all()
        ]
        daily_production_ids = [
            dp.id
            for dp in session.query(DailyProduction).filter_by(work_order_id=work_order_id).all()
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
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.query(Customer).filter_by(id=customer_id).delete()
        session.commit()
    finally:
        session.close()


def _set_date(page, date_str):
    page.date_filter.date_input.setDate(page.date_filter.date_input.date().fromString(date_str, "dd.MM.yyyy"))


def test_cards_update_and_day_period_switch(qapp, scenario):
    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(2099, 2, 8),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=3,
        personnel_ids=[],
    )
    production_service.create_daily_production(
        production_date=datetime.date(2099, 2, 4),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=1800,
        quantity=1,
        personnel_ids=[],
    )

    page = RevenuePage()
    _set_date(page, "08.02.2099")
    page.date_filter.period_selector.set_current_period("Day")
    page.refresh()

    assert page.quantity_card.value_label.text() == "3"
    assert page.contribution_card.value_label.text() == "$300.00"
    assert page.machine_card.value_label.text() == "1"
    assert page.duration_card.value_label.text() == "3:00"

    page.date_filter.period_selector.set_current_period("Week")
    page.refresh()

    assert page.quantity_card.value_label.text() == "4"
    assert page.contribution_card.value_label.text() == "$400.00"
    assert page.duration_card.value_label.text() == "3:30"
    assert len(page.figure.axes) == 1


def test_month_filter_shows_only_selected_month(qapp, scenario):
    isolated_year = datetime.date.today().year - 5

    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(isolated_year, 1, 15),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=2,
        personnel_ids=[],
    )
    production_service.create_daily_production(
        production_date=datetime.date(isolated_year, 2, 15),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=5,
        personnel_ids=[],
    )

    page = RevenuePage()
    page.date_filter.month_selector.set_year_month(isolated_year, 1)

    assert page.date_filter.source == "month"
    assert page.quantity_card.value_label.text() == "2"

    page.date_filter.month_selector.set_year_month(isolated_year, 2)

    assert page.quantity_card.value_label.text() == "5"
