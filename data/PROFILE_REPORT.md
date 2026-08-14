# Nifty-50 Real Dataset Profile and ETL Reconciliation

Profile date: 2026-08-14. Counts come from the unmodified files in `data/raw/`. Monetary values are Indian rupees (₹) unless a field is a ratio or percentage.

## Executive findings

- The historical file has 287,310 rows, 25 columns, 49 unique tickers, and no duplicate `(Ticker, Date)` keys. Its local-date range is 1999-01-01 through 2026-01-30.
- The summary file has 49 rows, 18 columns, and one row per ticker.
- Every non-null value in an expected numeric column parsed as numeric. Forty-seven rows have zero for every OHLC value and were rejected.
- Header and unit differences were isolated to `COLUMN_MAP` and ETL normalization. No schema or initial-migration change was required.
- The real load produced 49 stocks and 287,263 rows in each dated table. A complete rerun produced identical counts.

## Historical file profile

`nifty50_historical_data.csv` has shape `(287310, 25)`.

| Source column | pandas dtype | Nulls | Destination / treatment |
|---|---|---:|---|
| `Date` | object | 0 | All dated tables; parse `+05:30` ISO timestamps while retaining local date. |
| `Ticker` | object | 0 | `stocks.symbol`; strip `.NS`. |
| `Company_Name` | object | 0 | `stocks.company_name`. |
| `Sector` | object | 0 | `sectors.name`. |
| `Open` | float64 | 0 | `stock_prices.open` (₹). |
| `High` | float64 | 0 | `stock_prices.high` (₹). |
| `Low` | float64 | 0 | `stock_prices.low` (₹). |
| `Close` | float64 | 0 | `stock_prices.close` and fallback `adj_close` (₹). |
| `Volume` | int64 | 0 | `stock_prices.volume`. |
| `Dividend` | float64 | 0 | Unmapped. |
| `Stock_Split` | float64 | 287,212 | Unmapped. |
| `Daily_Return` | float64 | 49 | Unmapped; recomputed by ETL. |
| `Volatility_20D` | float64 | 980 | `volatility_annualized`; multiply daily value by `sqrt(252)`. |
| `MA_50` | float64 | 2,401 | `sma_50`; explicit alias added. |
| `MA_200` | float64 | 9,751 | `sma_200`; explicit alias added. |
| `Market_Cap` | int64 | 0 | `market_cap` in raw ₹. |
| `PE_Ratio` | float64 | 5,857 | `pe_ratio`. |
| `Forward_PE` | float64 | 0 | Unmapped. |
| `PEG_Ratio` | float64 | 287,310 | Unmapped; entirely null. |
| `Price_to_Book` | float64 | 0 | `pb_ratio`; explicit alias added. |
| `Dividend_Yield` | float64 | 5,857 | `dividend_yield`; source percentage-point units. |
| `EPS` | float64 | 0 | `eps` in ₹ per share. |
| `Beta` | float64 | 3,759 | `beta`. |
| `52Week_High` | float64 | 0 | Unmapped. |
| `52Week_Low` | float64 | 0 | Unmapped. |

`RSI_14` and `MACD` are absent, so their existing nullable destination fields remain null.

### Numeric, key, and quality checks

- Non-numeric, non-null values in expected numeric columns: **0**.
- Unique tickers: **49**; duplicate `(Ticker, Date)` rows: **0**; invalid dates: **0**.
- Non-positive OHLC rows: **47**. Every one has zero in all four OHLC fields.
- Strict OHLC ordering flagged 197 rows, but the non-zero cases differ only by binary floating-point noise. The ETL now allows `0.000001` tolerance while still rejecting zero prices.
- Source `Daily_Return` matches `Close / prior Close - 1` within `1e-10` for every comparable row. Its 49 nulls are the first observation of each ticker.

### Date coverage by ticker

