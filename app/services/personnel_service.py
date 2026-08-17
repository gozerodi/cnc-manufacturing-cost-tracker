import dataclasses
import decimal

from app.core.database import get_session
from app.repositories import personnel_cost_repository, personnel_repository

HOURLY_COST_QUANTIZE = decimal.Decimal("0.0001")

TYPE_LABELS = {"production": "Production", "administrative": "Administrative"}


@dataclasses.dataclass
class PersonnelListItem:
    id: int
    name: str
    type: str
    monthly_salary: decimal.Decimal
    days_per_month: int
    hours_per_day: int
    hourly_cost: decimal.Decimal


def calculate_hourly_cost(
    monthly_salary: decimal.Decimal, days_per_month: int, hours_per_day: int
) -> decimal.Decimal:
    total_hours = decimal.Decimal(days_per_month) * decimal.Decimal(hours_per_day)
    return (monthly_salary / total_hours).quantize(
        HOURLY_COST_QUANTIZE, rounding=decimal.ROUND_HALF_UP
    )


def create_personnel(
    name: str,
    type_: str,
    monthly_salary: decimal.Decimal,
    days_per_month: int,
    hours_per_day: int,
) -> int:
    hourly_cost = calculate_hourly_cost(monthly_salary, days_per_month, hours_per_day)
    session = get_session()
    try:
        personnel = personnel_repository.create(session, name=name, type_=type_)
        personnel_cost_repository.create(
            session,
            personnel_id=personnel.id,
            monthly_salary=monthly_salary,
            days_per_month=days_per_month,
            hours_per_day=hours_per_day,
            hourly_cost=hourly_cost,
        )
        session.commit()
        return personnel.id
    finally:
        session.close()


def update_personnel(
    personnel_id: int,
    name: str,
    type_: str,
    monthly_salary: decimal.Decimal,
    days_per_month: int,
    hours_per_day: int,
) -> None:
    hourly_cost = calculate_hourly_cost(monthly_salary, days_per_month, hours_per_day)
    session = get_session()
    try:
        personnel_repository.update_basic_info(session, personnel_id, name=name, type_=type_)
        personnel_cost_repository.create(
            session,
            personnel_id=personnel_id,
            monthly_salary=monthly_salary,
            days_per_month=days_per_month,
            hours_per_day=hours_per_day,
            hourly_cost=hourly_cost,
        )
        session.commit()
    finally:
        session.close()


def soft_delete_personnel(personnel_id: int) -> None:
    session = get_session()
    try:
        personnel_repository.soft_delete(session, personnel_id)
        session.commit()
    finally:
        session.close()


def list_personnel() -> list[PersonnelListItem]:
    session = get_session()
    try:
        personnel_rows = personnel_repository.list_active(session)
        ids = [p.id for p in personnel_rows]
        latest_costs = personnel_cost_repository.get_latest_for_personnel_ids(session, ids)

        result = []
        for personnel in personnel_rows:
            cost = latest_costs.get(personnel.id)
            result.append(
                PersonnelListItem(
                    id=personnel.id,
                    name=personnel.name,
                    type=personnel.type,
                    monthly_salary=cost.monthly_salary if cost else decimal.Decimal(0),
                    days_per_month=cost.days_per_month if cost else 0,
                    hours_per_day=cost.hours_per_day if cost else 0,
                    hourly_cost=cost.hourly_cost if cost else decimal.Decimal(0),
                )
            )
        return result
    finally:
        session.close()


def list_production_personnel() -> list[PersonnelListItem]:
    return [item for item in list_personnel() if item.type == "production"]
