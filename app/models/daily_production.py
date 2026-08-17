import datetime
import decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DailyProduction(Base, TimestampMixin):
    __tablename__ = "daily_productions"

    production_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), nullable=False)
    step_id: Mapped[int] = mapped_column(ForeignKey("work_order_steps.id"), nullable=False)
    actual_unit_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_contribution: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
