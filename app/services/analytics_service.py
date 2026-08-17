import dataclasses
import datetime
import decimal

from app.core.database import get_session
from app.models import Customer
from app.repositories import (
    daily_production_repository,
    machine_repository,
    work_order_repository,
    work_order_step_personnel_repository,
    work_order_step_repository,
)

DEVIATION_QUANTIZE = decimal.Decimal("0.0001")
PERFORMANCE_QUANTIZE = decimal.Decimal("0.0001")
MAX_PERFORMANCE_ROWS = 10


def period_start_date(selected_date: datetime.date, period: str) -> datetime.date:
    if period == "Day":
        return selected_date
    if period == "Week":
        return selected_date - datetime.timedelta(days=6)
    months_by_period = {"Month": 1, "3 Months": 3, "6 Months": 6, "1 Year": 12}
    months = months_by_period.get(period)
    if months is not None:
        return _subtract_months(selected_date, months)
    return selected_date


def _subtract_months(date_value: datetime.date, months: int) -> datetime.date:
    month_index = date_value.month - 1 - months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date_value.day, days_in_month(year, month))
    return datetime.date(year, month, day)


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    return (next_month - datetime.date(year, month, 1)).days


@dataclasses.dataclass
class StepProgress:
    step_no: int
    machine_name: str
    produced_quantity: int
    target_quantity: int


@dataclasses.dataclass
class OrderProgress:
    work_order_id: int
    customer_name: str
    product_name: str
    quantity: int
    steps: list[StepProgress]


@dataclasses.dataclass
class CompletedOrder:
    work_order_id: int
    customer_name: str
    product_name: str
    quantity: int
    completed_at: datetime.datetime | None


@dataclasses.dataclass
class DeviationRecord:
    daily_production_id: int
    customer_name: str
    product_name: str
    step_no: int
    machine_name: str
    planned_unit_seconds: int
    actual_unit_seconds: int
    quantity: int
    deviation_cost: decimal.Decimal


@dataclasses.dataclass
class MachinePerformance:
    machine_id: int
    machine_name: str
    hourly_return: decimal.Decimal
    total_price_contribution: decimal.Decimal


@dataclasses.dataclass
class MachineDetailEntry:
    id: int
    production_date: datetime.date
    customer_name: str
    product_name: str
    step_no: int
    actual_unit_seconds: int
    quantity: int
    price_contribution: decimal.Decimal


@dataclasses.dataclass
class CustomerPerformance:
    customer_id: int
    customer_name: str
    hourly_return: decimal.Decimal
    total_price_contribution: decimal.Decimal


@dataclasses.dataclass
class CustomerDetailEntry:
    id: int
    production_date: datetime.date
    product_name: str
    step_no: int
    machine_name: str
    actual_unit_seconds: int
    quantity: int
    price_contribution: decimal.Decimal


@dataclasses.dataclass
class RevenueSummary:
    total_quantity: int
    total_price_contribution: decimal.Decimal
    distinct_machine_count: int
    total_work_seconds: int


@dataclasses.dataclass
class DailyContribution:
    production_date: datetime.date
    total_price_contribution: decimal.Decimal


def list_active_order_progress() -> list[OrderProgress]:
    session = get_session()
    try:
        rows = work_order_repository.list_active_with_customer(session)
        result = []
        for row in rows:
            work_order = row.WorkOrder
            step_rows = work_order_step_repository.list_by_work_order_with_machine(
                session, work_order.id
            )
            steps = [
                StepProgress(
                    step_no=step_row.WorkOrderStep.step_no,
                    machine_name=step_row.machine_name,
                    produced_quantity=daily_production_repository.sum_quantity_for_step(
                        session, work_order.id, step_row.WorkOrderStep.id
                    ),
                    target_quantity=work_order.quantity,
                )
                for step_row in step_rows
            ]
            result.append(
                OrderProgress(
                    work_order_id=work_order.id,
                    customer_name=row.customer_name,
                    product_name=work_order.product_name,
                    quantity=work_order.quantity,
                    steps=steps,
                )
            )
        return result
    finally:
        session.close()


