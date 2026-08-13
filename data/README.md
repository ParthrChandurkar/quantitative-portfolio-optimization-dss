# OptiVest data workspace

The unmodified source dataset is stored locally in `data/raw/` and is intentionally excluded from Git because the historical CSV is approximately 84 MiB.

## Source

- Dataset: [Nifty50 Stocks (1999–2026) Daily OHLCV & Fundamentals](https://www.kaggle.com/datasets/kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals)
- Kaggle identifier: `kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals`
- License reported by Kaggle: CC0 1.0
- Dataset metadata period: 1999-01-01 through 2026-01-31
- Metadata source: Yahoo Finance
- Downloaded: 2026-08-13

## Local raw files

| File | Rows | Columns | SHA-256 |
|---|---:|---:|---|
| `data/raw/nifty50_historical_data.csv` | 287,310 | 25 | `F6FF6BA3EAFAE0C3C35D629D3D8CF440623B761FE0141EE8C1495752565EF646` |
| `data/raw/nifty50_summary_statistics.csv` | 49 | 18 | `E89B952953BFBC01FF10C7E8F69ECDF97AA637A0FBFBA4E6E12AFD471F7D00F8` |
| `data/raw/metadata.json` | — | — | `7D51C63D1BBFD10373A3D41626878003D642AF62F675D737851F789416CD8FEE` |

## Re-download

From the repository root:

```bash
kaggle datasets download \
  -d kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals \
  -p data/raw \
  --unzip
```

## ETL reconciliation notes

The historical CSV uses several headers that should be added to the Phase 2 loader's `COLUMN_MAP` before ingestion:

- `Company_Name`
- `MA_50` and `MA_200`
- `Price_to_Book`
- `Volatility_20D`

Header normalization already handles underscore variants such as `Company_Name`, `PE_Ratio`, `Market_Cap`, and `Dividend_Yield` where an equivalent spaced alias exists. `MA_50`, `MA_200`, `Price_to_Book`, and the 20-day volatility field require explicit semantic mapping decisions.

## Dataset usage status

Status after Phase 6:

- The Kaggle files are downloaded and their dimensions, headers, metadata, and checksums are recorded.
- Phase 2 ETL behavior is tested against a synthetic fixture, not this full raw dataset.
- Phases 4–6 are validated against deterministic synthetic/golden optimization fixtures.
- The real CSV has not yet undergone EDA, ETL mapping reconciliation, cleaning, PostgreSQL ingestion, or production optimization.
- Phase 6 sector sensitivity coefficients are declared calibration assumptions and have not been estimated from the raw dataset.
