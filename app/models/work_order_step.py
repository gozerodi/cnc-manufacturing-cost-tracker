import decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WorkOrderStep(Base, TimestampMixin):
    __tablename__ = "work_order_steps"

    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), nullable=False)
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), nullable=False)
    unit_process_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    setup_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    machine_hourly_cost_snapshot: Mapped[decimal.Decimal] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    step_unit_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_net_price_contribution: Mapped[decimal.Decimal] = mapped_column(
        Numeric(14, 4), nullable=False
    )

    work_order: Mapped["WorkOrder"] = relationship(back_populates="steps")