def list_completed_orders() -> list[CompletedOrder]:
    session = get_session()
    try:
        rows = work_order_repository.list_completed_with_customer(session)
        return [
            CompletedOrder(
                work_order_id=row.WorkOrder.id,
                customer_name=row.customer_name,
                product_name=row.WorkOrder.product_name,
                quantity=row.WorkOrder.quantity,
                completed_at=row.WorkOrder.completed_at,
            )
            for row in rows
        ]
    finally:
        session.close()


def list_deviation_records() -> list[DeviationRecord]:
    session = get_session()
    try:
        daily_productions = daily_production_repository.list_all(session)
        result = []
        for row in daily_productions:
            step = work_order_step_repository.get_by_id(session, row.step_id)
            if row.actual_unit_seconds == step.unit_process_seconds:
                continue

            work_order = work_order_repository.get_by_id(session, row.work_order_id)
            customer = session.get(Customer, work_order.customer_id)
            step_rows = work_order_step_repository.list_by_work_order_with_machine(
                session, row.work_order_id
            )
            machine_name = next(
                (r.machine_name for r in step_rows if r.WorkOrderStep.id == step.id), ""
            )

            personnel_snapshot_total = (
                work_order_step_personnel_repository.sum_hourly_cost_snapshot_for_step(
                    session, step.id
                )
            )
            hourly_total = personnel_snapshot_total + step.machine_hourly_cost_snapshot

            actual_total_seconds = row.actual_unit_seconds * row.quantity
            planned_total_seconds = step.unit_process_seconds * row.quantity
            deviation_cost = (
                hourly_total
                * decimal.Decimal(actual_total_seconds - planned_total_seconds)
                / decimal.Decimal(3600)
            ).quantize(DEVIATION_QUANTIZE, rounding=decimal.ROUND_HALF_UP)

            result.append(
                DeviationRecord(
                    daily_production_id=row.id,
                    customer_name=customer.name,
                    product_name=work_order.product_name,
                    step_no=step.step_no,
                    machine_name=machine_name,
                    planned_unit_seconds=step.unit_process_seconds,
                    actual_unit_seconds=row.actual_unit_seconds,
                    quantity=row.quantity,
                    deviation_cost=deviation_cost,
                )
            )
        return result
    finally:
        session.close()


def list_machine_performance(
    start_date: datetime.date, end_date: datetime.date
) -> list[MachinePerformance]:
    session = get_session()
    try:
        rows = daily_production_repository.list_by_date_range(session, start_date, end_date)

        totals: dict[int, dict] = {}
        for row in rows:
            step = work_order_step_repository.get_by_id(session, row.step_id)
            work_seconds = row.actual_unit_seconds * row.quantity
            agg = totals.setdefault(
                step.machine_id, {"work_seconds": 0, "price": decimal.Decimal(0)}
            )
            agg["work_seconds"] += work_seconds
            agg["price"] += row.price_contribution

        result = []
        for machine_id, agg in totals.items():
            machine = machine_repository.get_by_id(session, machine_id)
            if agg["work_seconds"] > 0:
                hourly_return = (
                    agg["price"] / (decimal.Decimal(agg["work_seconds"]) / decimal.Decimal(3600))
                ).quantize(PERFORMANCE_QUANTIZE, rounding=decimal.ROUND_HALF_UP)
            else:
                hourly_return = decimal.Decimal("0.0000")
            result.append(
                MachinePerformance(
                    machine_id=machine_id,
                    machine_name=machine.name,
                    hourly_return=hourly_return,
                    total_price_contribution=agg["price"],
                )
            )

        result.sort(key=lambda item: item.hourly_return, reverse=True)
        return result[:MAX_PERFORMANCE_ROWS]
    finally:
        session.close()


def list_machine_detail(
    machine_id: int, start_date: datetime.date, end_date: datetime.date
) -> list[MachineDetailEntry]:
    session = get_session()
    try:
        rows = daily_production_repository.list_by_date_range(session, start_date, end_date)

        result = []
        for row in rows:
            step = work_order_step_repository.get_by_id(session, row.step_id)
            if step.machine_id != machine_id:
                continue
            work_order = work_order_repository.get_by_id(session, row.work_order_id)
            customer = session.get(Customer, work_order.customer_id)
            result.append(
                MachineDetailEntry(
                    id=row.id,
                    production_date=row.production_date,
                    customer_name=customer.name,
                    product_name=work_order.product_name,
                    step_no=step.step_no,
                    actual_unit_seconds=row.actual_unit_seconds,
                    quantity=row.quantity,
                    price_contribution=row.price_contribution,
                )
            )
        return result
    finally:
        session.close()


