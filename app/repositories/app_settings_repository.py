from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSetting


def get_by_key(session: Session, key: str) -> AppSetting | None:
    stmt = select(AppSetting).where(AppSetting.key == key)
    return session.scalars(stmt).first()
