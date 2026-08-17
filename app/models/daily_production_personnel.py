from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DailyProductionPersonnel(Base, TimestampMixin):
    __tablename__ = "daily_production_personnel"

    daily_production_id: Mapped[int] = mapped_column(
        ForeignKey("daily_productions.id"), nullable=False
    )
    personnel_id: Mapped[int] = mapped_column(ForeignKey("personnel.id"), nullable=False)
