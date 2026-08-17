import datetime
import decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WorkOrder(Base, TimestampMixin):
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed')", name="ck_work_orders_status"),
    )

    order_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_raw_material_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_production_cost: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    profit_percent: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_sale_price: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_cost: Mapped[decimal.Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=0, server_default="0"
    )
    total_price: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )

    steps: Mapped[list["WorkOrderStep"]] = relationship(back_populates="work_order")
