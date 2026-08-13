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
pytest --cov=app/db --cov=app/etl --cov-report=term-missing
```
