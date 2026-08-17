import datetime
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
from app.services import customer_service, machine_service, personnel_service, planning_service, tool_service

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    personnel_id = personnel_service.create_personnel(
        f"Plan Staff {suffix}", "production", D("30000"), 20, 9
    )
    machine_id = machine_service.create_machine(f"Plan Machine {suffix}", D("300"))
    tool_id = tool_service.create_tool(f"Plan Tool {suffix}", 1, D("100"))
    customer_id = customer_service.create_customer(f"Plan Customer {suffix}")

    yield {
        "personnel_id": personnel_id,
        "machine_id": machine_id,
        "tool_id": tool_id,
        "customer_id": customer_id,
    }

    session = get_session()
    try:
        work_order_ids = [
            wo.id
            for wo in session.query(WorkOrder).filter_by(customer_id=customer_id).all()
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
        session.query(WorkOrderStep).filter(
            WorkOrderStep.id.in_(step_ids)
        ).delete(synchronize_session=False)
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


def test_create_work_order_matches_spec_example(scenario):
    steps = [
        planning_service.DraftStep(
            machine_id=scenario["machine_id"],
            unit_process_seconds=60,
            personnel_ids=[scenario["personnel_id"]],
            tools=[planning_service.DraftStepTool(tool_id=scenario["tool_id"], corners_used=2)],
        )
    ]

    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=scenario["customer_id"],
        product_name="Test Product",
        quantity=40,
        raw_material_cost=D("100"),
        profit_percent=D("20"),
        extra_cost=D("0"),
        steps=steps,
    )

    session = get_session()
    try:
        work_order = session.get(WorkOrder, work_order_id)
        step = (
            session.query(WorkOrderStep)
            .filter_by(work_order_id=work_order_id)
            .one()
        )
        step_personnel = (
            session.query(WorkOrderStepPersonnel).filter_by(step_id=step.id).one()
        )
        step_tool = session.query(WorkOrderStepTool).filter_by(step_id=step.id).one()
    finally:
        session.close()

    assert step.step_unit_cost.quantize(D("0.01")) == D("12.78")
    assert work_order.unit_production_cost.quantize(D("0.01")) == D("112.78")

    expected_unit_sale_price = (work_order.unit_production_cost * D("1.20")).quantize(
        D("0.0001"), rounding=decimal.ROUND_HALF_UP
    )
    assert work_order.unit_sale_price == expected_unit_sale_price
    assert work_order.total_price == expected_unit_sale_price * 40

    assert step_personnel.hourly_cost_snapshot == D("166.6667")
    assert step.machine_hourly_cost_snapshot == D("300.0000")
    assert step_tool.price_per_corner_snapshot == D("100.0000")
    assert step_tool.corners_used == 2

    pool = work_order.unit_sale_price - work_order.unit_raw_material_cost
    assert abs(step.unit_net_price_contribution - pool) <= D("0.01")

    work_orders = planning_service.list_work_orders()
    assert work_orders[0].id == work_order_id


def test_work_order_unaffected_by_later_personnel_salary_change(scenario):
    steps = [
        planning_service.DraftStep(
            machine_id=scenario["machine_id"],
            unit_process_seconds=60,
            personnel_ids=[scenario["personnel_id"]],
            tools=[],
        )
    ]

    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=scenario["customer_id"],
        product_name="Test Product 2",
        quantity=10,
        raw_material_cost=D("50"),
        profit_percent=D("10"),
        extra_cost=D("0"),
        steps=steps,
    )

    session = get_session()
    try:
        step_before = (
            session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).one()
        )
        step_personnel_before = (
            session.query(WorkOrderStepPersonnel).filter_by(step_id=step_before.id).one()
        )
        snapshot_before = step_personnel_before.hourly_cost_snapshot
    finally:
        session.close()

    personnel_service.update_personnel(
        scenario["personnel_id"], f"Changed {uuid.uuid4().hex[:4]}", "production", D("60000"), 20, 9
    )

    session = get_session()
    try:
        step_personnel_after = (
            session.query(WorkOrderStepPersonnel).filter_by(step_id=step_before.id).one()
        )
    finally:
        session.close()

    assert step_personnel_after.hourly_cost_snapshot == snapshot_before
    assert snapshot_before == D("166.6667")


def test_delete_work_order_removes_steps_and_related_rows(scenario):
    steps = [
        planning_service.DraftStep(
            machine_id=scenario["machine_id"],
            unit_process_seconds=60,
            personnel_ids=[scenario["personnel_id"]],
            tools=[planning_service.DraftStepTool(tool_id=scenario["tool_id"], corners_used=2)],
        )
    ]
    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=scenario["customer_id"],
        product_name="Product To Delete",
        quantity=10,
        raw_material_cost=D("100"),
        profit_percent=D("20"),
        extra_cost=D("0"),
        steps=steps,
    )

    session = get_session()
    try:
        step_ids = [
            s.id for s in session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).all()
        ]
    finally:
        session.close()

    planning_service.delete_work_order(work_order_id)

    session = get_session()
    try:
        assert session.get(WorkOrder, work_order_id) is None
        assert session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).count() == 0
        assert (
            session.query(WorkOrderStepPersonnel)
            .filter(WorkOrderStepPersonnel.step_id.in_(step_ids))
            .count()
            == 0
        )
        assert (
            session.query(WorkOrderStepTool).filter(WorkOrderStepTool.step_id.in_(step_ids)).count()
            == 0
        )
    finally:
        session.close()

    assert all(o.id != work_order_id for o in planning_service.list_work_orders())


def test_delete_work_order_blocked_when_production_recorded(scenario):
    from app.services import production_service

    steps = [
        planning_service.DraftStep(
            machine_id=scenario["machine_id"],
            unit_process_seconds=60,
            personnel_ids=[scenario["personnel_id"]],
            tools=[],
        )
    ]
    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=scenario["customer_id"],
        product_name="Product With Production Started",
        quantity=10,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=steps,
    )
    step = production_service.list_steps_for_work_order(work_order_id)[0]
    daily_production_id = production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=work_order_id,
        step_id=step.id,
        actual_unit_seconds=60,
        quantity=1,
        personnel_ids=[],
    )

    try:
        with pytest.raises(planning_service.WorkOrderHasProductionRecordsError):
            planning_service.delete_work_order(work_order_id)

        assert any(o.id == work_order_id for o in planning_service.list_work_orders())
    finally:
        production_service.delete_daily_production(daily_production_id)
        planning_service.delete_work_order(work_order_id)


def test_step_tool_cost_recalculates_with_quantity_change():
    tool_costs = [(D("100"), 2)]
    assert planning_service.calculate_step_tool_cost(tool_costs, 40) == D("5.0000")
    assert planning_service.calculate_step_tool_cost(tool_costs, 50) == D("4.0000")