def list_customer_performance(
    start_date: datetime.date, end_date: datetime.date
) -> list[CustomerPerformance]:
    session = get_session()
    try:
        rows = daily_production_repository.list_by_date_range(session, start_date, end_date)

        totals: dict[int, dict] = {}
        for row in rows:
            work_order = work_order_repository.get_by_id(session, row.work_order_id)
            work_seconds = row.actual_unit_seconds * row.quantity
            agg = totals.setdefault(
                work_order.customer_id, {"work_seconds": 0, "price": decimal.Decimal(0)}
            )
            agg["work_seconds"] += work_seconds
            agg["price"] += row.price_contribution

        result = []
        for customer_id, agg in totals.items():
            customer = session.get(Customer, customer_id)
            if agg["work_seconds"] > 0:
                hourly_return = (
                    agg["price"] / (decimal.Decimal(agg["work_seconds"]) / decimal.Decimal(3600))
                ).quantize(PERFORMANCE_QUANTIZE, rounding=decimal.ROUND_HALF_UP)
            else:
                hourly_return = decimal.Decimal("0.0000")
            result.append(
                CustomerPerformance(
                    customer_id=customer_id,
                    customer_name=customer.name,
                    hourly_return=hourly_return,
                    total_price_contribution=agg["price"],
                )
            )

        result.sort(key=lambda item: item.hourly_return, reverse=True)
        return result[:MAX_PERFORMANCE_ROWS]
    finally:
        session.close()


def list_customer_detail(
    customer_id: int, start_date: datetime.date, end_date: datetime.date
) -> list[CustomerDetailEntry]:
    session = get_session()
    try:
        rows = daily_production_repository.list_by_date_range(session, start_date, end_date)

        result = []
        for row in rows:
            work_order = work_order_repository.get_by_id(session, row.work_order_id)
            if work_order.customer_id != customer_id:
                continue
            step = work_order_step_repository.get_by_id(session, row.step_id)
            step_rows = work_order_step_repository.list_by_work_order_with_machine(
                session, row.work_order_id
            )
            machine_name = next(
                (r.machine_name for r in step_rows if r.WorkOrderStep.id == step.id), ""
            )
            result.append(
                CustomerDetailEntry(
                    id=row.id,
                    production_date=row.production_date,
                    product_name=work_order.product_name,
                    step_no=step.step_no,
                    machine_name=machine_name,
                    actual_unit_seconds=row.actual_unit_seconds,
                    quantity=row.quantity,
                    price_contribution=row.price_contribution,
                )
            )
        return result
    finally:
        session.close()


def get_revenue_summary(start_date: datetime.date, end_date: datetime.date) -> RevenueSummary:
    session = get_session()
    try:
        rows = daily_production_repository.list_by_date_range(session, start_date, end_date)

        total_quantity = 0
        total_price_contribution = decimal.Decimal(0)
        total_work_seconds = 0
        machine_ids = set()

        for row in rows:
            step = work_order_step_repository.get_by_id(session, row.step_id)
            total_quantity += row.quantity
            total_price_contribution += row.price_contribution
            total_work_seconds += row.actual_unit_seconds * row.quantity
            machine_ids.add(step.machine_id)

        return RevenueSummary(
            total_quantity=total_quantity,
            total_price_contribution=total_price_contribution,
            distinct_machine_count=len(machine_ids),
            total_work_seconds=total_work_seconds,
        )
    finally:
        session.close()


def list_daily_contribution(
    start_date: datetime.date, end_date: datetime.date
) -> list[DailyContribution]:
    session = get_session()
    try:
        rows = daily_production_repository.list_by_date_range(session, start_date, end_date)

        totals: dict[datetime.date, decimal.Decimal] = {}
        for row in rows:
            totals[row.production_date] = (
                totals.get(row.production_date, decimal.Decimal(0)) + row.price_contribution
            )

        return [
            DailyContribution(production_date=date, total_price_contribution=totals[date])
            for date in sorted(totals)
        ]
    finally:
        session.close()
