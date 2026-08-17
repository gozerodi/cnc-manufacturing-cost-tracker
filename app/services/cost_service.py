import dataclasses
import datetime
import decimal

from app.core.database import get_session
from app.repositories import (
    daily_production_repository,
    fixed_expense_repository,
    machine_cost_repository,
    machine_repository,
    personnel_cost_repository,
    personnel_repository,
    special_expense_repository,
    work_order_step_repository,
)
from app.services import analytics_service

MACHINE_COST_QUANTIZE = decimal.Decimal("0.0001")

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


@dataclasses.dataclass
class FixedExpenseListItem:
    id: int
    name: str
    amount: decimal.Decimal
    period: str


@dataclasses.dataclass
class SpecialExpenseListItem:
    id: int
    name: str
    amount: decimal.Decimal
    year: int
    month: int
    machine_id: int | None
    machine_name: str | None


@dataclasses.dataclass
class CostCategory:
    label: str
    amount: decimal.Decimal


@dataclasses.dataclass
class GeneralCostBreakdown:
    categories: list[CostCategory]
    total: decimal.Decimal


@dataclasses.dataclass
class MachineCostDetail:
    working_cost: decimal.Decimal
    special_expenses_total: decimal.Decimal
    total: decimal.Decimal


def month_label(year: int, month: int) -> str:
    return f"{MONTH_NAMES[month - 1]} {year}"


def _month_date_range(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, analytics_service.days_in_month(year, month))
    return start_date, end_date


def create_fixed_expense(name: str, amount: decimal.Decimal, period: str) -> int:
    session = get_session()
    try:
        expense = fixed_expense_repository.create(session, name=name, amount=amount, period=period)
        session.commit()
        return expense.id
    finally:
        session.close()


def update_fixed_expense(expense_id: int, name: str, amount: decimal.Decimal, period: str) -> None:
    session = get_session()
    try:
        fixed_expense_repository.update(session, expense_id, name=name, amount=amount, period=period)
        session.commit()
    finally:
        session.close()


def soft_delete_fixed_expense(expense_id: int) -> None:
    session = get_session()
    try:
        fixed_expense_repository.soft_delete(session, expense_id)
        session.commit()
    finally:
        session.close()


def list_fixed_expenses() -> list[FixedExpenseListItem]:
    session = get_session()
    try:
        rows = fixed_expense_repository.list_active(session)
        return [
            FixedExpenseListItem(id=row.id, name=row.name, amount=row.amount, period=row.period)
            for row in rows
        ]
    finally:
        session.close()


def create_special_expense(
    name: str, amount: decimal.Decimal, year: int, month: int, machine_id: int | None
) -> int:
    session = get_session()
    try:
        expense = special_expense_repository.create(
            session, name=name, amount=amount, year=year, month=month, machine_id=machine_id
        )
        session.commit()
        return expense.id
    finally:
        session.close()


def update_special_expense(
    expense_id: int,
    name: str,
    amount: decimal.Decimal,
    year: int,
    month: int,
    machine_id: int | None,
) -> None:
    session = get_session()
    try:
        special_expense_repository.update(
            session,
            expense_id,
            name=name,
            amount=amount,
            year=year,
            month=month,
            machine_id=machine_id,
        )
        session.commit()
    finally:
        session.close()


def delete_special_expense(expense_id: int) -> None:
    session = get_session()
    try:
        special_expense_repository.delete(session, expense_id)
        session.commit()
    finally:
        session.close()


def _to_special_expense_list_items(session, rows) -> list[SpecialExpenseListItem]:
    result = []
    for row in rows:
        machine_name = None
        if row.machine_id is not None:
            machine = machine_repository.get_by_id(session, row.machine_id)
            machine_name = machine.name if machine is not None else None
        result.append(
            SpecialExpenseListItem(
                id=row.id,
                name=row.name,
                amount=row.amount,
                year=row.year,
                month=row.month,
                machine_id=row.machine_id,
                machine_name=machine_name,
            )
        )
    return result


def list_special_expenses() -> list[SpecialExpenseListItem]:
    session = get_session()
    try:
        rows = special_expense_repository.list_all(session)
        return _to_special_expense_list_items(session, rows)
    finally:
        session.close()


def list_special_expenses_for_month(year: int, month: int) -> list[SpecialExpenseListItem]:
    session = get_session()
    try:
        rows = special_expense_repository.list_by_year_month(session, year, month)
        return _to_special_expense_list_items(session, rows)
    finally:
        session.close()


