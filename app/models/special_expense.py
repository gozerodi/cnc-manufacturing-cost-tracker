import decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SpecialExpense(Base, TimestampMixin):
    __tablename__ = "special_expenses"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    machine_id: Mapped[int | None] = mapped_column(ForeignKey("machines.id"), nullable=True)
