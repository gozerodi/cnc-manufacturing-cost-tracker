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

D = decimal.Decimal


@pytest.fixture
def work_order_scenario():
    suffix = uuid.uuid4().hex[:8]
    personnel_id = personnel_service.create_personnel(
        f"Prod Staff {suffix}", "production", D("30000"), 20, 9
    )
    machine_id = machine_service.create_machine(f"Prod Machine {suffix}", D("300"))
    customer_id = customer_service.create_customer(f"Prod Customer {suffix}")

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
        product_name=f"Prod Product {suffix}",
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
    }

    session = get_session()
    try:
        step_ids = [
            s.id
            for s in session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).all()
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


def test_active_work_order_appears_in_selection_list(work_order_scenario):
    work_order_id = work_order_scenario["work_order_id"]
    options = production_service.list_active_work_orders()
    assert any(o.id == work_order_id for o in options)


def test_price_contribution_matches_locked_contribution_times_quantity(work_order_scenario):
    work_order_id = work_order_scenario["work_order_id"]
    steps = production_service.list_steps_for_work_order(work_order_id)
    first_step = steps[0]

    daily_production_id = production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=first_step.id,
        actual_unit_seconds=60,
        quantity=3,
        personnel_ids=[],
    )

    entries = production_service.list_daily_productions_for_date(datetime.date(2026, 7, 24))
    entry = next(e for e in entries if e.id == daily_production_id)

    expected = (first_step.unit_net_price_contribution * 3).quantize(D("0.0001"))
    assert entry.price_contribution == expected


def test_completion_at_ten_not_at_nine(work_order_scenario):
    work_order_id = work_order_scenario["work_order_id"]
    steps = production_service.list_steps_for_work_order(work_order_id)
    last_step = steps[-1]

    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=last_step.id,
        actual_unit_seconds=90,
        quantity=9,
        personnel_ids=[],
    )

    session = get_session()
    try:
        work_order = session.get(WorkOrder, work_order_id)
        assert work_order.status == "active"
    finally:
        session.close()

    last_id = production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 25),
        work_order_id=work_order_id,
        step_id=last_step.id,
        actual_unit_seconds=90,
        quantity=1,
        personnel_ids=[],
    )

    session = get_session()
    try:
        work_order = session.get(WorkOrder, work_order_id)
        assert work_order.status == "completed"
        assert work_order.completed_at is not None
    finally:
        session.close()

    options = production_service.list_active_work_orders()
    assert all(o.id != work_order_id for o in options)

    production_service.delete_daily_production(last_id)

    session = get_session()
    try:
        work_order = session.get(WorkOrder, work_order_id)
        assert work_order.status == "active"
        assert work_order.completed_at is None
    finally:
        session.close()


def test_multiple_entries_on_same_step_across_different_days(work_order_scenario):
    work_order_id = work_order_scenario["work_order_id"]
    steps = production_service.list_steps_for_work_order(work_order_id)
    first_step = steps[0]

    id_day1 = production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=first_step.id,
        actual_unit_seconds=60,
        quantity=4,
        personnel_ids=[],
    )
    id_day2 = production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 25),
        work_order_id=work_order_id,
        step_id=first_step.id,
        actual_unit_seconds=60,
        quantity=6,
        personnel_ids=[],
    )

    session = get_session()
    try:
        rows = (
            session.query(DailyProduction)
            .filter_by(work_order_id=work_order_id, step_id=first_step.id)
            .order_by(DailyProduction.production_date)
            .all()
        )
    finally:
        session.close()

    assert [r.id for r in rows] == [id_day1, id_day2]
    assert [r.production_date for r in rows] == [datetime.date(2026, 7, 24), datetime.date(2026, 7, 25)]
    assert sum(r.quantity for r in rows) == 10