| Ticker | First date | Last date | Rows |
|---|---|---|---:|
| ADANIENT.NS | 2002-07-01 | 2026-01-30 | 5,858 |
| ADANIPORTS.NS | 2007-11-27 | 2026-01-30 | 4,482 |
| APOLLOHOSP.NS | 2002-07-01 | 2026-01-30 | 5,856 |
| ASIANPAINT.NS | 2002-07-01 | 2026-01-30 | 5,856 |
| AXISBANK.NS | 1999-01-01 | 2026-01-30 | 6,767 |
| BAJAJ-AUTO.NS | 2002-07-01 | 2026-01-30 | 5,859 |
| BAJAJFINSV.NS | 2002-08-12 | 2026-01-30 | 5,825 |
| BAJFINANCE.NS | 2002-07-01 | 2026-01-30 | 5,856 |
| BHARTIARTL.NS | 2002-07-01 | 2026-01-30 | 5,856 |
| BPCL.NS | 1999-01-01 | 2026-01-30 | 6,767 |
| BRITANNIA.NS | 1999-01-01 | 2026-01-30 | 6,770 |
| CIPLA.NS | 1999-01-01 | 2026-01-30 | 6,769 |
| COALINDIA.NS | 2010-11-04 | 2026-01-30 | 3,759 |
| DIVISLAB.NS | 2003-03-12 | 2026-01-30 | 5,677 |
| DRREDDY.NS | 1999-01-01 | 2026-01-30 | 6,767 |
| EICHERMOT.NS | 1999-01-01 | 2026-01-30 | 6,767 |
| GRASIM.NS | 2002-07-01 | 2026-01-30 | 5,856 |
| HCLTECH.NS | 2002-08-12 | 2026-01-30 | 5,830 |
| HDFCBANK.NS | 1999-01-01 | 2026-01-30 | 6,770 |
| HDFCLIFE.NS | 2017-11-17 | 2026-01-30 | 2,027 |
| HEROMOTOCO.NS | 2002-07-01 | 2026-01-30 | 5,856 |
| HINDALCO.NS | 1999-01-01 | 2026-01-30 | 6,770 |
| HINDUNILVR.NS | 1999-01-01 | 2026-01-30 | 6,770 |
| ICICIBANK.NS | 2002-07-01 | 2026-01-30 | 5,856 |
| INDUSINDBK.NS | 2002-07-01 | 2026-01-30 | 5,857 |
| INFY.NS | 1999-01-01 | 2026-01-30 | 6,770 |
| ITC.NS | 1999-01-01 | 2026-01-30 | 6,767 |
| JSWSTEEL.NS | 2003-05-08 | 2026-01-30 | 5,636 |
| KOTAKBANK.NS | 2001-07-02 | 2026-01-30 | 6,118 |
| LT.NS | 2002-07-01 | 2026-01-30 | 5,859 |
| LTIM.NS | 2016-07-21 | 2026-01-30 | 2,355 |
| M&M.NS | 1999-01-01 | 2026-01-30 | 6,768 |
| MARUTI.NS | 2003-07-09 | 2026-01-30 | 5,592 |
| NESTLEIND.NS | 2002-08-12 | 2026-01-30 | 5,829 |
| NTPC.NS | 2004-11-05 | 2026-01-30 | 5,245 |
| ONGC.NS | 1999-01-01 | 2026-01-30 | 6,767 |
| POWERGRID.NS | 2007-10-05 | 2026-01-30 | 4,518 |
| RELIANCE.NS | 1999-01-01 | 2026-01-30 | 6,767 |
| SBILIFE.NS | 2017-10-03 | 2026-01-30 | 2,059 |
| SBIN.NS | 1999-01-01 | 2026-01-30 | 6,768 |
| SHREECEM.NS | 2001-07-02 | 2026-01-30 | 6,116 |
| SUNPHARMA.NS | 1999-01-01 | 2026-01-30 | 6,770 |
| TATACONSUM.NS | 1999-01-01 | 2026-01-30 | 6,767 |
| TATASTEEL.NS | 1999-01-01 | 2026-01-30 | 6,770 |
| TCS.NS | 2002-08-12 | 2026-01-30 | 5,827 |
| TECHM.NS | 2006-08-28 | 2026-01-30 | 4,793 |
| TITAN.NS | 1999-01-01 | 2026-01-30 | 6,770 |
| ULTRACEMCO.NS | 2002-08-12 | 2026-01-30 | 5,826 |
| WIPRO.NS | 1999-01-01 | 2026-01-30 | 6,770 |

## Summary file profile

`nifty50_summary_statistics.csv` has shape `(49, 18)`, 49 unique tickers, and no duplicates.

