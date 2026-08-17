import dataclasses
import decimal

from app.core.database import get_session
from app.repositories import machine_cost_repository, machine_repository


@dataclasses.dataclass
class MachineListItem:
    id: int
    name: str
    hourly_cost: decimal.Decimal


def create_machine(name: str, hourly_cost: decimal.Decimal) -> int:
    session = get_session()
    try:
        machine = machine_repository.create(session, name=name)
        machine_cost_repository.create(session, machine_id=machine.id, hourly_cost=hourly_cost)
        session.commit()
        return machine.id
    finally:
        session.close()


def update_machine(machine_id: int, name: str, hourly_cost: decimal.Decimal) -> None:
    session = get_session()
    try:
        machine_repository.update_name(session, machine_id, name=name)
        machine_cost_repository.create(session, machine_id=machine_id, hourly_cost=hourly_cost)
        session.commit()
    finally:
        session.close()


def soft_delete_machine(machine_id: int) -> None:
    session = get_session()
    try:
        machine_repository.soft_delete(session, machine_id)
        session.commit()
    finally:
        session.close()


def list_machines() -> list[MachineListItem]:
    session = get_session()
    try:
        machines = machine_repository.list_active(session)
        ids = [m.id for m in machines]
        latest_costs = machine_cost_repository.get_latest_for_machine_ids(session, ids)

        result = []
        for machine in machines:
            cost = latest_costs.get(machine.id)
            result.append(
                MachineListItem(
                    id=machine.id,
                    name=machine.name,
                    hourly_cost=cost.hourly_cost if cost else decimal.Decimal(0),
                )
            )
        return result
    finally:
        session.close()
