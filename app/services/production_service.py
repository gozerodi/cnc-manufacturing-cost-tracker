import dataclasses
import datetime
import decimal

from app.core.database import get_session
from app.models import Customer, Personnel
from app.repositories import (
    daily_production_personnel_repository,
    daily_production_repository,
    work_order_repository,
    work_order_step_repository,
)

QUANTIZE = decimal.Decimal("0.0001")


@dataclasses.dataclass
class WorkOrderOption:
    id: int
    customer_name: str
    product_name: str
    quantity: int


@dataclasses.dataclass
class StepOption:
    id: int
    step_no: int
    machine_name: str
    unit_net_price_contribution: decimal.Decimal


@dataclasses.dataclass
class DailyProductionListItem:
    id: int
    production_date: datetime.date
    customer_name: str
    product_name: str
    step_no: int
    machine_name: str
    actual_unit_seconds: int
    quantity: int
    price_contribution: decimal.Decimal
    personnel_names: list[str]


def list_active_work_orders() -> list[WorkOrderOption]:
    session = get_session()
    try:
        rows = work_order_repository.list_active_with_customer(session)
        return [
            WorkOrderOption(
                id=row.WorkOrder.id,
                customer_name=row.customer_name,
                product_name=row.WorkOrder.product_name,
                quantity=row.WorkOrder.quantity,
            )
            for row in rows
        ]
    finally:
        session.close()


def list_steps_for_work_order(work_order_id: int) -> list[StepOption]:
    session = get_session()
    try:
        rows = work_order_step_repository.list_by_work_order_with_machine(session, work_order_id)
        return [
            StepOption(
                id=row.WorkOrderStep.id,
                step_no=row.WorkOrderStep.step_no,
                machine_name=row.machine_name,
                unit_net_price_contribution=row.WorkOrderStep.unit_net_price_contribution,
            )
            for row in rows
        ]
    finally:
        session.close()


def _reevaluate_completion(session, work_order_id: int) -> None:
    session.flush()
    work_order = work_order_repository.get_by_id(session, work_order_id)
    step_rows = work_order_step_repository.list_by_work_order_with_machine(session, work_order_id)
    if not step_rows:
        return

    last_step = max((row.WorkOrderStep for row in step_rows), key=lambda step: step.step_no)
    total_quantity = daily_production_repository.sum_quantity_for_step(
        session, work_order_id, last_step.id
    )
    should_be_completed = total_quantity >= work_order.quantity

    if should_be_completed and work_order.status != "completed":
        work_order.status = "completed"
        work_order.completed_at = datetime.datetime.now()
    elif not should_be_completed and work_order.status == "completed":
        work_order.status = "active"
        work_order.completed_at = None


def create_daily_production(
    production_date: datetime.date,
    work_order_id: int,
    step_id: int,
    actual_unit_seconds: int,
    quantity: int,
    personnel_ids: list[int],
) -> int:
    session = get_session()
    try:
        step = work_order_step_repository.get_by_id(session, step_id)
        price_contribution = (step.unit_net_price_contribution * quantity).quantize(
            QUANTIZE, rounding=decimal.ROUND_HALF_UP
        )

        row = daily_production_repository.create(
            session,
            production_date=production_date,
            work_order_id=work_order_id,
            step_id=step_id,
            actual_unit_seconds=actual_unit_seconds,
            quantity=quantity,
            price_contribution=price_contribution,
        )

        for personnel_id in personnel_ids:
            daily_production_personnel_repository.create(
                session, daily_production_id=row.id, personnel_id=personnel_id
            )

        _reevaluate_completion(session, work_order_id)

        session.commit()
        return row.id
    finally:
        session.close()


def delete_daily_production(daily_production_id: int) -> None:
    session = get_session()
    try:
        row = daily_production_repository.get_by_id(session, daily_production_id)
        if row is None:
            return
        work_order_id = row.work_order_id

        daily_production_personnel_repository.delete_for_daily_production(
            session, daily_production_id
        )
        daily_production_repository.delete(session, daily_production_id)

        _reevaluate_completion(session, work_order_id)

        session.commit()
    finally:
        session.close()


def list_daily_productions_for_date(production_date: datetime.date) -> list[DailyProductionListItem]:
    session = get_session()
    try:
        rows = daily_production_repository.list_by_date(session, production_date)

        result = []
        for row in rows:
            work_order = work_order_repository.get_by_id(session, row.work_order_id)
            customer = session.get(Customer, work_order.customer_id)
            step = work_order_step_repository.get_by_id(session, row.step_id)
            step_rows = work_order_step_repository.list_by_work_order_with_machine(
                session, row.work_order_id
            )
            machine_name = next(
                (r.machine_name for r in step_rows if r.WorkOrderStep.id == step.id), ""
            )

            personnel_links = daily_production_personnel_repository.list_for_daily_production(
                session, row.id
            )
            personnel_names = []
            for link in personnel_links:
                personnel = session.get(Personnel, link.personnel_id)
                if personnel is not None:
                    personnel_names.append(personnel.name)

            result.append(
                DailyProductionListItem(
                    id=row.id,
                    production_date=row.production_date,
                    customer_name=customer.name,
                    product_name=work_order.product_name,
                    step_no=step.step_no,
                    machine_name=machine_name,
                    actual_unit_seconds=row.actual_unit_seconds,
                    quantity=row.quantity,
                    price_contribution=row.price_contribution,
                    personnel_names=personnel_names,
                )
            )
        return result
    finally:
        session.close()
