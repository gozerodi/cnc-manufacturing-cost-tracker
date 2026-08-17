import decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WorkOrderStepTool(Base, TimestampMixin):
    __tablename__ = "work_order_step_tools"

    step_id: Mapped[int] = mapped_column(ForeignKey("work_order_steps.id"), nullable=False)
    tool_id: Mapped[int] = mapped_column(ForeignKey("tools.id"), nullable=False)
    corners_used: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_corner_snapshot: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
