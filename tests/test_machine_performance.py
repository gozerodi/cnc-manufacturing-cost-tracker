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
from app.services import analytics_service, customer_service, machine_service, planning_service

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    machine1_id = machine_service.create_machine(f"Perf M1 {suffix}", D("100"))
    machine2_id = machine_service.create_machine(f"Perf M2 {suffix}", D("200"))
    customer_id = customer_service.create_customer(f"Perf Customer {suffix}")

    work_order1_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=customer_id,
        product_name=f"Perf Product1 {suffix}",
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
        order_date=datetime.date(2026, 7, 24),
        customer_id=customer_id,
        product_name=f"Perf Product2 {suffix}",
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
        "product_name1": f"Perf Product1 {suffix}",
        "product_name2": f"Perf Product2 {suffix}",
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
    from app.services import production_service

    return production_service.create_daily_production(
        production_date=production_date,
        work_order_id=work_order_id,
        step_id=step_id,
        actual_unit_seconds=actual_unit_seconds,
        quantity=quantity,
        personnel_ids=[],
    )


def test_machine_performance_matches_manual_calculation(scenario):
    from app.services import production_service

    step1 = production_service.list_steps_for_work_order(scenario["work_order1_id"])[0]
    step2 = production_service.list_steps_for_work_order(scenario["work_order2_id"])[0]

    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2026, 7, 24), 3600, 2)
    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2026, 7, 24), 1800, 1)
    _create_entry(scenario["work_order2_id"], step2.id, datetime.date(2026, 7, 24), 3600, 1)

    results = analytics_service.list_machine_performance(
        datetime.date(2026, 7, 24), datetime.date(2026, 7, 24)
    )
    m1 = next(r for r in results if r.machine_id == scenario["machine1_id"])
    m2 = next(r for r in results if r.machine_id == scenario["machine2_id"])

    assert m1.total_price_contribution == D("300.0000")
    assert m1.hourly_return == D("120.0000")
    assert m2.total_price_contribution == D("200.0000")
    assert m2.hourly_return == D("200.0000")

    assert results.index(m2) < results.index(m1)


def test_machine_performance_respects_date_range(scenario):
    from app.services import production_service

    step1 = production_service.list_steps_for_work_order(scenario["work_order1_id"])[0]

    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2026, 7, 24), 3600, 1)
    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2026, 1, 1), 3600, 5)

    results = analytics_service.list_machine_performance(
        datetime.date(2026, 7, 24), datetime.date(2026, 7, 24)
    )
    m1 = next(r for r in results if r.machine_id == scenario["machine1_id"])
    assert m1.total_price_contribution == D("100.0000")


def test_machine_detail_filters_by_machine_and_date(scenario):
    from app.services import production_service

    step1 = production_service.list_steps_for_work_order(scenario["work_order1_id"])[0]
    step2 = production_service.list_steps_for_work_order(scenario["work_order2_id"])[0]

    _create_entry(scenario["work_order1_id"], step1.id, datetime.date(2026, 7, 24), 3600, 2)
    _create_entry(scenario["work_order2_id"], step2.id, datetime.date(2026, 7, 24), 3600, 1)

    entries = analytics_service.list_machine_detail(
        scenario["machine1_id"], datetime.date(2026, 7, 24), datetime.date(2026, 7, 24)
    )
    assert len(entries) == 1
    assert entries[0].product_name == scenario["product_name1"]
