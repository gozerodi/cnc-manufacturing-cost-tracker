from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyProductionPersonnel


def create(session: Session, daily_production_id: int, personnel_id: int) -> DailyProductionPersonnel:
    row = DailyProductionPersonnel(daily_production_id=daily_production_id, personnel_id=personnel_id)
    session.add(row)
    session.flush()
    return row


def list_for_daily_production(session: Session, daily_production_id: int) -> list[DailyProductionPersonnel]:
    stmt = select(DailyProductionPersonnel).where(
        DailyProductionPersonnel.daily_production_id == daily_production_id
    )
    return list(session.scalars(stmt))


def delete_for_daily_production(session: Session, daily_production_id: int) -> None:
    session.query(DailyProductionPersonnel).filter_by(
        daily_production_id=daily_production_id
    ).delete()
