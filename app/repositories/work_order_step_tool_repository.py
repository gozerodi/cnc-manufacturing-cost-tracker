import decimal

from sqlalchemy.orm import Session

from app.models import WorkOrderStepTool


def create(
    session: Session,
    step_id: int,
    tool_id: int,
    corners_used: int,
    price_per_corner_snapshot: decimal.Decimal,
) -> WorkOrderStepTool:
    row = WorkOrderStepTool(
        step_id=step_id,
        tool_id=tool_id,
        corners_used=corners_used,
        price_per_corner_snapshot=price_per_corner_snapshot,
    )
    session.add(row)
    session.flush()
    return row


def delete_for_steps(session: Session, step_ids: list[int]) -> None:
    if not step_ids:
        return
    session.query(WorkOrderStepTool).filter(WorkOrderStepTool.step_id.in_(step_ids)).delete(
        synchronize_session=False
    )
