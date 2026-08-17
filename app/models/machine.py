from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Machine(Base, TimestampMixin):
    __tablename__ = "machines"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    costs: Mapped[list["MachineCost"]] = relationship(back_populates="machine")
