from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Personnel(Base, TimestampMixin):
    __tablename__ = "personnel"
    __table_args__ = (
        CheckConstraint("type IN ('production', 'administrative')", name="ck_personnel_type"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    costs: Mapped[list["PersonnelCost"]] = relationship(back_populates="personnel")
