"""Read-only Nifty universe and sector lookups."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Sector, Stock


async def list_stocks(session: AsyncSession, sector: str | None = None) -> list[dict]:
    statement = (
        select(Stock, Sector)
        .join(Sector, Stock.sector_id == Sector.id)
        .order_by(Stock.symbol)
    )
    if sector is not None:
        statement = statement.where(Sector.name == sector)
    rows = (await session.execute(statement)).all()
    return [
        {
            "id": stock.id,
            "symbol": stock.symbol,
            "company_name": stock.company_name,
            "sector": stock_sector.name,
            "industry": stock.industry,
            "listed_since": stock.listed_since,
        }
        for stock, stock_sector in rows
    ]


async def list_sectors(session: AsyncSession) -> list[dict]:
    sectors = (await session.scalars(select(Sector).order_by(Sector.name))).all()
    return [{"id": sector.id, "name": sector.name} for sector in sectors]
