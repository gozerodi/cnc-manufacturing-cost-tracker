import dataclasses
import decimal

from app.core.database import get_session
from app.repositories import tool_repository

PRICE_PER_CORNER_QUANTIZE = decimal.Decimal("0.0001")


@dataclasses.dataclass
class ToolListItem:
    id: int
    name: str
    corner_count: int
    price: decimal.Decimal
    price_per_corner: decimal.Decimal


def calculate_price_per_corner(price: decimal.Decimal, corner_count: int) -> decimal.Decimal:
    return (price / decimal.Decimal(corner_count)).quantize(
        PRICE_PER_CORNER_QUANTIZE, rounding=decimal.ROUND_HALF_UP
    )


def create_tool(name: str, corner_count: int, price: decimal.Decimal) -> int:
    price_per_corner = calculate_price_per_corner(price, corner_count)
    session = get_session()
    try:
        tool = tool_repository.create(session, name, corner_count, price, price_per_corner)
        session.commit()
        return tool.id
    finally:
        session.close()


def update_tool(tool_id: int, name: str, corner_count: int, price: decimal.Decimal) -> None:
    price_per_corner = calculate_price_per_corner(price, corner_count)
    session = get_session()
    try:
        tool_repository.update(session, tool_id, name, corner_count, price, price_per_corner)
        session.commit()
    finally:
        session.close()


def delete_tool(tool_id: int) -> None:
    session = get_session()
    try:
        tool_repository.delete(session, tool_id)
        session.commit()
    finally:
        session.close()


def list_tools() -> list[ToolListItem]:
    session = get_session()
    try:
        tools = tool_repository.list_all(session)
        return [
            ToolListItem(
                id=tool.id,
                name=tool.name,
                corner_count=tool.corner_count,
                price=tool.price,
                price_per_corner=tool.price_per_corner,
            )
            for tool in tools
        ]
    finally:
        session.close()
