import datetime
import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, WorkOrder


def create(
    session: Session,
    order_date: datetime.date,
    customer_id: int,
    product_name: str,
    unit_raw_material_cost: decimal.Decimal,
    unit_production_cost: decimal.Decimal,
    profit_percent: decimal.Decimal,
    unit_sale_price: decimal.Decimal,
    quantity: int,
    extra_cost: decimal.Decimal,
    total_price: decimal.Decimal,
) -> WorkOrder:
    work_order = WorkOrder(
        order_date=order_date,
        customer_id=customer_id,
        product_name=product_name,
        unit_raw_material_cost=unit_raw_material_cost,
        unit_production_cost=unit_production_cost,
        profit_percent=profit_percent,
        unit_sale_price=unit_sale_price,
        quantity=quantity,
        extra_cost=extra_cost,
        total_price=total_price,
        status="active",
    )
    session.add(work_order)
    session.flush()
    return work_order


def get_by_id(session: Session, work_order_id: int) -> WorkOrder | None:
    return session.get(WorkOrder, work_order_id)


def delete(session: Session, work_order_id: int) -> None:
    work_order = session.get(WorkOrder, work_order_id)
    if work_order is not None:
        session.delete(work_order)


def list_all_with_customer(session: Session):
    stmt = (
        select(WorkOrder, Customer.name.label("customer_name"))
        .join(Customer, WorkOrder.customer_id == Customer.id)
        .order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc())
    )
    return session.execute(stmt).all()


def list_active_with_customer(session: Session):
    stmt = (
        select(WorkOrder, Customer.name.label("customer_name"))
        .join(Customer, WorkOrder.customer_id == Customer.id)
        .where(WorkOrder.status == "active")
        .order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc())
    )
    return session.execute(stmt).all()


def list_completed_with_customer(session: Session):
    stmt = (
        select(WorkOrder, Customer.name.label("customer_name"))
        .join(Customer, WorkOrder.customer_id == Customer.id)
        .where(WorkOrder.status == "completed")
        .order_by(WorkOrder.completed_at.desc(), WorkOrder.id.desc())
    )
    return session.execute(stmt).all()
