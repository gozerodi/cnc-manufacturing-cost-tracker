import datetime
import decimal
import uuid

import pytest

from app.core.database import get_session
from app.models import (
    Customer,
    DailyProduction,
    DailyProductionPersonnel,
    FixedExpense,
    Machine,
    MachineCost,
    Personnel,
    PersonnelCost,
    SpecialExpense,
    WorkOrder,
    WorkOrderStep,
    WorkOrderStepPersonnel,
    WorkOrderStepTool,
)
from app.services import (
    analytics_service,
    cost_service,
    customer_service,
    machine_service,
    personnel_service,
    planning_service,
    production_service,
)

D = decimal.Decimal


def _cleanup_fixed_expense(expense_id):
    session = get_session()
    try:
        session.query(FixedExpense).filter_by(id=expense_id).delete()
        session.commit()
    finally:
        session.close()


def _cleanup_special_expense(expense_id):
    session = get_session()
    try:
        session.query(SpecialExpense).filter_by(id=expense_id).delete()
        session.commit()
    finally:
        session.close()


def test_create_update_delete_fixed_expense():
    suffix = uuid.uuid4().hex[:8]
    expense_id = cost_service.create_fixed_expense(f"Kira {suffix}", D("5000"), "monthly")
    try:
        items = cost_service.list_fixed_expenses()
        created = next(i for i in items if i.id == expense_id)
        assert created.name == f"Kira {suffix}"
        assert created.period == "monthly"
        assert created.amount == D("5000.0000")

        cost_service.update_fixed_expense(expense_id, f"Rent Updated {suffix}", D("5500"), "daily")
        items = cost_service.list_fixed_expenses()
        updated = next(i for i in items if i.id == expense_id)
        assert updated.name == f"Rent Updated {suffix}"
        assert updated.period == "daily"
        assert updated.amount == D("5500.0000")

        cost_service.soft_delete_fixed_expense(expense_id)
        items = cost_service.list_fixed_expenses()
        assert all(i.id != expense_id for i in items)
    finally:
        _cleanup_fixed_expense(expense_id)


def test_create_update_delete_special_expense():
    suffix = uuid.uuid4().hex[:8]
    expense_id = cost_service.create_special_expense(
        f"Maintenance {suffix}", D("300"), 2099, 3, None
    )
    try:
        items = cost_service.list_special_expenses()
        created = next(i for i in items if i.id == expense_id)
        assert created.name == f"Maintenance {suffix}"
        assert created.year == 2099
        assert created.month == 3
        assert created.machine_id is None

        cost_service.update_special_expense(
            expense_id, f"Maintenance Updated {suffix}", D("400"), 2099, 4, None
        )
        items = cost_service.list_special_expenses()
        updated = next(i for i in items if i.id == expense_id)
        assert updated.month == 4
        assert updated.amount == D("400.0000")

        cost_service.delete_special_expense(expense_id)
        items = cost_service.list_special_expenses()
        assert all(i.id != expense_id for i in items)
        expense_id = None
    finally:
        if expense_id is not None:
            _cleanup_special_expense(expense_id)


def test_month_label_format():
    assert cost_service.month_label(2026, 7) == "July 2026"
    assert cost_service.month_label(2027, 1) == "January 2027"


@pytest.fixture
def general_scenario():
    suffix = uuid.uuid4().hex[:8]
    production_id = personnel_service.create_personnel(
        f"Cost Production {suffix}", "production", D("10000"), 20, 8
    )
    admin_id = personnel_service.create_personnel(
        f"Cost Administrative {suffix}", "administrative", D("8000"), 20, 8
    )
    monthly_fixed_id = cost_service.create_fixed_expense(f"Cost Monthly {suffix}", D("2000"), "monthly")
    daily_fixed_id = cost_service.create_fixed_expense(f"Cost Daily {suffix}", D("10"), "daily")

    machine_id = machine_service.create_machine(f"Cost Machine {suffix}", D("50"))
    customer_id = customer_service.create_customer(f"Cost Customer {suffix}")

    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2099, 3, 1),
        customer_id=customer_id,
        product_name=f"Cost Product {suffix}",
        quantity=1,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=[
            planning_service.DraftStep(
                machine_id=machine_id, unit_process_seconds=3600, personnel_ids=[], tools=[]
            )
        ],
    )

    yield {
        "production_id": production_id,
        "admin_id": admin_id,
        "monthly_fixed_id": monthly_fixed_id,
        "daily_fixed_id": daily_fixed_id,
        "machine_id": machine_id,
        "customer_id": customer_id,
        "work_order_id": work_order_id,
    }

    session = get_session()
    try:
        step_ids = [
            s.id for s in session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).all()
        ]
        daily_production_ids = [
            dp.id
            for dp in session.query(DailyProduction).filter_by(work_order_id=work_order_id).all()
        ]
        session.query(DailyProductionPersonnel).filter(
            DailyProductionPersonnel.daily_production_id.in_(daily_production_ids)
        ).delete(synchronize_session=False)
        session.query(DailyProduction).filter_by(work_order_id=work_order_id).delete()
        session.query(WorkOrderStepPersonnel).filter(
            WorkOrderStepPersonnel.step_id.in_(step_ids)
        ).delete(synchronize_session=False)
        session.query(WorkOrderStepTool).filter(
            WorkOrderStepTool.step_id.in_(step_ids)
        ).delete(synchronize_session=False)
        session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).delete()
        session.query(WorkOrder).filter_by(id=work_order_id).delete()
        session.query(SpecialExpense).filter_by(machine_id=machine_id).delete()
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.query(Customer).filter_by(id=customer_id).delete()
        session.query(FixedExpense).filter(
            FixedExpense.id.in_([monthly_fixed_id, daily_fixed_id])
        ).delete(synchronize_session=False)
        session.query(PersonnelCost).filter(
            PersonnelCost.personnel_id.in_([production_id, admin_id])
        ).delete(synchronize_session=False)
        session.query(Personnel).filter(Personnel.id.in_([production_id, admin_id])).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


