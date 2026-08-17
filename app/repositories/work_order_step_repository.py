import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Machine, WorkOrderStep


def create(
    session: Session,
    work_order_id: int,
    step_no: int,
    machine_id: int,
    unit_process_seconds: int,
    machine_hourly_cost_snapshot: decimal.Decimal,
    step_unit_cost: decimal.Decimal,
    unit_net_price_contribution: decimal.Decimal,
    setup_seconds: int = 0,
) -> WorkOrderStep:
    step = WorkOrderStep(
        work_order_id=work_order_id,
        step_no=step_no,
        machine_id=machine_id,
        unit_process_seconds=unit_process_seconds,
        setup_seconds=setup_seconds,
        machine_hourly_cost_snapshot=machine_hourly_cost_snapshot,
        step_unit_cost=step_unit_cost,
        unit_net_price_contribution=unit_net_price_contribution,
    )
    session.add(step)
    session.flush()
    return step


def get_by_id(session: Session, step_id: int) -> WorkOrderStep | None:
    return session.get(WorkOrderStep, step_id)


def list_by_work_order_with_machine(session: Session, work_order_id: int):
    stmt = (
        select(WorkOrderStep, Machine.name.label("machine_name"))
        .join(Machine, WorkOrderStep.machine_id == Machine.id)
        .where(WorkOrderStep.work_order_id == work_order_id)
        .order_by(WorkOrderStep.step_no)
    )
    return session.execute(stmt).all()


def list_ids_by_work_order(session: Session, work_order_id: int) -> list[int]:
    stmt = select(WorkOrderStep.id).where(WorkOrderStep.work_order_id == work_order_id)
    return list(session.scalars(stmt))


def delete_for_work_order(session: Session, work_order_id: int) -> None:
    session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).delete()
