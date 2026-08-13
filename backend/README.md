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

Run its independent 90% coverage gate with:

```bash
pytest tests/optimization --cov=app/optimization --cov-fail-under=90
```
