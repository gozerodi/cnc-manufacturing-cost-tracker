import dataclasses
import datetime
import decimal

from app.core.database import get_session
from app.models import Personnel
from app.repositories import (
    daily_production_repository,
    machine_cost_repository,
    personnel_cost_repository,
    tool_repository,
    work_order_repository,
    work_order_step_personnel_repository,
    work_order_step_repository,
    work_order_step_tool_repository,
)

QUANTIZE = decimal.Decimal("0.0001")


class WorkOrderHasProductionRecordsError(Exception):
    pass


@dataclasses.dataclass
class DraftStepTool:
    tool_id: int
    corners_used: int


@dataclasses.dataclass
class DraftStep:
    machine_id: int
    unit_process_seconds: int
    personnel_ids: list[int]
    tools: list[DraftStepTool]
    setup_seconds: int = 0


@dataclasses.dataclass
class WorkOrderListItem:
    id: int
    order_date: datetime.date
    customer_name: str
    product_name: str
    quantity: int
    unit_sale_price: decimal.Decimal
    total_price: decimal.Decimal


@dataclasses.dataclass
class WorkOrderStepDetail:
    step_no: int
    machine_name: str
    personnel_names: list[str]


def calculate_step_labor_machine_cost(
    machine_hourly_cost: decimal.Decimal,
    personnel_hourly_costs: list[decimal.Decimal],
    unit_process_seconds: int,
) -> decimal.Decimal:
    hourly_total = machine_hourly_cost + sum(personnel_hourly_costs, decimal.Decimal(0))
    return (hourly_total * decimal.Decimal(unit_process_seconds) / decimal.Decimal(3600)).quantize(
        QUANTIZE, rounding=decimal.ROUND_HALF_UP
    )


def calculate_step_tool_cost(
    tool_costs: list[tuple[decimal.Decimal, int]], quantity: int
) -> decimal.Decimal:
    if not tool_costs:
        return decimal.Decimal("0.0000")
    total = sum(
        (price_per_corner * corners_used for price_per_corner, corners_used in tool_costs),
        decimal.Decimal(0),
    )
    return (total / decimal.Decimal(quantity)).quantize(QUANTIZE, rounding=decimal.ROUND_HALF_UP)


def calculate_step_setup_cost(
    machine_hourly_cost: decimal.Decimal,
    personnel_hourly_costs: list[decimal.Decimal],
    setup_seconds: int,
    quantity: int,
) -> decimal.Decimal:
    """Setup time is not per unit — it's done once for the ENTIRE order.

    The total setup cost (selected personnel + machine hourly cost × setup time)
    is calculated and divided by the order quantity to get the per-unit share
    (same logic as tool cost).
    """
    if not setup_seconds:
        return decimal.Decimal("0.0000")
    hourly_total = machine_hourly_cost + sum(personnel_hourly_costs, decimal.Decimal(0))
    total_setup_cost = hourly_total * decimal.Decimal(setup_seconds) / decimal.Decimal(3600)
    return (total_setup_cost / decimal.Decimal(quantity)).quantize(
        QUANTIZE, rounding=decimal.ROUND_HALF_UP
    )


def calculate_step_unit_cost(
    machine_hourly_cost: decimal.Decimal,
    personnel_hourly_costs: list[decimal.Decimal],
    unit_process_seconds: int,
    tool_costs: list[tuple[decimal.Decimal, int]],
    quantity: int,
    setup_seconds: int = 0,
) -> decimal.Decimal:
    labor_machine_cost = calculate_step_labor_machine_cost(
        machine_hourly_cost, personnel_hourly_costs, unit_process_seconds
    )
    setup_cost = calculate_step_setup_cost(
        machine_hourly_cost, personnel_hourly_costs, setup_seconds, quantity
    )
    tool_cost = calculate_step_tool_cost(tool_costs, quantity)
    return labor_machine_cost + setup_cost + tool_cost


def calculate_unit_production_cost(
    step_unit_costs: list[decimal.Decimal], raw_material_cost: decimal.Decimal
) -> decimal.Decimal:
    return sum(step_unit_costs, decimal.Decimal(0)) + raw_material_cost


def calculate_unit_sale_price(
    unit_production_cost: decimal.Decimal, profit_percent: decimal.Decimal
) -> decimal.Decimal:
    return (
        unit_production_cost * (1 + profit_percent / decimal.Decimal(100))
    ).quantize(QUANTIZE, rounding=decimal.ROUND_HALF_UP)


def calculate_total_price(
    unit_sale_price: decimal.Decimal, quantity: int, extra_cost: decimal.Decimal
) -> decimal.Decimal:
    return unit_sale_price * quantity + extra_cost


def calculate_net_price_contributions(
    step_seconds: list[int], unit_sale_price: decimal.Decimal, raw_material_cost: decimal.Decimal
) -> list[decimal.Decimal]:
    pool = unit_sale_price - raw_material_cost
    total_seconds = sum(step_seconds)
    if total_seconds == 0:
        return [decimal.Decimal("0.0000") for _ in step_seconds]
    return [
        (pool * decimal.Decimal(seconds) / decimal.Decimal(total_seconds)).quantize(
            QUANTIZE, rounding=decimal.ROUND_HALF_UP
        )
        for seconds in step_seconds
    ]


