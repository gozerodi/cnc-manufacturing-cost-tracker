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
from app.services import analytics_service, customer_service, machine_service, personnel_service, planning_service, production_service

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    personnel_id = personnel_service.create_personnel(
        f"Analytics Staff {suffix}", "production", D("30000"), 20, 9
    )
    machine_id = machine_service.create_machine(f"Analytics Machine {suffix}", D("300"))
    customer_id = customer_service.create_customer(f"Analytics Customer {suffix}")

    steps = [
        planning_service.DraftStep(
            machine_id=machine_id, unit_process_seconds=60, personnel_ids=[personnel_id], tools=[]
        ),
        planning_service.DraftStep(
            machine_id=machine_id, unit_process_seconds=90, personnel_ids=[personnel_id], tools=[]
        ),
    ]
    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=customer_id,
        product_name=f"Analytics Product {suffix}",
        quantity=40,
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


def test_active_order_step_progress_matches_spec_example(scenario):
    work_order_id = scenario["work_order_id"]
    steps = production_service.list_steps_for_work_order(work_order_id)
    step1, step2 = steps[0], steps[1]

    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step1.id,
        actual_unit_seconds=60,
        quantity=40,
        personnel_ids=[],
    )
    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step2.id,
        actual_unit_seconds=90,
        quantity=20,
        personnel_ids=[],
    )

    orders = analytics_service.list_active_order_progress()
    order = next(o for o in orders if o.work_order_id == work_order_id)

    assert order.quantity == 40
    assert len(order.steps) == 2
    assert order.steps[0].step_no == 1
    assert order.steps[0].produced_quantity == 40
    assert order.steps[0].target_quantity == 40
    assert order.steps[1].step_no == 2
    assert order.steps[1].produced_quantity == 20
    assert order.steps[1].target_quantity == 40


def test_order_moves_to_completed_tab_with_completion_date(scenario):
    work_order_id = scenario["work_order_id"]
    steps = production_service.list_steps_for_work_order(work_order_id)
    step1, step2 = steps[0], steps[1]

    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step1.id,
        actual_unit_seconds=60,
        quantity=40,
        personnel_ids=[],
    )

    active_orders = analytics_service.list_active_order_progress()
    assert any(o.work_order_id == work_order_id for o in active_orders)
    completed_orders = analytics_service.list_completed_orders()
    assert all(o.work_order_id != work_order_id for o in completed_orders)

    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 25),
        work_order_id=work_order_id,
        step_id=step2.id,
        actual_unit_seconds=90,
        quantity=40,
        personnel_ids=[],
    )

    active_orders = analytics_service.list_active_order_progress()
    assert all(o.work_order_id != work_order_id for o in active_orders)

    completed_orders = analytics_service.list_completed_orders()
    completed = next(o for o in completed_orders if o.work_order_id == work_order_id)
    assert completed.completed_at is not None


def test_deviation_cost_matches_spec_example(scenario):
    work_order_id = scenario["work_order_id"]
    step1 = production_service.list_steps_for_work_order(work_order_id)[0]
    assert step1.step_no == 1

    daily_production_id = production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step1.id,
        actual_unit_seconds=120,
        quantity=20,
        personnel_ids=[],
    )

    session = get_session()
    try:
        step_row = session.get(WorkOrderStep, step1.id)
        personnel_snapshot_total = (
            session.query(WorkOrderStepPersonnel)
            .filter_by(step_id=step1.id)
            .first()
            .hourly_cost_snapshot
        )
        hourly_total = personnel_snapshot_total + step_row.machine_hourly_cost_snapshot
    finally:
        session.close()

    expected_deviation = (hourly_total * D(2400 - 1200) / D(3600)).quantize(D("0.0001"))

    records = analytics_service.list_deviation_records()
    record = next(r for r in records if r.daily_production_id == daily_production_id)
    assert record.deviation_cost == expected_deviation
    assert record.planned_unit_seconds == 60
    assert record.actual_unit_seconds == 120
    assert record.quantity == 20


def test_records_matching_plan_do_not_appear_in_deviation_list(scenario):
    work_order_id = scenario["work_order_id"]
    step1 = production_service.list_steps_for_work_order(work_order_id)[0]

    daily_production_id = production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step1.id,
        actual_unit_seconds=60,
        quantity=5,
        personnel_ids=[],
    )

    records = analytics_service.list_deviation_records()
    assert all(r.daily_production_id != daily_production_id for r in records)
