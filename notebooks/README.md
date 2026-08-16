# OptiVest Analysis Notebooks

These presentation notebooks use the real PostgreSQL-loaded Nifty-50 data and import the production OptiVest backend modules. They are read-only: optimization and scenario demonstrations run in memory and are not persisted.

Run them in this order:

1. `01_eda_nifty50.ipynb` — database coverage, sectors, prices, returns, correlations, volatility, fundamentals, and ETL quality notes.
2. `02_optimization_methodology.ipynb` — five-stock SciPy/PuLP worked example and the real 49-stock efficient frontier.
3. `03_explainability_and_scenarios.ipynb` — live-universe optimization narratives, binding-constraint insights, and a market-crash re-solve.
4. `04_methodology_integrity_case_study.ipynb` — look-ahead-bias correction and static-versus-walk-forward out-of-sample evidence.

## Setup

From the repository root, use Python 3.11 or newer and install the backend plus notebook dependencies:

```powershell
python -m pip install -e backend
python -m pip install -r notebooks/requirements.txt
```

Start the already-loaded PostgreSQL service. Database credentials and host settings are read only through `backend/app/core/config.py` and `backend/app/db/session.py`; the notebooks contain no credentials.

```powershell
docker compose -f backend/docker-compose.yml up -d postgres
```

Open the notebooks interactively with `jupyter lab`, or verify a clean top-to-bottom execution without manual input:

```powershell
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/01_eda_nifty50.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/02_optimization_methodology.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/03_explainability_and_scenarios.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/04_methodology_integrity_case_study.ipynb
```

The executed notebooks retain their tables and matplotlib/seaborn charts for standalone review. The real dataset must already be loaded as described in [`data/README.md`](../data/README.md).