def create_work_order(
    order_date: datetime.date,
    customer_id: int,
    product_name: str,
    quantity: int,
    raw_material_cost: decimal.Decimal,
    profit_percent: decimal.Decimal,
    extra_cost: decimal.Decimal,
    steps: list[DraftStep],
) -> int:
    session = get_session()
    try:
        machine_hourly_costs = []
        personnel_hourly_costs_per_step = []
        tool_costs_per_step = []
        personnel_snapshots_per_step = []
        tool_snapshots_per_step = []

        for step in steps:
            machine_cost = machine_cost_repository.get_latest_for_machine(session, step.machine_id)
            machine_hourly_costs.append(machine_cost.hourly_cost)

            personnel_snapshots = []
            for personnel_id in step.personnel_ids:
                cost = personnel_cost_repository.get_latest_for_personnel(session, personnel_id)
                personnel_snapshots.append((personnel_id, cost.hourly_cost))
            personnel_snapshots_per_step.append(personnel_snapshots)
            personnel_hourly_costs_per_step.append([c for _pid, c in personnel_snapshots])

            tool_snapshots = []
            for tool in step.tools:
                tool_row = tool_repository.get_by_id(session, tool.tool_id)
                tool_snapshots.append((tool.tool_id, tool.corners_used, tool_row.price_per_corner))
            tool_snapshots_per_step.append(tool_snapshots)
            tool_costs_per_step.append(
                [(price, corners) for _tid, corners, price in tool_snapshots]
            )

        step_unit_costs = [
            calculate_step_unit_cost(
                machine_hourly_costs[i],
                personnel_hourly_costs_per_step[i],
                steps[i].unit_process_seconds,
                tool_costs_per_step[i],
                quantity,
                setup_seconds=steps[i].setup_seconds,
            )
            for i in range(len(steps))
        ]

        unit_production_cost = calculate_unit_production_cost(step_unit_costs, raw_material_cost)
        unit_sale_price = calculate_unit_sale_price(unit_production_cost, profit_percent)
        total_price = calculate_total_price(unit_sale_price, quantity, extra_cost)
        contributions = calculate_net_price_contributions(
            [step.unit_process_seconds for step in steps], unit_sale_price, raw_material_cost
        )

        work_order = work_order_repository.create(
            session,
            order_date=order_date,
            customer_id=customer_id,
            product_name=product_name,
            unit_raw_material_cost=raw_material_cost,
            unit_production_cost=unit_production_cost,
            profit_percent=profit_percent,
            unit_sale_price=unit_sale_price,
            quantity=quantity,
            extra_cost=extra_cost,
            total_price=total_price,
        )

        for step_no, step in enumerate(steps, start=1):
            step_row = work_order_step_repository.create(
                session,
                work_order_id=work_order.id,
                step_no=step_no,
                machine_id=step.machine_id,
                unit_process_seconds=step.unit_process_seconds,
                setup_seconds=step.setup_seconds,
                machine_hourly_cost_snapshot=machine_hourly_costs[step_no - 1],
                step_unit_cost=step_unit_costs[step_no - 1],
                unit_net_price_contribution=contributions[step_no - 1],
            )

            for personnel_id, hourly_cost_snapshot in personnel_snapshots_per_step[step_no - 1]:
                work_order_step_personnel_repository.create(
                    session,
                    step_id=step_row.id,
                    personnel_id=personnel_id,
                    hourly_cost_snapshot=hourly_cost_snapshot,
                )

            for tool_id, corners_used, price_per_corner_snapshot in tool_snapshots_per_step[
                step_no - 1
            ]:
                work_order_step_tool_repository.create(
                    session,
                    step_id=step_row.id,
                    tool_id=tool_id,
                    corners_used=corners_used,
                    price_per_corner_snapshot=price_per_corner_snapshot,
                )

        session.commit()
        return work_order.id
    finally:
        session.close()


def list_work_orders() -> list[WorkOrderListItem]:
    session = get_session()
    try:
        rows = work_order_repository.list_all_with_customer(session)
        return [
            WorkOrderListItem(
                id=row.WorkOrder.id,
                order_date=row.WorkOrder.order_date,
                customer_name=row.customer_name,
                product_name=row.WorkOrder.product_name,
                quantity=row.WorkOrder.quantity,
                unit_sale_price=row.WorkOrder.unit_sale_price,
                total_price=row.WorkOrder.total_price,
            )
            for row in rows
        ]
    finally:
        session.close()


def get_work_order_step_details(work_order_id: int) -> list[WorkOrderStepDetail]:
    session = get_session()
    try:
        step_rows = work_order_step_repository.list_by_work_order_with_machine(
            session, work_order_id
        )
        result = []
        for step_row in step_rows:
            step = step_row.WorkOrderStep
            links = work_order_step_personnel_repository.list_for_step(session, step.id)
            personnel_names = []
            for link in links:
                personnel = session.get(Personnel, link.personnel_id)
                if personnel is not None:
                    personnel_names.append(personnel.name)
            result.append(
                WorkOrderStepDetail(
                    step_no=step.step_no,
                    machine_name=step_row.machine_name,
                    personnel_names=personnel_names,
                )
            )
        return result
    finally:
        session.close()


def delete_work_order(work_order_id: int) -> None:
    session = get_session()
    try:
        if daily_production_repository.exists_for_work_order(session, work_order_id):
            raise WorkOrderHasProductionRecordsError(
                "This work order has daily production records and cannot be deleted."
            )

        step_ids = work_order_step_repository.list_ids_by_work_order(session, work_order_id)
        work_order_step_personnel_repository.delete_for_steps(session, step_ids)
        work_order_step_tool_repository.delete_for_steps(session, step_ids)
        work_order_step_repository.delete_for_work_order(session, work_order_id)
        work_order_repository.delete(session, work_order_id)

        session.commit()
    finally:
        session.close()
