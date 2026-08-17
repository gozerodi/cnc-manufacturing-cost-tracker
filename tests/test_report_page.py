import datetime
import decimal
import tempfile
import uuid

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QFileDialog, QMessageBox

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
from app.ui.pages.admin import report_page as report_page_module
from app.ui.pages.admin.report_page import ReportPage

D = decimal.Decimal


@pytest.fixture
def scenario():
    isolated_year = datetime.date.today().year - 5
    suffix = uuid.uuid4().hex[:8]
    report_date = datetime.date(isolated_year, 9, 12)
    empty_date = datetime.date(isolated_year, 9, 13)

    machine_id = machine_service.create_machine(f"Page Report M {suffix}", D("100"))
    customer_name = f"Page Report Customer {suffix}"
    customer_id = customer_service.create_customer(customer_name)

    work_order_id = planning_service.create_work_order(
        order_date=report_date,
        customer_id=customer_id,
        product_name=f"Page Report Product {suffix}",
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
    step_id = production_service.list_steps_for_work_order(work_order_id)[0].id
    production_service.create_daily_production(
        production_date=report_date,
        work_order_id=work_order_id,
        step_id=step_id,
        actual_unit_seconds=3600,
        quantity=5,
        personnel_ids=[],
    )

    yield {
        "report_date": report_date,
        "empty_date": empty_date,
        "customer_id": customer_id,
        "work_order_id": work_order_id,
        "machine_id": machine_id,
    }

    session = get_session()
    try:
        step_ids = [
            s.id for s in session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).all()
        ]
        daily_production_ids = [
            dp.id for dp in session.query(DailyProduction).filter_by(work_order_id=work_order_id).all()
        ]
        session.query(DailyProductionPersonnel).filter(
            DailyProductionPersonnel.daily_production_id.in_(daily_production_ids)
        ).delete(synchronize_session=False)
        session.query(DailyProduction).filter_by(work_order_id=work_order_id).delete()
        session.query(WorkOrderStepPersonnel).filter(
            WorkOrderStepPersonnel.step_id.in_(step_ids)
        ).delete(synchronize_session=False)
        session.query(WorkOrderStepTool).filter(WorkOrderStepTool.step_id.in_(step_ids)).delete(
            synchronize_session=False
        )
        session.query(WorkOrderStep).filter_by(work_order_id=work_order_id).delete()
        session.query(WorkOrder).filter_by(id=work_order_id).delete()
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.query(Customer).filter_by(id=customer_id).delete()
        session.query(DailyReport).filter_by(report_date=report_date).delete()
        session.commit()
    finally:
        session.close()


def _set_date(page: ReportPage, date_value: datetime.date) -> None:
    page.date_input.setDate(QDate(date_value.year, date_value.month, date_value.day))


def test_generate_warns_when_no_production_for_date(qapp, monkeypatch, scenario):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    page = ReportPage()
    _set_date(page, scenario["empty_date"])
    initial_count = page.reports_list.count()

    page._on_generate_clicked()

    assert len(warnings) == 1
    expected_date_text = scenario["empty_date"].strftime("%d.%m.%Y")
    assert expected_date_text in warnings[0][2]
    assert page.reports_list.count() == initial_count


def test_generate_creates_report_and_refreshes_list(qapp, monkeypatch, scenario):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    page = ReportPage()
    _set_date(page, scenario["report_date"])

    page._on_generate_clicked()

    assert warnings == []
    assert page.reports_list.count() >= 1

    expected_name = f"{scenario['report_date'].strftime('%d.%m.%Y')}_Report"
    top_report = page._reports[0]
    assert top_report.display_name == expected_name

    pdf_data = report_service.get_report_pdf(top_report.id)
    assert pdf_data is not None
    assert pdf_data[:4] == b"%PDF"


def test_download_writes_pdf_bytes_to_chosen_path(qapp, monkeypatch, scenario):
    report_id = report_service.save_report(scenario["report_date"], b"%PDF-fake-bytes")

    page = ReportPage()

    with tempfile.TemporaryDirectory() as tmp_dir:
        target_path = f"{tmp_dir}/downloaded_report.pdf"
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (target_path, ""))
        )

        page._on_download(report_id, "26.07.2026_Report")

        with open(target_path, "rb") as pdf_file:
            assert pdf_file.read() == b"%PDF-fake-bytes"


def test_remove_temp_file_safely_deletes_existing_file(tmp_path):
    target = tmp_path / "temp.pdf"
    target.write_bytes(b"data")

    report_page_module._remove_temp_file_safely(str(target))

    assert not target.exists()


def test_remove_temp_file_safely_gives_up_silently_on_permission_error(monkeypatch):
    # On Windows a newly written file can stay locked briefly; in that case the
    # function should give up without raising (without silently crashing on Windows).
    monkeypatch.setattr(report_page_module.time, "sleep", lambda *_a: None)

    def _always_fail(_path):
        raise PermissionError("file in use")

    monkeypatch.setattr(report_page_module.os, "remove", _always_fail)

    report_page_module._remove_temp_file_safely("/var/tmp/missing-file.pdf")
