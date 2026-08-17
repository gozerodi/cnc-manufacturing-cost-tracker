import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SpecialExpense


def create(
    session: Session,
    name: str,
    amount: decimal.Decimal,
    year: int,
    month: int,
    machine_id: int | None,
) -> SpecialExpense:
    expense = SpecialExpense(name=name, amount=amount, year=year, month=month, machine_id=machine_id)
    session.add(expense)
    session.flush()
    return expense


def get_by_id(session: Session, expense_id: int) -> SpecialExpense | None:
    return session.get(SpecialExpense, expense_id)


def list_all(session: Session) -> list[SpecialExpense]:
    stmt = select(SpecialExpense).order_by(SpecialExpense.created_at.desc(), SpecialExpense.id.desc())
    return list(session.scalars(stmt))


def list_by_year_month(session: Session, year: int, month: int) -> list[SpecialExpense]:
    stmt = (
        select(SpecialExpense)
        .where(SpecialExpense.year == year, SpecialExpense.month == month)
        .order_by(SpecialExpense.created_at.desc(), SpecialExpense.id.desc())
    )
    return list(session.scalars(stmt))


def update(
    session: Session,
    expense_id: int,
    name: str,
    amount: decimal.Decimal,
    year: int,
    month: int,
    machine_id: int | None,
) -> SpecialExpense:
    expense = session.get(SpecialExpense, expense_id)
    expense.name = name
    expense.amount = amount
    expense.year = year
    expense.month = month
    expense.machine_id = machine_id
    return expense


def delete(session: Session, expense_id: int) -> None:
    expense = session.get(SpecialExpense, expense_id)
    if expense is not None:
        session.delete(expense)
