import datetime
import decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MachineCost(Base, TimestampMixin):
    __tablename__ = "machine_costs"

    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), nullable=False)
    hourly_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    valid_from: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    machine: Mapped["Machine"] = relationship(back_populates="costs")
