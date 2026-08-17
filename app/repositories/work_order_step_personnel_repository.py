import decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import WorkOrderStepPersonnel


def create(
    session: Session, step_id: int, personnel_id: int, hourly_cost_snapshot: decimal.Decimal
) -> WorkOrderStepPersonnel:
    row = WorkOrderStepPersonnel(
        step_id=step_id,
        personnel_id=personnel_id,
        hourly_cost_snapshot=hourly_cost_snapshot,
    )
    session.add(row)
    session.flush()
    return row


def delete_for_steps(session: Session, step_ids: list[int]) -> None:
    if not step_ids:
        return
    session.query(WorkOrderStepPersonnel).filter(
        WorkOrderStepPersonnel.step_id.in_(step_ids)
    ).delete(synchronize_session=False)


def list_for_step(session: Session, step_id: int) -> list[WorkOrderStepPersonnel]:
    stmt = select(WorkOrderStepPersonnel).where(WorkOrderStepPersonnel.step_id == step_id)
    return list(session.scalars(stmt))


def sum_hourly_cost_snapshot_for_step(session: Session, step_id: int) -> decimal.Decimal:
    stmt = select(
        func.coalesce(func.sum(WorkOrderStepPersonnel.hourly_cost_snapshot), decimal.Decimal("0"))
    ).where(WorkOrderStepPersonnel.step_id == step_id)
    return session.execute(stmt).scalar_one()
