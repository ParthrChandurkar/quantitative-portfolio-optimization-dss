# OptiVest data layer

All persisted currency amounts are denominated in Indian rupees (INR) and use fixed-precision PostgreSQL `NUMERIC` columns.

## Install

```bash
python -m pip install -e ".[test]"
```

## Configure PostgreSQL

Set an asynchronous SQLAlchemy connection URL before running application code:

```text
DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5432/optivest
```

Create or upgrade the schema from this directory:

```bash
alembic upgrade head
```

PostgreSQL must permit creation of the `pgcrypto` extension. The initial migration uses `gen_random_uuid()` for every table's primary key.

## Load the Nifty dataset

```bash
python -m app.etl.load_nifty_dataset path/to/nifty.csv
```

Multiple CSV paths may be supplied. Raw header aliases are declared only in `COLUMN_MAP` in `app/etl/load_nifty_dataset.py`. The loader validates rows, calculates daily adjusted-close return per symbol, and upserts dated records, so rerunning an import does not duplicate observations.

## Verify

```bash
ruff check app tests alembic
mypy app
pytest --cov=app --cov-report=term-missing
```

## Optimization engine

The framework-independent engine is imported without FastAPI:

```python
from app.optimization import OptimizationInput, solve

result = solve(problem)
```

Returns, volatility, weights, and sector caps use decimal values (`0.14` means 14%). Budgets and resulting allocation amounts are denominated in Indian rupees. `Auto` dispatches continuous problems to the SciPy quadratic solver and cardinality problems to the PuLP/CBC Konno–Yamazaki MAD model. OR-Tools can be selected explicitly for CP-SAT support selection followed by a restricted SciPy QP.

The result contract reports solver status, weights, objective and risk-return metrics, named C1–C7 constraint checks, timing, shadow prices when available, Euler variance contributions, and excluded-stock diagnostics. No HTTP or framework type is exposed by the package.

### Deterministic explanations

`app.explainability.build_explanations(result)` converts a feasible optimization result into an `ExplainabilityBundle` containing holding-level reasons, notable exclusions, material shadow-price insights, stock and sector concentration measures, a diversification score, and a display-ready portfolio summary. The service uses fixed rules and pure string templates only; it makes no generative-model or external API calls. Its item fields align with the `explanation_items` table and also expose the Phase 3 `rationale` and `model_score` display fields.

### Scenario simulation

`app.scenarios.run_scenario(base_inputs, scenario_type, params)` applies a pure shock transform to expected returns, covariance, INR budget, or risk constraints and then invokes the optimization and explainability layers again. Supported scenarios are market crash, rate increase, inflation, sector crash, budget increase, budget reduction, and risk-profile change.

The result includes baseline and simulated metrics, holding-level weight changes and directions, regenerated explanations, nominal and inflation-adjusted return where applicable, and an explicit budget-scale/lot-feasibility classification. Sector sensitivity coefficients are documented assumptions in `app/scenarios/sensitivity_tables.py`; they are not represented as empirically fitted values.

### Analytics dashboard service

`await app.analytics.get_analytics(snapshot_or_weights, universe, date_range, session=session)` returns chart-ready allocation, risk-return, growth projection, historical performance, risk metrics, efficient-frontier, and sector-distribution sections. Values and VaR amounts are INR.

Historical performance is queried from `stock_prices` and includes both buy-and-hold and configurable periodic-rebalance series. Missing observations freeze that stock position for the date; this also handles the 47 zero-OHLC source rows rejected during ETL. Allocations for stocks not yet listed remain cash, and closed-market dates are not manufactured. The efficient frontier reuses the Phase 4 SciPy solver for every target-return point.

Run the analytics coverage gate and the opt-in real PostgreSQL integration test with:

```bash
pytest tests/analytics --cov=app.analytics --cov-fail-under=85
REAL_DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5433/optivest \
  pytest tests/analytics/test_backtest_real_data_integration.py
```

### PDF reports

`await app.reports.generate_report(snapshot_id, report_type, user_id, session=session)` produces Portfolio Summary, Optimization Report, and Investment Recommendation PDFs. Report context reuses persisted snapshot, holding, explanation, and constraint values plus the Phase 7 analytics bundle. Generated artifacts are written through the `ReportStorage` interface and recorded in the `reports` table.

## ML return forecasting

The optimize request accepts `return_estimation_method` as either
`historical_mean` (the unchanged default) or `ml_forecast`. The latter uses the saved
gradient-boosting model while the covariance matrix and OR solver remain unchanged.
To regenerate the ignored model artifact and reproduce the fixed out-of-sample
comparison against the loaded PostgreSQL data, run from this directory:

```bash
python -m scripts.compare_return_estimation_methods --output ml-comparison.json
```

The command trains only on feature and target dates strictly before its recorded
cutoff. The checked-in results and limitations are in `../docs/methodology-notes.md`.

WeasyPrint requires its native Pango runtime. Linux deployments should install the distribution packages documented by WeasyPrint. On Windows, install current MSYS2 Pango and either use the standard `C:\msys64\mingw64\bin` location detected by the renderer or set `WEASYPRINT_DLL_DIRECTORIES` explicitly. Local output defaults to `generated-reports/` and can be redirected with `REPORT_STORAGE_ROOT`.

Run the reports coverage gate with:

```bash
pytest tests/reports --cov=app.reports --cov-fail-under=80
```

### FastAPI system wiring

Apply all migrations (including the Phase 9 refresh-token table), configure the JWT
secret, and start the API from `backend/`:

```text
DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5433/optivest
JWT_SECRET=replace-with-a-long-random-production-secret
JWT_ACCESS_EXPIRY=900
JWT_REFRESH_EXPIRY=2592000
COVARIANCE_LOOKBACK_DAYS=252
CORS_ORIGINS=http://localhost:5173
DEBUG=false
```

```bash
alembic upgrade head
uvicorn main:app --reload
```

The versioned API is available under `/api/v1`. JSON responses use the shared
`data`/`error` envelope; the report download endpoint is intentionally raw
`application/pdf`. All currency request and response values are Indian rupees (INR).

Run the Phase 9 API/service coverage gate and its opt-in 49-stock PostgreSQL test with:

```bash
pytest tests/api --cov=app.api --cov=app.services --cov-fail-under=80
REAL_DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5433/optivest \
  pytest tests/api/test_optimization.py::test_real_49_stock_optimization_through_http_api
```

Run its independent 90% coverage gate with:

```bash
pytest tests/optimization --cov=app/optimization --cov-fail-under=90
```
