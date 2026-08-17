import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MachineCost


def create(session: Session, machine_id: int, hourly_cost: decimal.Decimal) -> MachineCost:
    cost = MachineCost(machine_id=machine_id, hourly_cost=hourly_cost)
    session.add(cost)
    session.flush()
    return cost


def get_latest_for_machine(session: Session, machine_id: int) -> MachineCost | None:
    stmt = (
        select(MachineCost)
        .where(MachineCost.machine_id == machine_id)
        .order_by(MachineCost.valid_from.desc(), MachineCost.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def get_latest_for_machine_ids(session: Session, machine_ids: list[int]) -> dict[int, MachineCost]:
    if not machine_ids:
        return {}
    stmt = (
        select(MachineCost)
        .where(MachineCost.machine_id.in_(machine_ids))
        .order_by(MachineCost.machine_id, MachineCost.valid_from.desc(), MachineCost.id.desc())
    )
    latest: dict[int, MachineCost] = {}
    for cost in session.scalars(stmt):
        latest.setdefault(cost.machine_id, cost)
    return latest
