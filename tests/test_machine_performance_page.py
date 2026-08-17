import datetime
import decimal
import uuid

import pytest
import qdarktheme

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
from app.services import (
    customer_service,
    machine_service,
    planning_service,
    production_service,
)
from app.ui.pages.admin.machine_performance_page import MachinePerformancePage

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    machine_id = machine_service.create_machine(f"PagePerf M {suffix}", D("100"))
    customer_id = customer_service.create_customer(f"PagePerf Customer {suffix}")

    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=customer_id,
        product_name=f"PagePerf Product {suffix}",
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
        "work_order_id": work_order_id,
        "machine_name": f"PagePerf M {suffix}",
        "product_name": f"PagePerf Product {suffix}",
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
    for row in range(table.row_count() if hasattr(table, "row_count") else table.rowCount()):
        item = table.model.item(row, column) if hasattr(table, "model") else table.item(row, column)
        if text in item.text():
            return row
    raise AssertionError(f"'{text}' not found")


def test_performance_table_and_pie_match_manual_calc(qapp, scenario):
    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=1,
        personnel_ids=[],
    )

    page = MachinePerformancePage()
    page.date_filter.date_input.setDate(page.date_filter.date_input.date().fromString("24.07.2026", "dd.MM.yyyy"))
    page.date_filter.period_selector.set_current_period("Day")
    page.refresh()

    row = _find_row(page.performance_table, scenario["machine_name"])
    assert page.performance_table.model.item(row, 1).text() == "$100.00"
    assert page.performance_table.model.item(row, 2).text() == "$100.00"
    assert len(page.figure.axes) == 1
    assert len(page.figure.axes[0].patches) == len(page._performance)


def test_theme_change_does_not_break_pie_chart(qapp, scenario):
    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=1,
        personnel_ids=[],
    )

    for theme in ("dark", "light"):
        qdarktheme.setup_theme(theme)
        page = MachinePerformancePage()
        page.date_filter.date_input.setDate(page.date_filter.date_input.date().fromString("24.07.2026", "dd.MM.yyyy"))
        page.refresh()
        assert len(page.figure.axes) == 1
    qdarktheme.setup_theme("auto")


def test_machine_detail_updates_when_machine_selected(qapp, scenario):
    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(2026, 7, 24),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=3,
        personnel_ids=[],
    )

    page = MachinePerformancePage()
    page.date_filter.date_input.setDate(page.date_filter.date_input.date().fromString("24.07.2026", "dd.MM.yyyy"))
    page.refresh()

    index = page.machine_combo.findData(scenario["machine_id"])
    assert index >= 0
    page.machine_combo.setCurrentIndex(index)

    row = _find_row(page.detail_table, scenario["product_name"], column=2)
    assert page.detail_table.model.item(row, 5).text() == "3"


def test_month_filter_shows_only_selected_month(qapp, scenario):
    isolated_year = datetime.date.today().year - 5

    step = production_service.list_steps_for_work_order(scenario["work_order_id"])[0]
    production_service.create_daily_production(
        production_date=datetime.date(isolated_year, 3, 10),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=2,
        personnel_ids=[],
    )
    production_service.create_daily_production(
        production_date=datetime.date(isolated_year, 4, 10),
        work_order_id=scenario["work_order_id"],
        step_id=step.id,
        actual_unit_seconds=3600,
        quantity=9,
        personnel_ids=[],
    )

    page = MachinePerformancePage()
    page.date_filter.month_selector.set_year_month(isolated_year, 3)

    assert page.date_filter.source == "month"
    row = _find_row(page.performance_table, scenario["machine_name"])
    assert page.performance_table.model.item(row, 1).text() == "$100.00"

    page.date_filter.month_selector.set_year_month(isolated_year, 4)

    row = _find_row(page.performance_table, scenario["machine_name"])
    assert page.performance_table.model.item(row, 1).text() == "$100.00"
    assert page.performance_table.model.item(row, 2).text() == "$900.00"