def get_general_cost_breakdown(year: int, month: int) -> GeneralCostBreakdown:
    session = get_session()
    try:
        production_total = decimal.Decimal(0)
        administrative_total = decimal.Decimal(0)
        personnel_rows = personnel_repository.list_active(session)
        personnel_ids = [p.id for p in personnel_rows]
        latest_costs = personnel_cost_repository.get_latest_for_personnel_ids(session, personnel_ids)
        for personnel in personnel_rows:
            cost = latest_costs.get(personnel.id)
            if cost is None:
                continue
            if personnel.type == "production":
                production_total += cost.monthly_salary
            else:
                administrative_total += cost.monthly_salary

        days = analytics_service.days_in_month(year, month)
        fixed_total = decimal.Decimal(0)
        for expense in fixed_expense_repository.list_active(session):
            if expense.period == "monthly":
                fixed_total += expense.amount
            else:
                fixed_total += expense.amount * days

        special_rows = special_expense_repository.list_by_year_month(session, year, month)
        special_total = sum((row.amount for row in special_rows), decimal.Decimal(0))

        start_date, end_date = _month_date_range(year, month)
        daily_rows = daily_production_repository.list_by_date_range(session, start_date, end_date)
        machine_total = decimal.Decimal(0)
        for row in daily_rows:
            step = work_order_step_repository.get_by_id(session, row.step_id)
            machine_cost = machine_cost_repository.get_latest_for_machine(session, step.machine_id)
            hourly_cost = machine_cost.hourly_cost if machine_cost is not None else decimal.Decimal(0)
            work_seconds = row.actual_unit_seconds * row.quantity
            machine_total += (hourly_cost * decimal.Decimal(work_seconds) / decimal.Decimal(3600)).quantize(
                MACHINE_COST_QUANTIZE, rounding=decimal.ROUND_HALF_UP
            )

        categories = [
            CostCategory("Production Staff Salaries", production_total),
            CostCategory("Administrative Staff Salaries", administrative_total),
            CostCategory("Fixed Expenses", fixed_total),
            CostCategory("Machine Expenses", machine_total),
        ]
        if special_rows:
            categories.append(CostCategory(f"{month_label(year, month)} Expenses", special_total))

        categories.sort(key=lambda category: category.amount, reverse=True)
        total = sum((category.amount for category in categories), decimal.Decimal(0))
        return GeneralCostBreakdown(categories=categories, total=total)
    finally:
        session.close()


def get_machine_cost_detail(
    machine_id: int | None, start_date: datetime.date, end_date: datetime.date
) -> MachineCostDetail:
    session = get_session()
    try:
        daily_rows = daily_production_repository.list_by_date_range(session, start_date, end_date)
        working_cost = decimal.Decimal(0)
        for row in daily_rows:
            step = work_order_step_repository.get_by_id(session, row.step_id)
            if machine_id is not None and step.machine_id != machine_id:
                continue
            machine_cost = machine_cost_repository.get_latest_for_machine(session, step.machine_id)
            hourly_cost = machine_cost.hourly_cost if machine_cost is not None else decimal.Decimal(0)
            work_seconds = row.actual_unit_seconds * row.quantity
            working_cost += (hourly_cost * decimal.Decimal(work_seconds) / decimal.Decimal(3600)).quantize(
                MACHINE_COST_QUANTIZE, rounding=decimal.ROUND_HALF_UP
            )

        months: set[tuple[int, int]] = set()
        cursor = datetime.date(start_date.year, start_date.month, 1)
        while cursor <= end_date:
            months.add((cursor.year, cursor.month))
            if cursor.month == 12:
                cursor = datetime.date(cursor.year + 1, 1, 1)
            else:
                cursor = datetime.date(cursor.year, cursor.month + 1, 1)

        special_total = decimal.Decimal(0)
        for year, month in months:
            for expense in special_expense_repository.list_by_year_month(session, year, month):
                if machine_id is not None and expense.machine_id != machine_id:
                    continue
                if machine_id is None and expense.machine_id is None:
                    continue
                special_total += expense.amount

        return MachineCostDetail(
            working_cost=working_cost,
            special_expenses_total=special_total,
            total=working_cost + special_total,
        )
    finally:
        session.close()
