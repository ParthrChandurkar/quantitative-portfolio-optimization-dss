"""Integration tests for the Nifty CSV ETL pipeline."""

from __future__ import annotations

import csv
import math
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Sector,
    Stock,
    StockFundamental,
    StockPrice,
    StockTechnicalIndicator,
)
from app.etl.load_nifty_dataset import COLUMN_MAP, load_nifty_dataset, read_csv_files

FIXTURE = Path(__file__).parent / "fixtures" / "nifty_sample.csv"


async def count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def test_loader_imports_ten_rows_two_symbols_and_is_idempotent(
    session: AsyncSession,
) -> None:
    """FR-2 and NFR-7: canonical import and idempotent dated upserts."""

    first = await load_nifty_dataset([FIXTURE], session)
    assert first.accepted_rows == 10
    assert first.rejected_count == 0
    assert first.symbols == ("HDFCBANK", "INFY")
    assert await count(session, Sector) == 2
    assert await count(session, Stock) == 2
    assert await count(session, StockPrice) == 10
    assert await count(session, StockFundamental) == 10
    assert await count(session, StockTechnicalIndicator) == 10

    second = await load_nifty_dataset([FIXTURE], session)
    assert second.accepted_rows == 10
    assert await count(session, Sector) == 2
    assert await count(session, Stock) == 2
    assert await count(session, StockPrice) == 10
    assert await count(session, StockFundamental) == 10
    assert await count(session, StockTechnicalIndicator) == 10


async def test_daily_return_is_computed_per_symbol_in_date_order(
    session: AsyncSession,
) -> None:
    await load_nifty_dataset([FIXTURE], session)
    prices = (
        await session.execute(
            select(Stock.symbol, StockPrice.trade_date, StockPrice.daily_return)
            .join(StockPrice, StockPrice.stock_id == Stock.id)
            .order_by(Stock.symbol, StockPrice.trade_date)
        )
    ).all()
    by_symbol = {symbol: [] for symbol, _, _ in prices}
    for symbol, _, daily_return in prices:
        by_symbol[symbol].append(daily_return)

    assert by_symbol["HDFCBANK"][0] is None
    assert by_symbol["HDFCBANK"][1] == Decimal("0.1000000000")
    assert by_symbol["HDFCBANK"][2] == Decimal("0.1000000000")
    assert by_symbol["INFY"][0] is None
    assert by_symbol["INFY"][1] == Decimal("0.0500000000")


async def test_rerun_updates_existing_natural_key_without_duplicate(
    session: AsyncSession, tmp_path: Path
) -> None:
    await load_nifty_dataset([FIXTURE], session)
    amended = tmp_path / "amended.csv"
    content = FIXTURE.read_text(encoding="utf-8").replace(
        "2026-01-05,115,117,112,114,146.41,1400",
        "2026-01-05,115,119,112,118,146.41,9999",
    )
    amended.write_text(content, encoding="utf-8")
    await load_nifty_dataset([amended], session)

    assert await count(session, StockPrice) == 10
    hdfc = await session.scalar(select(Stock).where(Stock.symbol == "HDFCBANK"))
    latest = await session.scalar(
        select(StockPrice)
        .where(StockPrice.stock_id == hdfc.id)
        .order_by(StockPrice.trade_date.desc())
        .limit(1)
    )
    assert latest.close == Decimal("118.00")
    assert latest.volume == 9999


def test_column_map_accepts_header_variants(tmp_path: Path) -> None:
    """Header-name changes remain isolated to COLUMN_MAP."""

    variant = tmp_path / "variant.csv"
    variant.write_text(
        "Ticker,Company,Sector Name,Trade Date,Open Price,High Price,Low Price,Close Price,Adjusted Close,Traded Volume\n"
        "RELIANCE,Reliance Industries,Energy,2026-01-02,100,105,99,103,103,5000\n",
        encoding="utf-8",
    )
    rows, rejected = read_csv_files([variant])
    assert rejected == []
    assert rows[0].symbol == "RELIANCE"
    assert set(COLUMN_MAP) >= {"symbol", "trade_date", "adj_close"}


