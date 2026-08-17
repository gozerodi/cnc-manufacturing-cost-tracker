import datetime
import decimal
import uuid

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from app.core.database import get_session
from app.models import (
    Customer,
    DailyProduction,
    DailyProductionPersonnel,
    Machine,
    MachineCost,
    Personnel,
    PersonnelCost,
    WorkOrder,
    WorkOrderStep,
    WorkOrderStepPersonnel,
    WorkOrderStepTool,
)
from app.services import customer_service, machine_service, personnel_service, planning_service
from app.ui.pages.staff.daily_production_page import DailyProductionPage

D = decimal.Decimal


@pytest.fixture
def scenario():
    suffix = uuid.uuid4().hex[:8]
    personnel_id = personnel_service.create_personnel(
        f"Page Prod Staff {suffix}", "production", D("30000"), 20, 9
    )
    machine_id = machine_service.create_machine(f"Page Prod Machine {suffix}", D("300"))
    customer_id = customer_service.create_customer(f"Page Prod Customer {suffix}")

    steps = [
        planning_service.DraftStep(
            machine_id=machine_id, unit_process_seconds=60, personnel_ids=[personnel_id], tools=[]
        )
    ]
    work_order_id = planning_service.create_work_order(
        order_date=datetime.date(2026, 7, 24),
        customer_id=customer_id,
        product_name=f"Page Prod Product {suffix}",
        quantity=5,
        raw_material_cost=D("0"),
        profit_percent=D("0"),
        extra_cost=D("0"),
        steps=steps,
    )

    yield {
        "personnel_id": personnel_id,
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
        session.query(PersonnelCost).filter_by(personnel_id=personnel_id).delete()
        session.query(Personnel).filter_by(id=personnel_id).delete()
        session.query(MachineCost).filter_by(machine_id=machine_id).delete()
        session.query(Machine).filter_by(id=machine_id).delete()
        session.query(Customer).filter_by(id=customer_id).delete()
        session.commit()
    finally:
        session.close()


def _select_work_order(page: DailyProductionPage, work_order_id: int) -> None:
    index = page.work_order_combo.findData(work_order_id)
    assert index >= 0
    page.work_order_combo.setCurrentIndex(index)


def test_completed_work_order_not_selectable_after_full_quantity(qapp, scenario):
    page = DailyProductionPage()
    work_order_id = scenario["work_order_id"]

    _select_work_order(page, work_order_id)
    assert page.step_combo.count() == 1

    page.seconds_input.set_seconds(60)
    page.quantity_input.setValue(5)
    page._on_save()

    page.refresh()
    assert page.work_order_combo.findData(work_order_id) == -1


def test_save_writes_price_contribution_and_appears_in_list(qapp, scenario):
    page = DailyProductionPage()
    work_order_id = scenario["work_order_id"]

    _select_work_order(page, work_order_id)
    step_id = page.step_combo.currentData()

    for i in range(page.personnel_list.count()):
        item = page.personnel_list.item(i)
        if item.data(Qt.ItemDataRole.UserRole) == scenario["personnel_id"]:
            item.setCheckState(Qt.CheckState.Checked)

    page.seconds_input.set_seconds(60)
    page.quantity_input.setValue(2)
    page._on_save()

    session = get_session()
    try:
        row = (
            session.query(DailyProduction)
            .filter_by(work_order_id=work_order_id, step_id=step_id)
            .one()
        )
        step = session.get(WorkOrderStep, step_id)
        expected = (step.unit_net_price_contribution * 2).quantize(D("0.0001"))
        assert row.price_contribution == expected
    finally:
        session.close()

    assert page.entries_table.row_count() >= 1


def test_delete_entry_reverts_completion(qapp, monkeypatch, scenario):
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )

    page = DailyProductionPage()
    work_order_id = scenario["work_order_id"]

    _select_work_order(page, work_order_id)
    page.seconds_input.set_seconds(60)
    page.quantity_input.setValue(5)
    page._on_save()

    session = get_session()
    try:
        work_order = session.get(WorkOrder, work_order_id)
        assert work_order.status == "completed"
    finally:
        session.close()

    assert page.entries_table.row_count() >= 1
    row_index = next(
        i for i, e in enumerate(page._entries) if e.customer_name == scenario_customer_name(scenario)
    )
    page._on_delete_requested(row_index)

    session = get_session()
    try:
        work_order = session.get(WorkOrder, work_order_id)
        assert work_order.status == "active"
    finally:
        session.close()


def scenario_customer_name(scenario):
    session = get_session()
    try:
        customer = session.get(Customer, scenario["customer_id"])
        return customer.name
    finally:
        session.close()


def test_only_production_personnel_listed(qapp, scenario):
    admin_id = personnel_service.create_personnel(
        f"Administrative {uuid.uuid4().hex[:8]}", "administrative", D("20000"), 22, 8
    )
    try:
        page = DailyProductionPage()
        ids = [
            page.personnel_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(page.personnel_list.count())
        ]
        assert admin_id not in ids
        assert scenario["personnel_id"] in ids
    finally:
        session = get_session()
        try:
            session.query(PersonnelCost).filter_by(personnel_id=admin_id).delete()
            session.query(Personnel).filter_by(id=admin_id).delete()
            session.commit()
        finally:
            session.close()