def test_general_cost_breakdown_matches_manual_calculation():
    isolated_year, month = 2099, 3
    other_month = 4
    suffix = uuid.uuid4().hex[:8]

    before = cost_service.get_general_cost_breakdown(isolated_year, month)
    before_by_label = {c.label: c.amount for c in before.categories}

    production_id = personnel_service.create_personnel(
        f"Cost Production {suffix}", "production", D("10000"), 20, 8
    )
    admin_id = personnel_service.create_personnel(
        f"Cost Administrative {suffix}", "administrative", D("8000"), 20, 8
    )
    monthly_fixed_id = cost_service.create_fixed_expense(f"Cost Monthly {suffix}", D("2000"), "monthly")
    daily_fixed_id = cost_service.create_fixed_expense(f"Cost Daily {suffix}", D("10"), "daily")
    machine_id = machine_service.create_machine(f"Cost Machine {suffix}", D("50"))
    customer_id = customer_service.create_customer(f"Cost Customer {suffix}")

    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(isolated_year, month, 1),
        customer_id=customer_id,
        product_name=f"Cost Product {suffix}",
        quantity=1,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=[
            planning_service.DraftStep(
                machine_id=machine_id, unit_process_seconds=3600, personnel_ids=[], tools=[]
            )
        ],
    )
    step = production_service.list_steps_for_work_order(work_order_id)[0]
    production_service.create_daily_production(
        production_date=datetime.date(isolated_year, month, 10),
        work_order_id=work_order_id,
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=2,
        personnel_ids=[],
    )

    special_id = cost_service.create_special_expense(
        "Test Maintenance", D("300"), isolated_year, month, machine_id
    )
    try:
        after = cost_service.get_general_cost_breakdown(isolated_year, month)
        after_by_label = {c.label: c.amount for c in after.categories}

        days = analytics_service.days_in_month(isolated_year, month)

        assert after_by_label["Production Staff Salaries"] - before_by_label.get(
            "Production Staff Salaries", D(0)
        ) == D("10000.0000")
        assert after_by_label["Administrative Staff Salaries"] - before_by_label.get(
            "Administrative Staff Salaries", D(0)
        ) == D("8000.0000")
        assert after_by_label["Fixed Expenses"] - before_by_label.get(
            "Fixed Expenses", D(0)
        ) == D("2000.0000") + D("10.0000") * days
        assert after_by_label["Machine Expenses"] - before_by_label.get(
            "Machine Expenses", D(0)
        ) == D("100.0000")

        special_label = f"{cost_service.month_label(isolated_year, month)} Expenses"
        assert special_label in after_by_label
        assert after_by_label[special_label] == D("300.0000")

        other_breakdown = cost_service.get_general_cost_breakdown(isolated_year, other_month)
        other_labels = [c.label for c in other_breakdown.categories]
        assert special_label not in other_labels
    finally:
        _cleanup_special_expense(special_id)

        session = get_session()
        try:
            step_ids = [
                s.id
                for s in session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).all()
            ]
            daily_production_ids = [
                dp.id
                for dp in session.query(DailyProduction)
                .filter_by(work_order_id=work_order_id)
                .all()
            ]
            session.query(DailyProductionPersonnel).filter(
                DailyProductionPersonnel.daily_production_id.in_(daily_production_ids)
            ).delete(synchronize_session=False)
            session.query(DailyProduction).filter_by(work_order_id=work_order_id).delete()
            session.query(WorkOrderStepPersonnel).filter(
                WorkOrderStepPersonnel.step_id.in_(step_ids)
            ).delete(synchronize_session=False)
            session.query(WorkOrderStepTool).filter(
                WorkOrderStepTool.step_id.in_(step_ids)
            ).delete(synchronize_session=False)
            session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).delete()
            session.query(WorkOrder).filter_by(id=work_order_id).delete()
            session.query(MachineCost).filter_by(machine_id=machine_id).delete()
            session.query(Machine).filter_by(id=machine_id).delete()
            session.query(Customer).filter_by(id=customer_id).delete()
            session.query(FixedExpense).filter(
                FixedExpense.id.in_([monthly_fixed_id, daily_fixed_id])
            ).delete(synchronize_session=False)
            session.query(PersonnelCost).filter(
                PersonnelCost.personnel_id.in_([production_id, admin_id])
            ).delete(synchronize_session=False)
            session.query(Personnel).filter(Personnel.id.in_([production_id, admin_id])).delete(
                synchronize_session=False
            )
            session.commit()
        finally:
            session.close()


def test_machine_cost_detail_sums_working_cost_and_special_expenses(general_scenario):
    machine_id = general_scenario["machine_id"]
    start_date = datetime.date(2099, 5, 1)
    end_date = datetime.date(2099, 5, 31)

    step = production_service.list_steps_for_work_order(general_scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(2099, 5, 15),
        work_order_id=general_scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=4,
        personnel_ids=[],
    )
    special_id = cost_service.create_special_expense("Test Spare Part", D("150"), 2099, 5, machine_id)

    try:
        detail = cost_service.get_machine_cost_detail(machine_id, start_date, end_date)
        assert detail.working_cost == D("200.0000")
        assert detail.special_expenses_total == D("150.0000")
        assert detail.total == D("350.0000")

        all_detail = cost_service.get_machine_cost_detail(None, start_date, end_date)
        assert all_detail.working_cost >= detail.working_cost
        assert all_detail.special_expenses_total >= detail.special_expenses_total
    finally:
        _cleanup_special_expense(special_id)
