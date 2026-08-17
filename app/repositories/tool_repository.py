import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tool


def create(
    session: Session, name: str, corner_count: int, price: decimal.Decimal, price_per_corner: decimal.Decimal
) -> Tool:
    tool = Tool(name=name, corner_count=corner_count, price=price, price_per_corner=price_per_corner)
    session.add(tool)
    session.flush()
    return tool


def get_by_id(session: Session, tool_id: int) -> Tool | None:
    return session.get(Tool, tool_id)


def list_all(session: Session) -> list[Tool]:
    stmt = select(Tool).order_by(Tool.created_at.desc(), Tool.id.desc())
    return list(session.scalars(stmt))


def update(
    session: Session,
    tool_id: int,
    name: str,
    corner_count: int,
    price: decimal.Decimal,
    price_per_corner: decimal.Decimal,
) -> Tool:
    tool = session.get(Tool, tool_id)
    tool.name = name
    tool.corner_count = corner_count
    tool.price = price
    tool.price_per_corner = price_per_corner
    return tool


def delete(session: Session, tool_id: int) -> None:
    tool = session.get(Tool, tool_id)
    if tool is not None:
        session.delete(tool)
