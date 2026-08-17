import dataclasses
import datetime
import decimal

from app.core.database import get_session
from app.repositories import daily_report_repository
from app.services import production_service


@dataclasses.dataclass
class ReportLine:
    product_name: str
    step_no: int
    quantity: int
    price_contribution: decimal.Decimal
    work_seconds: int


@dataclasses.dataclass
class CustomerSection:
    customer_name: str
    lines: list[ReportLine]


@dataclasses.dataclass
class ReportTotals:
    customer_names: list[str]
    product_names: list[str]
    quantity: int
    price_contribution: decimal.Decimal
    work_seconds: int


@dataclasses.dataclass
class ReportData:
    report_date: datetime.date
    sections: list[CustomerSection]
    totals: ReportTotals


@dataclasses.dataclass
class ReportListItem:
    id: int
    display_name: str
    report_date: datetime.date
    created_at: datetime.datetime


def has_production_for_date(report_date: datetime.date) -> bool:
    return bool(production_service.list_daily_productions_for_date(report_date))


def build_report_data(report_date: datetime.date) -> ReportData:
    items = production_service.list_daily_productions_for_date(report_date)

    grouped: dict[tuple[str, str, int], dict] = {}
    for item in items:
        key = (item.customer_name, item.product_name, item.step_no)
        agg = grouped.setdefault(
            key, {"quantity": 0, "price_contribution": decimal.Decimal(0), "work_seconds": 0}
        )
        agg["quantity"] += item.quantity
        agg["price_contribution"] += item.price_contribution
        agg["work_seconds"] += item.actual_unit_seconds * item.quantity

    by_customer: dict[str, list[ReportLine]] = {}
    for (customer_name, product_name, step_no), agg in grouped.items():
        by_customer.setdefault(customer_name, []).append(
            ReportLine(
                product_name=product_name,
                step_no=step_no,
                quantity=agg["quantity"],
                price_contribution=agg["price_contribution"],
                work_seconds=agg["work_seconds"],
            )
        )

    sections = [
        CustomerSection(
            customer_name=customer_name,
            lines=sorted(by_customer[customer_name], key=lambda line: (line.product_name, line.step_no)),
        )
        for customer_name in sorted(by_customer)
    ]

    totals = ReportTotals(
        customer_names=sorted(by_customer),
        product_names=sorted({line.product_name for lines in by_customer.values() for line in lines}),
        quantity=sum(item.quantity for item in items),
        price_contribution=sum((item.price_contribution for item in items), decimal.Decimal(0)),
        work_seconds=sum(item.actual_unit_seconds * item.quantity for item in items),
    )

    return ReportData(report_date=report_date, sections=sections, totals=totals)


def save_report(report_date: datetime.date, pdf_data: bytes) -> int:
    session = get_session()
    try:
        existing_count = daily_report_repository.count_for_date(session, report_date)
        date_text = report_date.strftime("%d.%m.%Y")
        display_name = (
            f"{date_text}_Report" if existing_count == 0 else f"{date_text}_Report({existing_count + 1})"
        )

        report = daily_report_repository.create(
            session, report_date=report_date, display_name=display_name, pdf_data=pdf_data
        )
        session.commit()
        return report.id
    finally:
        session.close()


def list_recent_reports(limit: int | None = None) -> list[ReportListItem]:
    """Returns all reports with the most recently created first (if no limit is given)."""
    session = get_session()
    try:
        rows = daily_report_repository.list_all(session)
        if limit is not None:
            rows = rows[:limit]
        return [
            ReportListItem(
                id=row.id,
                display_name=row.display_name,
                report_date=row.report_date,
                created_at=row.created_at,
            )
            for row in rows
        ]
    finally:
        session.close()


def get_report_pdf(report_id: int) -> bytes | None:
    session = get_session()
    try:
        report = daily_report_repository.get_by_id(session, report_id)
        return report.pdf_data if report is not None else None
    finally:
        session.close()
