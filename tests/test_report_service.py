import datetime
import decimal
import uuid

import pytest

from app.core.database import get_session
from app.models import (
    Customer,
    DailyProduction,
    DailyProductionPersonnel,
    DailyReport,
    Machine,
    MachineCost,
    WorkOrder,
    WorkOrderStep,
    WorkOrderStepPersonnel,
    WorkOrderStepTool,
)
from app.services import customer_service, machine_service, planning_service, production_service, report_service

D = decimal.Decimal


@pytest.fixture
def scenario():
    isolated_year = datetime.date.today().year - 5
    suffix = uuid.uuid4().hex[:8]
    report_date = datetime.date(isolated_year, 8, 15)
    other_date = datetime.date(isolated_year, 8, 16)

    machine1_id = machine_service.create_machine(f"Report M1 {suffix}", D("100"))
    machine2_id = machine_service.create_machine(f"Report M2 {suffix}", D("200"))

    customer_a_name = f"Report Customer A {suffix}"
    customer_b_name = f"Report Customer B {suffix}"
    customer_a_id = customer_service.create_customer(customer_a_name)
    customer_b_id = customer_service.create_customer(customer_b_name)

    product_z_name = f"Report Product Z {suffix}"
    product_a_name = f"Report Product A {suffix}"

    work_order_a_id = planning_service.create_work_order(
        order_date=report_date,
        customer_id=customer_a_id,
        product_name=product_z_name,
        quantity=1,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=[
            planning_service.DraftStep(
                machine_id=machine1_id, unit_process_seconds=3600, personnel_ids=[], tools=[]
            ),
            planning_service.DraftStep(
                machine_id=machine2_id, unit_process_seconds=3600, personnel_ids=[], tools=[]
            ),
        ],
    )
    work_order_b_id = planning_service.create_work_order(
        order_date=report_date,
        customer_id=customer_b_id,
        product_name=product_a_name,
        quantity=1,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=[
            planning_service.DraftStep(
                machine_id=machine1_id, unit_process_seconds=3600, personnel_ids=[], tools=[]
            )
        ],
    )

    yield {
        "report_date": report_date,
        "other_date": other_date,
        "empty_date": datetime.date(isolated_year, 8, 17),
        "machine1_id": machine1_id,
        "machine2_id": machine2_id,
        "customer_a_name": customer_a_name,
        "customer_b_name": customer_b_name,
        "product_z_name": product_z_name,
        "product_a_name": product_a_name,
        "work_order_a_id": work_order_a_id,
        "work_order_b_id": work_order_b_id,
    }

    session = get_session()
    try:
        for work_order_id in (work_order_a_id, work_order_b_id):
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
        session.query(MachineCost).filter(
            MachineCost.machine_id.in_([machine1_id, machine2_id])
        ).delete(synchronize_session=False)
        session.query(Machine).filter(Machine.id.in_([machine1_id, machine2_id])).delete(
            synchronize_session=False
        )
        session.query(Customer).filter(Customer.id.in_([customer_a_id, customer_b_id])).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


@pytest.fixture
def cleanup_reports():
    created_ids: list[int] = []
    yield created_ids
    session = get_session()
    try:
        session.query(DailyReport).filter(DailyReport.id.in_(created_ids)).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


def _create_entry(work_order_id, step_id, production_date, actual_unit_seconds, quantity):
    return production_service.create_daily_production(
        production_date=production_date,
        work_order_id=work_order_id,
        step_id=step_id,
        actual_unit_seconds=actual_unit_seconds,
        quantity=quantity,
        personnel_ids=[],
    )


def test_has_production_for_date(scenario):
    step_a1 = production_service.list_steps_for_work_order(scenario["work_order_a_id"])[0]
    _create_entry(scenario["work_order_a_id"], step_a1.id, scenario["report_date"], 3600, 1)

    assert report_service.has_production_for_date(scenario["report_date"]) is True
    assert report_service.has_production_for_date(scenario["empty_date"]) is False


