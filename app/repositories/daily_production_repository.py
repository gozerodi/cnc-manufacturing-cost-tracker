import datetime
import decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DailyProduction


def create(
    session: Session,
    production_date: datetime.date,
    work_order_id: int,
    step_id: int,
    actual_unit_seconds: int,
    quantity: int,
    price_contribution: decimal.Decimal,
) -> DailyProduction:
    row = DailyProduction(
        production_date=production_date,
        work_order_id=work_order_id,
        step_id=step_id,
        actual_unit_seconds=actual_unit_seconds,
        quantity=quantity,
        price_contribution=price_contribution,
    )
    session.add(row)
    session.flush()
    return row


def get_by_id(session: Session, daily_production_id: int) -> DailyProduction | None:
    return session.get(DailyProduction, daily_production_id)


def delete(session: Session, daily_production_id: int) -> None:
    row = session.get(DailyProduction, daily_production_id)
    if row is not None:
        session.delete(row)


def sum_quantity_for_step(session: Session, work_order_id: int, step_id: int) -> int:
    stmt = select(func.coalesce(func.sum(DailyProduction.quantity), 0)).where(
        DailyProduction.work_order_id == work_order_id,
        DailyProduction.step_id == step_id,
    )
    return session.execute(stmt).scalar_one()


def exists_for_work_order(session: Session, work_order_id: int) -> bool:
    stmt = select(DailyProduction.id).where(DailyProduction.work_order_id == work_order_id).limit(1)
    return session.execute(stmt).first() is not None


def list_by_date(session: Session, production_date: datetime.date) -> list[DailyProduction]:
    stmt = (
        select(DailyProduction)
        .where(DailyProduction.production_date == production_date)
        .order_by(DailyProduction.created_at.desc(), DailyProduction.id.desc())
    )
    return list(session.scalars(stmt))


def list_all(session: Session) -> list[DailyProduction]:
    stmt = select(DailyProduction).order_by(DailyProduction.created_at.desc(), DailyProduction.id.desc())
    return list(session.scalars(stmt))


def list_by_date_range(
    session: Session, start_date: datetime.date, end_date: datetime.date
) -> list[DailyProduction]:
    stmt = (
        select(DailyProduction)
        .where(
            DailyProduction.production_date >= start_date,
            DailyProduction.production_date <= end_date,
        )
        .order_by(DailyProduction.created_at.desc(), DailyProduction.id.desc())
    )
    return list(session.scalars(stmt))
