# OptiVest data workspace

The unmodified source dataset is stored locally in `data/raw/` and is intentionally excluded from Git because the historical CSV is approximately 84 MiB.

## Source

- Dataset: [Nifty50 Stocks (1999–2026) Daily OHLCV & Fundamentals](https://www.kaggle.com/datasets/kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals)
- Kaggle identifier: `kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals`
- License reported by Kaggle: CC0 1.0
- Metadata source: Yahoo Finance
- Downloaded: 2026-08-13

## Local raw files

| File | Rows | Columns | SHA-256 |
|---|---:|---:|---|
| `data/raw/nifty50_historical_data.csv` | 287,310 | 25 | `F6FF6BA3EAFAE0C3C35D629D3D8CF440623B761FE0141EE8C1495752565EF646` |
| `data/raw/nifty50_summary_statistics.csv` | 49 | 18 | `E89B952953BFBC01FF10C7E8F69ECDF97AA637A0FBFBA4E6E12AFD471F7D00F8` |
| `data/raw/metadata.json` | — | — | `7D51C63D1BBFD10373A3D41626878003D642AF62F675D737851F789416CD8FEE` |

## Re-download

```bash
kaggle datasets download \
  -d kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals \
  -p data/raw \
  --unzip
```

## Reconciled PostgreSQL load

The real-data checkpoint was completed on 2026-08-14 against PostgreSQL 16 after applying Alembic revision `0001`. Full details are in [PROFILE_REPORT.md](PROFILE_REPORT.md).

| Table | Rows after first load | Rows after identical rerun |
|---|---:|---:|
| `stocks` | 49 | 49 |
| `stock_prices` | 287,263 | 287,263 |
| `stock_fundamentals` | 287,263 | 287,263 |
| `stock_technical_indicators` | 287,263 | 287,263 |

Both executions accepted 287,263 rows and rejected the same 47 source rows whose OHLC values were zero. The first run took 563.155 seconds and the idempotency run took 423.649 seconds on the local development machine. The summary-statistics CSV is an aggregate reference file and is not loaded into the dated tables.

## Dataset usage status

- Full column, type, null, numeric-validity, symbol, and date-range profiling is complete.
- The Phase 2 mapping layer is reconciled to all real headers; no schema change was required.
- Full PostgreSQL ingestion and full-volume idempotency validation are complete.
- Stored `daily_return` values were independently verified for HDFCBANK, INFY, and RELIANCE.
- Phase 7 now queries `stock_prices` directly for buy-and-hold and periodic-rebalance backtests. The real PostgreSQL integration run used RELIANCE, TCS, HDFCBANK, INFY, and ITC across 249 market dates in 2025, with a maximum four-day calendar gap and no missing-data warnings.
- The equal-weight monthly-rebalance integration check changed ₹1,000,000 to ₹993,348.58; this is a pipeline-validation result, not an investment recommendation.
- Corporate-action outliers and the 47 rejected zero-price rows documented in the profile remain visible to downstream data-quality filters. The loaded dataset is ready for subsequent API wiring and deeper model evaluation.
- Phase 8 report generation consumes the same Phase 7 real-data analytics bundle and persisted snapshot values; it introduces no new dataset transformation or alternative metric calculation. Dataset row counts remain unchanged.
- Phase 9 now loads the full 49-stock universe through the authenticated HTTP optimization endpoint. The live integration check completed signup, ownership validation, a 252-observation covariance build, SciPy solve, and persisted holdings/explanations in one response within the five-second solver budget. Its temporary user records were removed afterward; dataset table counts remain unchanged.
