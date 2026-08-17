import datetime

from sqlalchemy import Date, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DailyReport(Base, TimestampMixin):
    __tablename__ = "daily_reports"

    report_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pdf_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
