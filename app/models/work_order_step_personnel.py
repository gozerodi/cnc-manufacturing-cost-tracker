import decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WorkOrderStepPersonnel(Base, TimestampMixin):
    __tablename__ = "work_order_step_personnel"

    step_id: Mapped[int] = mapped_column(ForeignKey("work_order_steps.id"), nullable=False)
    personnel_id: Mapped[int] = mapped_column(ForeignKey("personnel.id"), nullable=False)
    hourly_cost_snapshot: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
