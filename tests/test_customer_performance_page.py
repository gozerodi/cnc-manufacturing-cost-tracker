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
    WorkOrder,
    WorkOrderStep,
    WorkOrderStepPersonnel,
    WorkOrderStepTool,
)
from app.services import customer_service, machine_service, planning_service, production_service
from app.ui.pages.admin.customer_performance_page import CustomerPerformancePage

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    machine_id = machine_service.create_machine(f"PageCPerf M {suffix}", D("100"))
    customer_id = customer_service.create_customer(f"Harbor Machining {suffix}")

    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=customer_id,
        product_name=f"PageCPerf Product {suffix}",
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
        "machine_id": machine_id,
        "customer_id": customer_id,
        "customer_name": f"Harbor Machining {suffix}",
        "work_order_id": work_order_id,
        "product_name": f"PageCPerf Product {suffix}",
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
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.query(Customer).filter_by(id=customer_id).delete()
        session.commit()
    finally:
        session.close()


def _find_row(table, text, column=0):
    for row in range(table.row_count()):
        item = table.model.item(row, column)
        if text in item.text():
            return row
    raise AssertionError(f"'{text}' not found")


def test_performance_table_matches_manual_calc(qapp, scenario):
    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=1,
        personnel_ids=[],
    )

    page = CustomerPerformancePage()
    page.date_filter.date_input.setDate(page.date_filter.date_input.date().fromString("24.07.2026", "dd.MM.yyyy"))
    page.refresh()

    row = _find_row(page.performance_table, scenario["customer_name"])
    assert page.performance_table.model.item(row, 1).text() == "$100.00"
    assert page.performance_table.model.item(row, 2).text() == "$100.00"


def test_customer_search_is_case_insensitive_and_updates_detail(qapp, scenario):
    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=2,
        personnel_ids=[],
    )

    page = CustomerPerformancePage()
    page.date_filter.date_input.setDate(page.date_filter.date_input.date().fromString("24.07.2026", "dd.MM.yyyy"))
    page.refresh()

    page._customer_completer.setCompletionPrefix("ha")
    lowercase_matches = [
        page._customer_completer.completionModel().index(i, 0).data()
        for i in range(page._customer_completer.completionModel().rowCount())
    ]
    assert any(scenario["customer_name"] == match for match in lowercase_matches)

    page.customer_input.setText(scenario["customer_name"])

    row = _find_row(page.detail_table, scenario["product_name"], column=1)
    assert page.detail_table.model.item(row, 4).text() == "2"


def test_month_filter_shows_only_selected_month(qapp, scenario):
    isolated_year = datetime.date.today().year - 5

    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(isolated_year, 5, 10),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=2,
        personnel_ids=[],
    )
    production_service.create_daily_production(
        production_date=datetime.date(isolated_year, 6, 10),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=9,
        personnel_ids=[],
    )

    page = CustomerPerformancePage()
    page.date_filter.month_selector.set_year_month(isolated_year, 5)

    assert page.date_filter.source == "month"
    row = _find_row(page.performance_table, scenario["customer_name"])
    assert page.performance_table.model.item(row, 2).text() == "$200.00"

    page.date_filter.month_selector.set_year_month(isolated_year, 6)

    row = _find_row(page.performance_table, scenario["customer_name"])
    assert page.performance_table.model.item(row, 2).text() == "$900.00"