def test_build_report_data_groups_by_customer_product_step(scenario):
    steps_a = production_service.list_steps_for_work_order(scenario["work_order_a_id"])
    step_a1, step_a2 = steps_a[0], steps_a[1]
    step_b1 = production_service.list_steps_for_work_order(scenario["work_order_b_id"])[0]

    report_date = scenario["report_date"]

    # Two records entered at different times of the same day for the same (customer, product, step) should be summed into one line.
    _create_entry(scenario["work_order_a_id"], step_a1.id, report_date, 3600, 10)
    _create_entry(scenario["work_order_a_id"], step_a1.id, report_date, 1800, 5)
    _create_entry(scenario["work_order_a_id"], step_a2.id, report_date, 3600, 8)
    _create_entry(scenario["work_order_b_id"], step_b1.id, report_date, 1800, 4)

    # A record from a different date should not leak into the report.
    _create_entry(scenario["work_order_a_id"], step_a1.id, scenario["other_date"], 3600, 99)

    data = report_service.build_report_data(report_date)

    assert data.report_date == report_date
    assert [s.customer_name for s in data.sections] == sorted(
        [scenario["customer_a_name"], scenario["customer_b_name"]]
    )

    section_a = next(s for s in data.sections if s.customer_name == scenario["customer_a_name"])
    assert len(section_a.lines) == 2
    line_step1, line_step2 = section_a.lines
    assert line_step1.product_name == scenario["product_z_name"]
    assert line_step1.step_no == 1
    assert line_step1.quantity == 15
    assert line_step1.price_contribution == D("2250.0000")
    assert line_step1.work_seconds == 3600 * 10 + 1800 * 5

    assert line_step2.step_no == 2
    assert line_step2.quantity == 8
    assert line_step2.price_contribution == D("1200.0000")
    assert line_step2.work_seconds == 3600 * 8

    section_b = next(s for s in data.sections if s.customer_name == scenario["customer_b_name"])
    assert len(section_b.lines) == 1
    assert section_b.lines[0].product_name == scenario["product_a_name"]
    assert section_b.lines[0].quantity == 4
    assert section_b.lines[0].price_contribution == D("400.0000")
    assert section_b.lines[0].work_seconds == 1800 * 4

    totals = data.totals
    assert totals.customer_names == sorted([scenario["customer_a_name"], scenario["customer_b_name"]])
    assert totals.product_names == sorted([scenario["product_z_name"], scenario["product_a_name"]])
    assert totals.quantity == 15 + 8 + 4
    assert totals.price_contribution == D("2250.0000") + D("1200.0000") + D("400.0000")
    assert totals.work_seconds == (3600 * 10 + 1800 * 5) + (3600 * 8) + (1800 * 4)


def test_build_report_data_empty_date_returns_no_sections(scenario):
    data = report_service.build_report_data(scenario["empty_date"])
    assert data.sections == []
    assert data.totals.quantity == 0
    assert data.totals.customer_names == []


def test_save_report_naming_increments_for_same_date(scenario, cleanup_reports):
    report_date = scenario["report_date"]

    first_id = report_service.save_report(report_date, b"pdf-bytes-1")
    cleanup_reports.append(first_id)
    second_id = report_service.save_report(report_date, b"pdf-bytes-2")
    cleanup_reports.append(second_id)

    date_text = report_date.strftime("%d.%m.%Y")
    recent = report_service.list_recent_reports(limit=5)
    by_id = {item.id: item for item in recent}

    assert by_id[first_id].display_name == f"{date_text}_Report"
    assert by_id[second_id].display_name == f"{date_text}_Report(2)"

    # The most recently created report is on top.
    assert recent[0].id == second_id
    assert recent[1].id == first_id

    assert report_service.get_report_pdf(first_id) == b"pdf-bytes-1"
    assert report_service.get_report_pdf(second_id) == b"pdf-bytes-2"


def test_get_report_pdf_returns_none_for_unknown_id():
    assert report_service.get_report_pdf(-1) is None
