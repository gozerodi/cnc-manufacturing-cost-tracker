import decimal

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Tool(Base, TimestampMixin):
    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    corner_count: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    price_per_corner: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