def test_invalid_rows_are_rejected_with_row_number(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.csv"
    invalid.write_text(
        "Symbol,Date,Open,High,Low,Close,Adj Close,Volume\n"
        "INFY,2026-01-02,100,105,99,-1,103,5000\n",
        encoding="utf-8",
    )
    rows, rejected = read_csv_files([invalid])
    assert rows == []
    assert len(rejected) == 1
    assert rejected[0].row_number == 2
    assert "positive" in rejected[0].reason


def test_missing_required_headers_fail_fast(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    missing.write_text("Symbol,Date\nINFY,2026-01-02\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        read_csv_files([missing])


async def test_real_kaggle_headers_load_two_hundred_rows(
    session: AsyncSession, tmp_path: Path
) -> None:
    """Real 25-column headers, timezone dates, and source units remain supported."""

    fixture = tmp_path / "nifty_real_header_200.csv"
    headers = [
        "Date", "Ticker", "Company_Name", "Sector", "Open", "High", "Low",
        "Close", "Volume", "Dividend", "Stock_Split", "Daily_Return",
        "Volatility_20D", "MA_50", "MA_200", "Market_Cap", "PE_Ratio",
        "Forward_PE", "PEG_Ratio", "Price_to_Book", "Dividend_Yield", "EPS",
        "Beta", "52Week_High", "52Week_Low",
    ]
    with fixture.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for index in range(200):
            symbol = "HDFCBANK.NS" if index % 2 == 0 else "INFY.NS"
            close = Decimal(100) + Decimal(index // 2)
            writer.writerow(
                {
                    "Date": f"{date(2025, 1, 1) + timedelta(days=index // 2)} 00:00:00+05:30",
                    "Ticker": symbol,
                    "Company_Name": symbol.removesuffix(".NS"),
                    "Sector": "Financial Services" if index % 2 == 0 else "IT",
                    "Open": close,
                    "High": close + 1,
                    "Low": close - 1,
                    "Close": close,
                    "Volume": 1_000 + index,
                    "Dividend": 0,
                    "Stock_Split": "",
                    "Daily_Return": 999,
                    "Volatility_20D": "0.02",
                    "MA_50": "98.5",
                    "MA_200": "95.25",
                    "Market_Cap": "1000000000000",
                    "PE_Ratio": "20.5",
                    "Forward_PE": "19.5",
                    "PEG_Ratio": "",
                    "Price_to_Book": "3.25",
                    "Dividend_Yield": "1.2",
                    "EPS": "50.5",
                    "Beta": "0.9",
                    "52Week_High": "150",
                    "52Week_Low": "80",
                }
            )

    result = await load_nifty_dataset([fixture], session)
    assert result.accepted_rows == 200
    assert result.rejected_count == 0
    assert await count(session, Stock) == 2
    assert await count(session, StockPrice) == 200
    assert await count(session, StockFundamental) == 200
    assert await count(session, StockTechnicalIndicator) == 200

    hdfc = await session.scalar(select(Stock).where(Stock.symbol == "HDFCBANK"))
    first_price = await session.scalar(
        select(StockPrice)
        .where(StockPrice.stock_id == hdfc.id)
        .order_by(StockPrice.trade_date)
        .limit(1)
    )
    first_fundamental = await session.scalar(
        select(StockFundamental)
        .where(StockFundamental.stock_id == hdfc.id)
        .order_by(StockFundamental.as_of_date)
        .limit(1)
    )
    first_technical = await session.scalar(
        select(StockTechnicalIndicator)
        .where(StockTechnicalIndicator.stock_id == hdfc.id)
        .order_by(StockTechnicalIndicator.trade_date)
        .limit(1)
    )
    assert first_price.adj_close == first_price.close == Decimal("100.00")
    assert first_price.daily_return is None  # Source Daily_Return is intentionally ignored.
    assert first_fundamental.pb_ratio == Decimal("3.2500")
    assert first_technical.sma_50 == Decimal("98.50")
    assert first_technical.sma_200 == Decimal("95.25")
    assert first_technical.volatility_annualized == pytest.approx(
        Decimal("0.02") * Decimal(str(math.sqrt(252))), abs=Decimal("0.00000001")
    )
