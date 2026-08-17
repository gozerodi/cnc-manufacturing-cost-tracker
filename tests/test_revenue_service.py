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
from app.services import analytics_service, customer_service, machine_service, planning_service, production_service

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    machine1_id = machine_service.create_machine(f"Rev M1 {suffix}", D("100"))
    machine2_id = machine_service.create_machine(f"Rev M2 {suffix}", D("200"))
    customer_id = customer_service.create_customer(f"Rev Customer {suffix}")

    work_order1_id = planning_service.create_work_order(
        order_date=datetime.date(2099, 1, 8),
        customer_id=customer_id,
        product_name=f"Rev Product1 {suffix}",
        quantity=1,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=[
            planning_service.DraftStep(
                machine_id=machine1_id, unit_process_seconds=3600, personnel_ids=[], tools=[]
            )
        ],
    )
    work_order2_id = planning_service.create_work_order(
        order_date=datetime.date(2099, 1, 8),
        customer_id=customer_id,
        product_name=f"Rev Product2 {suffix}",
        quantity=1,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=[
            planning_service.DraftStep(
                machine_id=machine2_id, unit_process_seconds=3600, personnel_ids=[], tools=[]
            )
        ],
    )

    yield {
        "machine1_id": machine1_id,
        "machine2_id": machine2_id,
        "customer_id": customer_id,
        "work_order1_id": work_order1_id,
        "work_order2_id": work_order2_id,
    }

    session = get_session()
    try:
        for work_order_id in (work_order1_id, work_order2_id):
            step_ids = [
                s.id
                for s in session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).all()
            ]
            daily_production_ids = [
                dp.id
                for dp in session.query(DailyProduction)
                .filter_by(work_order_id=work_order_id)
                .all()
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
        session.query(MachineCost).filter(
            MachineCost.machine_id.in_([machine1_id, machine2_id])
        ).delete(synchronize_session=False)
        session.query(Machine).filter(Machine.id.in_([machine1_id, machine2_id])).delete(
            synchronize_session=False
        )
        session.query(Customer).filter_by(id=customer_id).delete()
        session.commit()
    finally:
        session.close()


def _create_entry(work_order_id, step_id, production_date, actual_unit_seconds, quantity):
    return production_service.create_daily_production(
        production_date=production_date,
        work_order_id=work_order_id,
        step_id=step_id,
        actual_unit_seconds=actual_unit_seconds,
        quantity=quantity,
        personnel_ids=[],
    )


def test_revenue_summary_matches_manual_calculation(scenario):
    step1 = production_service.list_steps_for_work_order(scenario["work_order1_id"])[0]
    step2 = production_service.list_steps_for_work_order(scenario["work_order2_id"])[0]

    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2099, 1, 8), 3600, 2)
    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2099, 1, 4), 1800, 1)
    _create_entry(scenario["work_order2_id"], step2.id, datetime.date(2099, 1, 8), 3600, 1)

    summary = analytics_service.get_revenue_summary(
        datetime.date(2099, 1, 2), datetime.date(2099, 1, 8)
    )

    assert summary.total_quantity == 4
    assert summary.total_price_contribution == D("500.0000")
    assert summary.distinct_machine_count == 2
    assert summary.total_work_seconds == 12600


def test_revenue_summary_respects_day_vs_period(scenario):
    step1 = production_service.list_steps_for_work_order(scenario["work_order1_id"])[0]

    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2099, 1, 8), 3600, 2)
    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2099, 1, 4), 1800, 1)

    day_summary = analytics_service.get_revenue_summary(
        datetime.date(2099, 1, 8), datetime.date(2099, 1, 8)
    )
    assert day_summary.total_quantity == 2

    week_summary = analytics_service.get_revenue_summary(
        analytics_service.period_start_date(datetime.date(2099, 1, 8), "Week"),
        datetime.date(2099, 1, 8),
    )
    assert week_summary.total_quantity == 3


def test_daily_contribution_grouped_by_date(scenario):
    step1 = production_service.list_steps_for_work_order(scenario["work_order1_id"])[0]

    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2099, 1, 8), 3600, 2)
    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2099, 1, 4), 1800, 1)

    daily = analytics_service.list_daily_contribution(
        datetime.date(2099, 1, 2), datetime.date(2099, 1, 8)
    )
    by_date = {item.production_date: item.total_price_contribution for item in daily}

    assert by_date[datetime.date(2099, 1, 8)] == D("200.0000")
    assert by_date[datetime.date(2099, 1, 4)] == D("100.0000")
