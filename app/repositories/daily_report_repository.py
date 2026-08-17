import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DailyReport


def create(
    session: Session,
    report_date: datetime.date,
    display_name: str,
    pdf_data: bytes,
) -> DailyReport:
    report = DailyReport(report_date=report_date, display_name=display_name, pdf_data=pdf_data)
    session.add(report)
    session.flush()
    return report


def get_by_id(session: Session, report_id: int) -> DailyReport | None:
    return session.get(DailyReport, report_id)


def count_for_date(session: Session, report_date: datetime.date) -> int:
    stmt = select(func.count(DailyReport.id)).where(DailyReport.report_date == report_date)
    return session.execute(stmt).scalar_one()


def list_all(session: Session) -> list[DailyReport]:
    stmt = select(DailyReport).order_by(DailyReport.created_at.desc(), DailyReport.id.desc())
    return list(session.scalars(stmt))
