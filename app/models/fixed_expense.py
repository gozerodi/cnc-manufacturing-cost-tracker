import decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FixedExpense(Base, TimestampMixin):
    __tablename__ = "fixed_expenses"
    __table_args__ = (
        CheckConstraint("period IN ('daily', 'monthly')", name="ck_fixed_expenses_period"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