| Source column | pandas dtype | Nulls |
|---|---|---:|
| `Ticker` | object | 0 |
| `Company_Name` | object | 0 |
| `Sector` | object | 0 |
| `First_Date` | object | 0 |
| `Last_Date` | object | 0 |
| `Total_Trading_Days` | int64 | 0 |
| `Starting_Price` | float64 | 0 |
| `Ending_Price` | float64 | 0 |
| `Total_Return_%` | float64 | 0 |
| `Highest_Price` | float64 | 0 |
| `Lowest_Price` | float64 | 0 |
| `Avg_Daily_Volume` | float64 | 0 |
| `Total_Dividends_Paid` | float64 | 0 |
| `Number_of_Splits` | int64 | 0 |
| `Avg_Daily_Return_%` | float64 | 0 |
| `Volatility_%` | float64 | 0 |
| `Current_Market_Cap` | int64 | 0 |
| `Current_PE_Ratio` | float64 | 1 |

All expected numeric fields have zero non-numeric, non-null values. This is aggregate metadata without a single defensible `as_of_date`, so all 18 summary columns are explicitly **unmapped for ingestion** and the file is retained for EDA and validation.

## Explicit assumptions and unmapped fields

1. `Close` supplies both `close` and `adj_close`: the export has no adjusted-close column, and its Yahoo-derived OHLC series is the basis of its supplied returns. This preserves consistency but does not claim corporate-action anomalies are absent.
2. `Daily_Return` is ignored as input. The loader recomputes `current adj_close / previous adj_close - 1` per ticker in local-date order.
3. `Volatility_20D` has the scale of daily rolling standard deviation (median about 0.0175) and is annualized using `sqrt(252)`.
4. `Dividend_Yield` remains in source percentage-point units (median about 0.98), rather than being divided by 100.
5. `Market_Cap` is raw rupees; observed values range from about ₹698 billion to ₹18.88 trillion.
6. Historical columns `Dividend`, `Stock_Split`, `Daily_Return`, `Forward_PE`, `PEG_Ratio`, `52Week_High`, and `52Week_Low` are unmapped. None justifies a new nullable schema column for current optimizer requirements.

## PostgreSQL load and idempotency

PostgreSQL 16 ran through `backend/docker-compose.yml`; Alembic revision `0001` created the unchanged Phase 2 schema.

| Result | First load | Full rerun |
|---|---:|---:|
| Accepted source rows | 287,263 | 287,263 |
| Rejected source rows | 47 | 47 |
| `stocks` | 49 | 49 |
| `stock_prices` | 287,263 | 287,263 |
| `stock_fundamentals` | 287,263 | 287,263 |
| `stock_technical_indicators` | 287,263 | 287,263 |
| Runtime on development machine | 563.155 s | 423.649 s |

Unchanged counts after a complete second invocation prove idempotency on the real natural keys.

## Manual daily-return spot checks

The spreadsheet formula is `(current close / previous close) - 1`. Stored values use scale 10, so the tiny differences are decimal quantization.

| Symbol | Trade date | Previous close (₹) | Current close (₹) | Manual return | Stored return | Absolute difference |
|---|---|---:|---:|---:|---:|---:|
| HDFCBANK | 2026-01-28 | 926.400024 | 932.700012 | 0.006800504779 | 0.0068005048 | 2.14e-11 |
| HDFCBANK | 2026-01-29 | 932.700012 | 935.500000 | 0.003002023969 | 0.0030020240 | 3.05e-11 |
| HDFCBANK | 2026-01-30 | 935.500000 | 929.250000 | -0.006680919294 | -0.0066809193 | 5.51e-12 |
| INFY | 2026-01-28 | 1682.699951 | 1666.500000 | -0.009627355822 | -0.0096273558 | 2.22e-11 |
| INFY | 2026-01-29 | 1666.500000 | 1659.500000 | -0.004200420042 | -0.0042004200 | 4.20e-11 |
| INFY | 2026-01-30 | 1659.500000 | 1641.000000 | -0.011147936125 | -0.0111479361 | 2.53e-11 |
| RELIANCE | 2026-01-28 | 1380.500000 | 1396.699951 | 0.011734843297 | 0.0117348433 | 2.73e-12 |
| RELIANCE | 2026-01-29 | 1396.699951 | 1391.000000 | -0.004081013368 | -0.0040810134 | 3.20e-11 |
| RELIANCE | 2026-01-30 | 1391.000000 | 1395.400024 | 0.003163209500 | 0.0031632095 | 3.15e-13 |

The checks confirm correct per-symbol ordering and Close-based calculation with no one-day offset.
