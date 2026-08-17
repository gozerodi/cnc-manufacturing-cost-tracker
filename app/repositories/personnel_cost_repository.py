import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PersonnelCost


def create(
    session: Session,
    personnel_id: int,
    monthly_salary: decimal.Decimal,
    days_per_month: int,
    hours_per_day: int,
    hourly_cost: decimal.Decimal,
) -> PersonnelCost:
    cost = PersonnelCost(
        personnel_id=personnel_id,
        monthly_salary=monthly_salary,
        days_per_month=days_per_month,
        hours_per_day=hours_per_day,
        hourly_cost=hourly_cost,
    )
    session.add(cost)
    session.flush()
    return cost


def get_latest_for_personnel(session: Session, personnel_id: int) -> PersonnelCost | None:
    stmt = (
        select(PersonnelCost)
        .where(PersonnelCost.personnel_id == personnel_id)
        .order_by(PersonnelCost.valid_from.desc(), PersonnelCost.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def get_latest_for_personnel_ids(
    session: Session, personnel_ids: list[int]
) -> dict[int, PersonnelCost]:
    if not personnel_ids:
        return {}
    stmt = (
        select(PersonnelCost)
        .where(PersonnelCost.personnel_id.in_(personnel_ids))
        .order_by(
            PersonnelCost.personnel_id, PersonnelCost.valid_from.desc(), PersonnelCost.id.desc()
        )
    )
    latest: dict[int, PersonnelCost] = {}
    for cost in session.scalars(stmt):
        latest.setdefault(cost.personnel_id, cost)
    return latest
