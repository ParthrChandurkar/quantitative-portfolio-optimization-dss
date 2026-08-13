"""Idempotent CSV loader for the Nifty-50 historical dataset.

The loader implements FR-2 and NFR-7. Raw header variants are isolated in
``COLUMN_MAP``; all downstream logic uses canonical field names.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Sector,
    Stock,
    StockFundamental,
    StockPrice,
    StockTechnicalIndicator,
)
from app.db.session import AsyncSessionFactory

# Change or add a raw CSV header here; transformation and persistence code remains stable.
COLUMN_MAP: dict[str, tuple[str, ...]] = {
    "symbol": ("Symbol", "Ticker", "Stock Symbol"),
    "company_name": ("Company Name", "Company", "Name"),
    "sector": ("Sector", "Sector Name"),
    "industry": ("Industry", "Industry Name"),
    "listed_since": ("Listed Since", "Listing Date"),
    "trade_date": ("Date", "Trade Date", "Trading Date"),
    "open": ("Open", "Open Price"),
    "high": ("High", "High Price"),
    "low": ("Low", "Low Price"),
    "close": ("Close", "Close Price"),
    "adj_close": ("Adj Close", "Adjusted Close", "Adj_Close"),
    "volume": ("Volume", "Traded Volume"),
    "pe_ratio": ("PE Ratio", "P/E Ratio", "PE"),
    "pb_ratio": ("PB Ratio", "P/B Ratio", "PB"),
    "market_cap": ("Market Cap", "Market Capitalization"),
    "dividend_yield": ("Dividend Yield", "Div Yield"),
    "eps": ("EPS", "Earnings Per Share"),
    "beta": ("Beta",),
    "sma_50": ("SMA_50", "SMA 50", "50 Day SMA"),
    "sma_200": ("SMA_200", "SMA 200", "200 Day SMA"),
    "rsi_14": ("RSI_14", "RSI 14", "RSI"),
    "macd": ("MACD",),
    "volatility_annualized": (
        "Annualized Volatility",
        "Volatility Annualized",
        "Annualised Volatility",
    ),
}

REQUIRED_COLUMNS = {
    "symbol",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
}
NULL_MARKERS = {"", "na", "n/a", "nan", "none", "null", "-"}


@dataclass(frozen=True, slots=True)
class NormalizedRow:
    symbol: str
    company_name: str
    sector: str
    industry: str | None
    listed_since: date | None
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Decimal
    volume: int
    pe_ratio: Decimal | None
    pb_ratio: Decimal | None
    market_cap: Decimal | None
    dividend_yield: Decimal | None
    eps: Decimal | None
    beta: Decimal | None
    sma_50: Decimal | None
    sma_200: Decimal | None
    rsi_14: Decimal | None
    macd: Decimal | None
    volatility_annualized: Decimal | None


@dataclass(frozen=True, slots=True)
class RejectedRow:
    source: str
    row_number: int
    reason: str


@dataclass(frozen=True, slots=True)
class LoadResult:
    accepted_rows: int
    rejected_rows: tuple[RejectedRow, ...]
    symbols: tuple[str, ...]

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_rows)


def _normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _resolve_headers(fieldnames: Sequence[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise ValueError("CSV has no header row")
    available = {_normalise_header(header): header for header in fieldnames if header}
    resolved: dict[str, str] = {}
    for canonical, candidates in COLUMN_MAP.items():
        for candidate in candidates:
            raw = available.get(_normalise_header(candidate))
            if raw is not None:
                resolved[canonical] = raw
                break
    missing = sorted(REQUIRED_COLUMNS - resolved.keys())
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
    return resolved


def _value(row: Mapping[str, str | None], headers: Mapping[str, str], field: str) -> str:
    raw_header = headers.get(field)
    return (row.get(raw_header) or "").strip() if raw_header else ""


def _decimal(raw: str, field: str, *, required: bool = False) -> Decimal | None:
    cleaned = raw.strip().replace(",", "").replace("₹", "")
    if cleaned.casefold() in NULL_MARKERS:
        if required:
            raise ValueError(f"{field} is required")
        return None
    cleaned = cleaned.removesuffix("%")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not numeric: {raw!r}") from exc


def _date(raw: str, field: str, *, required: bool = False) -> date | None:
    if raw.strip().casefold() in NULL_MARKERS:
        if required:
            raise ValueError(f"{field} is required")
        return None
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw.strip(), pattern).date()  # noqa: DTZ007
        except ValueError:
            continue
    raise ValueError(f"{field} has an unsupported date format: {raw!r}")


def _normalise_row(
    row: Mapping[str, str | None], headers: Mapping[str, str]
) -> NormalizedRow:
    symbol = _value(row, headers, "symbol").upper().removesuffix(".NS")
    if not symbol:
        raise ValueError("symbol is required")
    trade_date = _date(_value(row, headers, "trade_date"), "trade_date", required=True)
    listed_since = _date(_value(row, headers, "listed_since"), "listed_since")
    prices = {
        field: cast(Decimal, _decimal(_value(row, headers, field), field, required=True))
        for field in ("open", "high", "low", "close", "adj_close")
    }
    if any(value <= 0 for value in prices.values()):
        raise ValueError("OHLC and adjusted close values must be positive")
    if prices["high"] < max(prices["open"], prices["low"], prices["close"]):
        raise ValueError("high is below another OHLC value")
    if prices["low"] > min(prices["open"], prices["high"], prices["close"]):
        raise ValueError("low is above another OHLC value")
    volume_decimal = _decimal(_value(row, headers, "volume"), "volume", required=True)
    if volume_decimal is None or volume_decimal < 0 or volume_decimal != volume_decimal.to_integral_value():
        raise ValueError("volume must be a non-negative integer")

    def optional_decimal(field: str) -> Decimal | None:
        return _decimal(_value(row, headers, field), field)

    assert trade_date is not None
    return NormalizedRow(
        symbol=symbol,
        company_name=_value(row, headers, "company_name") or symbol,
        sector=_value(row, headers, "sector") or "Unclassified",
        industry=_value(row, headers, "industry") or None,
        listed_since=listed_since,
        trade_date=trade_date,
        open=prices["open"],
        high=prices["high"],
        low=prices["low"],
        close=prices["close"],
        adj_close=prices["adj_close"],
        volume=int(volume_decimal),
        pe_ratio=optional_decimal("pe_ratio"),
        pb_ratio=optional_decimal("pb_ratio"),
        market_cap=optional_decimal("market_cap"),
        dividend_yield=optional_decimal("dividend_yield"),
        eps=optional_decimal("eps"),
        beta=optional_decimal("beta"),
        sma_50=optional_decimal("sma_50"),
        sma_200=optional_decimal("sma_200"),
        rsi_14=optional_decimal("rsi_14"),
        macd=optional_decimal("macd"),
        volatility_annualized=optional_decimal("volatility_annualized"),
    )


def read_csv_files(paths: Iterable[str | Path]) -> tuple[list[NormalizedRow], list[RejectedRow]]:
    """Parse and validate one or more CSV files without touching the database."""

    accepted: list[NormalizedRow] = []
    rejected: list[RejectedRow] = []
    for input_path in paths:
        path = Path(input_path)
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = _resolve_headers(reader.fieldnames)
            for row_number, row in enumerate(reader, start=2):
                try:
                    accepted.append(_normalise_row(row, headers))
                except ValueError as exc:
                    rejected.append(RejectedRow(str(path), row_number, str(exc)))
    accepted.sort(key=lambda item: (item.symbol, item.trade_date))
    return accepted, rejected


async def _get_or_create_sector(session: AsyncSession, name: str) -> Sector:
    sector = await session.scalar(select(Sector).where(Sector.name == name))
    if sector is None:
        sector = Sector(name=name)
        session.add(sector)
        await session.flush()
    return sector


async def _get_or_create_stock(
    session: AsyncSession, row: NormalizedRow, sector: Sector
) -> Stock:
    stock = await session.scalar(select(Stock).where(Stock.symbol == row.symbol))
    if stock is None:
        stock = Stock(
            symbol=row.symbol,
            company_name=row.company_name,
            sector_id=sector.id,
            industry=row.industry,
            listed_since=row.listed_since,
        )
        session.add(stock)
        await session.flush()
    else:
        stock.company_name = row.company_name
        stock.sector_id = sector.id
        stock.industry = row.industry
        stock.listed_since = row.listed_since
    return stock


def _dialect_insert(session: AsyncSession, model: type[Any]) -> Any:
    dialect_name = session.get_bind().dialect.name
    if dialect_name == "postgresql":
        return postgresql_insert(model)
    if dialect_name == "sqlite":
        return sqlite_insert(model)
    raise RuntimeError(f"ETL upsert is unsupported for SQL dialect {dialect_name!r}")


async def _upsert(
    session: AsyncSession,
    model: type[Any],
    values: dict[str, Any],
    natural_key: Sequence[str],
) -> None:
    statement: Any = _dialect_insert(session, model).values(**values)
    update_values = {key: value for key, value in values.items() if key not in natural_key}
    statement = statement.on_conflict_do_update(
        index_elements=[getattr(model, key) for key in natural_key], set_=update_values
    )
    await session.execute(statement)


async def load_nifty_dataset(
    paths: Iterable[str | Path], session: AsyncSession
) -> LoadResult:
    """Load validated Nifty rows atomically and idempotently.

    Daily return is ``current adjusted close / previous adjusted close - 1`` per symbol.
    The first incoming row also consults an earlier price already in the database, which
    keeps incremental loads correct.
    """

    rows, rejected = read_csv_files(paths)
    rows_by_symbol: dict[str, list[NormalizedRow]] = defaultdict(list)
    for row in rows:
        rows_by_symbol[row.symbol].append(row)

    try:
        for symbol_rows in rows_by_symbol.values():
            first = symbol_rows[0]
            sector = await _get_or_create_sector(session, first.sector)
            stock = await _get_or_create_stock(session, first, sector)
            previous_close = await session.scalar(
                select(StockPrice.adj_close)
                .where(
                    StockPrice.stock_id == stock.id,
                    StockPrice.trade_date < first.trade_date,
                )
                .order_by(StockPrice.trade_date.desc())
                .limit(1)
            )

            for row in symbol_rows:
                if row.sector != sector.name:
                    sector = await _get_or_create_sector(session, row.sector)
                stock = await _get_or_create_stock(session, row, sector)
                daily_return = None
                if previous_close is not None and previous_close != Decimal(0):
                    daily_return = (row.adj_close / previous_close) - Decimal(1)
                await _upsert(
                    session,
                    StockPrice,
                    {
                        "stock_id": stock.id,
                        "trade_date": row.trade_date,
                        "open": row.open,
                        "high": row.high,
                        "low": row.low,
                        "close": row.close,
                        "adj_close": row.adj_close,
                        "volume": row.volume,
                        "daily_return": daily_return,
                    },
                    ("stock_id", "trade_date"),
                )
                await _upsert(
                    session,
                    StockFundamental,
                    {
                        "stock_id": stock.id,
                        "as_of_date": row.trade_date,
                        "pe_ratio": row.pe_ratio,
                        "pb_ratio": row.pb_ratio,
                        "market_cap": row.market_cap,
                        "dividend_yield": row.dividend_yield,
                        "eps": row.eps,
                        "beta": row.beta,
                    },
                    ("stock_id", "as_of_date"),
                )
                await _upsert(
                    session,
                    StockTechnicalIndicator,
                    {
                        "stock_id": stock.id,
                        "trade_date": row.trade_date,
                        "sma_50": row.sma_50,
                        "sma_200": row.sma_200,
                        "rsi_14": row.rsi_14,
                        "macd": row.macd,
                        "volatility_annualized": row.volatility_annualized,
                    },
                    ("stock_id", "trade_date"),
                )
                previous_close = row.adj_close
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return LoadResult(
        accepted_rows=len(rows),
        rejected_rows=tuple(rejected),
        symbols=tuple(sorted(rows_by_symbol)),
    )


async def _run_cli(paths: Sequence[str]) -> None:
    async with AsyncSessionFactory() as session:
        result = await load_nifty_dataset(paths, session)
    print(
        f"Loaded {result.accepted_rows} rows across {len(result.symbols)} symbols; "
        f"rejected {result.rejected_count} rows."
    )
    for rejected in result.rejected_rows:
        print(f"{rejected.source}:{rejected.row_number}: {rejected.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Nifty-50 CSV data into OptiVest")
    parser.add_argument("csv", nargs="+", help="One or more Kaggle CSV files")
    args = parser.parse_args()
    asyncio.run(_run_cli(args.csv))


if __name__ == "__main__":
    main()
