import datetime
import decimal
import uuid

import pytest

from app.core.database import get_session
from app.models import (
    Customer,
    DailyProduction,
    DailyProductionPersonnel,
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
    cost_service,
    customer_service,
    machine_service,
    personnel_service,
    planning_service,
    production_service,
)
from app.ui.pages.admin.detailed_cost_page import DetailedCostPage

D = decimal.Decimal


@pytest.fixture
def scenario():
    isolated_year = datetime.date.today().year - 5
    suffix = uuid.uuid4().hex[:8]

    production_id = personnel_service.create_personnel(
        f"DCP Production {suffix}", "production", D("6000"), 20, 8
    )
    machine_id = machine_service.create_machine(f"DCP Machine {suffix}", D("40"))
    customer_id = customer_service.create_customer(f"DCP Customer {suffix}")

    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(isolated_year, 9, 1),
        customer_id=customer_id,
        product_name=f"DCP Product {suffix}",
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
        "isolated_year": isolated_year,
        "production_id": production_id,
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
        session.query(PersonnelCost).filter_by(personnel_id=production_id).delete()
        session.query(Personnel).filter_by(id=production_id).delete()
        session.commit()
    finally:
        session.close()


def _find_row(table, text, column=0):
    for row in range(table.row_count()):
        item = table.model.item(row, column)
        if text in item.text():
            return row
    raise AssertionError(f"'{text}' not found")


def test_general_module_shows_special_expense_only_in_its_month(qapp, scenario):
    year = scenario["isolated_year"]

    special_id = cost_service.create_special_expense(
        "Test Maintenance", D("250"), year, 9, scenario["machine_id"]
    )
    try:
        page = DetailedCostPage()
        page.general_month_selector.set_year_month(year, 9)

        expected_label = cost_service.month_label(year, 9) + " Expenses"
        row = _find_row(page.general_table, expected_label)
        assert page.general_table.model.item(row, 1).text() == "$250.00"

        page.general_month_selector.set_year_month(year, 10)
        labels = [
            page.general_table.model.item(r, 0).text() for r in range(page.general_table.row_count())
        ]
        assert expected_label not in labels
    finally:
        session = get_session()
        try:
            session.query(SpecialExpense).filter_by(id=special_id).delete()
            session.commit()
        finally:
            session.close()


def test_machine_module_totals_and_all_option(qapp, scenario):
    year = scenario["isolated_year"]
    machine_id = scenario["machine_id"]

    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(year, 9, 15),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=5,
        personnel_ids=[],
    )
    special_id = cost_service.create_special_expense(
        "Test Part", D("80"), year, 9, machine_id
    )

    try:
        page = DetailedCostPage()
        page.machine_date_filter.month_selector.set_year_month(year, 9)

        index = page.machine_combo.findData(machine_id)
        assert index >= 0
        page.machine_combo.setCurrentIndex(index)
        page._refresh_machine()

        assert page.working_cost_card.value_label.text() == "$200.00"
        assert page.special_cost_card.value_label.text() == "$80.00"
        assert page.total_cost_card.value_label.text() == "$280.00"

        all_index = page.machine_combo.findData(None)
        page.machine_combo.setCurrentIndex(all_index)
        page._refresh_machine()

        assert page.working_cost_card.value_label.text() != "$0.00"
    finally:
        session = get_session()
        try:
            session.query(SpecialExpense).filter_by(id=special_id).delete()
            session.commit()
        finally:
            session.close()
