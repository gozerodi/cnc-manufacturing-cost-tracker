import datetime
import decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PersonnelCost(Base, TimestampMixin):
    __tablename__ = "personnel_costs"

    personnel_id: Mapped[int] = mapped_column(ForeignKey("personnel.id"), nullable=False)
    monthly_salary: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    days_per_month: Mapped[int] = mapped_column(Integer, nullable=False)
    hours_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    hourly_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    valid_from: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    personnel: Mapped["Personnel"] = relationship(back_populates="costs")
