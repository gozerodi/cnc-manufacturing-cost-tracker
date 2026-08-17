import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FixedExpense


def create(session: Session, name: str, amount: decimal.Decimal, period: str) -> FixedExpense:
    expense = FixedExpense(name=name, amount=amount, period=period, is_active=True)
    session.add(expense)
    session.flush()
    return expense


def get_by_id(session: Session, expense_id: int) -> FixedExpense | None:
    return session.get(FixedExpense, expense_id)


def list_active(session: Session) -> list[FixedExpense]:
    stmt = (
        select(FixedExpense)
        .where(FixedExpense.is_active.is_(True))
        .order_by(FixedExpense.created_at.desc(), FixedExpense.id.desc())
    )
    return list(session.scalars(stmt))


def update(
    session: Session, expense_id: int, name: str, amount: decimal.Decimal, period: str
) -> FixedExpense:
    expense = session.get(FixedExpense, expense_id)
    expense.name = name
    expense.amount = amount
    expense.period = period
    return expense


def soft_delete(session: Session, expense_id: int) -> None:
    expense = session.get(FixedExpense, expense_id)
    if expense is not None:
        expense.is_active = False
