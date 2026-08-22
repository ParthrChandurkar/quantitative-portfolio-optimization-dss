# AI-Driven Personalized Investment Planning and Portfolio Optimization

**OptiVest** is an institutional-style decision-support system for constructing personalized Nifty portfolios. It combines a real Operations Research engine—continuous and mixed-integer constrained optimization—with an additive AI layer for market-return forecasting, investor risk profiling, grounded portfolio Q&A, and personalized alerts.

This is not a tutorial or fixture-only demonstration. The running system uses PostgreSQL data loaded from 287,310 real market rows, solves and explains portfolios over a 49-stock universe, re-solves explicit stress scenarios, validates performance on dates excluded from estimation, and generates auditable PDF reports. During development, a look-ahead-biased backtest was detected, documented, and replaced with a structurally disjoint out-of-sample evaluation.

> Academic decision support only. OptiVest does not execute trades and is not personalized investment advice. All monetary values are Indian rupees (INR).

## Quick Facts

| Measure | Verified value |
|---|---:|
| Raw historical dataset | 287,310 rows × 25 columns |
| Loaded universe | 49 stocks |
| Accepted dated records | 287,263 rows in each price, fundamental, and technical table |
| Database migrations | 7 Alembic revisions |
| API surface | 24 paths / 28 HTTP operations |
| Production ML models | 4 |
| Backend tests | 228/228 with real PostgreSQL enabled |
| Backend combined coverage | 90.31% |
| Frontend tests | 47/47 |
| Frontend coverage | 83.00% statements / 96.00% lines |

## Operations Research Core

- Continuous mean-variance quadratic optimization using SciPy SLSQP.
- Cardinality-constrained mean absolute deviation MILP using PuLP/CBC.
- OR-Tools CP-SAT support selection combined with continuous weight optimization.
- Long-only budget identity, stock-weight limits, sector caps, risk/return targets, cardinality, and minimum-lot constraints.
- Independent feasibility checks, binding-constraint logs, marginal return/risk contributions, and deterministic “Why?” narratives.
- Seven scenario families that transform `mu`, covariance, budget, or constraints and then re-solve; results are never produced by merely scaling portfolio value.
- Efficient-frontier construction plus static and monthly walk-forward out-of-sample backtests using real PostgreSQL prices.

## AI / Personalization Layer

- **ML return forecasting:** a leakage-safe gradient-boosting regressor supplies an optional expected-return vector; historical mean remains the unchanged default.
- **ML risk profiling:** logistic regression reproduces a transparent questionnaire rubric and recommends visible, editable OR defaults.
- **Grounded NLP assistant:** TF-IDF plus logistic-regression intent routing answers only from stored explanations, analytics, allocations, and real scenario re-solves—no external LLM is used.
- **Personalized alerts:** explicit profile-drift rules and per-stock Isolation Forests produce deduplicated, numerically grounded notifications.
- **Honest evaluation:** the ML forecast underperformed historical mean on the recorded OOS period, and the synthetic-label accuracy caveats for risk and intent classification are retained in the report.

## Verified Product Evidence

The closing real-data walkthrough used a fresh account, personalized moderate-risk defaults (`0.22` risk tolerance, `15%` stock cap, `30%` sector cap), and a ₹10,00,000 budget.

| Result | Historical mean | ML forecast |
|---|---:|---:|
| Solver time | 66 ms | 172 ms |
| Expected return | 41.8578% | 24.8629% |
| Expected volatility | 15.9253% | 15.4487% |
| Sharpe ratio | 2.6284 | 1.6094 |
| Diversification score | 79.50 | 84.00 |
| Holdings | 7 | 7 |

The historical portfolio held AXISBANK, BPCL, EICHERMOT, HEROMOTOCO, HINDALCO, SBIN, and TATASTEEL. The ML portfolio held ADANIENT, COALINDIA, HCLTECH, INDUSINDBK, ITC, ONGC, and TECHM. A 20% beta-scaled crash re-solve reduced the ML portfolio’s expected return from 24.8629% to 19.1097%, increased volatility from 15.4487% to 16.2793%, and reduced Sharpe from 1.6094 to 1.1739.

The same walkthrough confirmed a zero-overlap 252-observation estimation window and 249-observation evaluation window. Its historical-snapshot periodic backtest finished at ₹10,71,780.92 with 7.2980% annualized realized return, 0.5178 realized Sharpe, and −11.4126% maximum drawdown. All three PDF types downloaded as valid files and contained the mandatory academic disclaimer.

## Methodology and Report

- [Phase requirements and implementation traceability](docs/phase1-requirements/traceability-matrix.md)
- [Complete final project report](docs/final-report/)
- [Methodology notes: look-ahead-bias correction and walk-forward findings](docs/methodology-notes.md) — the most important document for understanding the project’s research rigor, including mistakes found and corrected.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript 5.9, Vite, React Router, React Query |
| API | Python 3.11+, FastAPI, Pydantic, JWT, Argon2 |
| Data | PostgreSQL 16, SQLAlchemy 2 async ORM, Alembic, asyncpg |
| OR and analytics | NumPy, SciPy SLSQP, PuLP/CBC, OR-Tools CP-SAT |
| AI/ML | scikit-learn gradient boosting, logistic regression, TF-IDF, Isolation Forest |
| Reports and tests | Jinja2, WeasyPrint, pytest, pytest-cov, Vitest, Testing Library |

## Repository Layout

```text
backend/                  FastAPI, database, ETL, OR, analytics, AI, reports, tests
data/raw/                 Local Kaggle CSVs (ignored because of size)
data/PROFILE_REPORT.md    Full real-data profiling and reconciliation evidence
docs/ai-personalization/  Model methodologies, evaluation, and limitations
docs/final-report/        Submission-ready B.Tech report and live screenshots
docs/phase1-requirements/ Formal FR/NFR definitions and traceability
src/                      React frontend (the repository root is the Vite project)
```

## Local Setup

Prerequisites: Node.js 20+, Python 3.11+, Docker Desktop, and Git.

### 1. PostgreSQL and Backend

```bash
cd backend
docker compose up -d postgres
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -e ".[test]"
copy .env.example .env                 # Windows
# cp .env.example .env                 # Linux/macOS

alembic upgrade head                   # applies revisions 0001 through 0007
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Docker Compose exposes PostgreSQL on host port `5433`. The development configuration uses:

```text
DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5433/optivest
```

Replace the development JWT secret outside local use. The API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Frontend

From the repository root:

```bash
npm install

# Optional .env.local override:
# VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1

npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## Real Kaggle Data Ingestion

Download `kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals` and place both CSV files under `data/raw/`:

```bash
kaggle datasets download \
  -d kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals \
  -p data/raw --unzip

cd backend
python -m app.etl.load_nifty_dataset ../data/raw/nifty50_historical_data.csv
```

The ETL uses natural-key upserts, so rerunning it is idempotent. It accepts 287,263 dated rows and consistently rejects the documented 47 zero-OHLC source rows. See the [data profile](data/PROFILE_REPORT.md) for headers, mappings, nulls, date coverage, units, and manual return checks.

## Tests and Coverage

```bash
cd backend
pytest --cov=app --cov-report=term-missing --cov-report=html

# Include the three real-PostgreSQL integrations:
# Windows PowerShell
$env:REAL_DATABASE_URL="postgresql+asyncpg://optivest:optivest@localhost:5433/optivest"
# Linux/macOS
# export REAL_DATABASE_URL="postgresql+asyncpg://optivest:optivest@localhost:5433/optivest"

pytest --cov=app --cov-report=term-missing --cov-report=html

cd ..
npm run test:coverage
npm run build
```

The verified baseline is 225 backend passes plus three environment-gated tests by default; all three pass against the loaded PostgreSQL database. The final database-enabled run passed 228/228 with 90.31% combined backend coverage. Frontend verification is 47/47 tests with 83.00% statement, 70.75% branch, 71.30% function, and 96.00% line coverage.

On Windows, WeasyPrint 66 requires a modern Pango runtime. The application automatically registers `C:\msys64\mingw64\bin` when that runtime is installed.

## Final Report Conversion

With Pandoc, XeLaTeX, and `mermaid-filter` installed:

```bash
pandoc docs/final-report/0*.md \
  --from=gfm+tex_math_dollars --toc --number-sections \
  --resource-path=docs/final-report --filter mermaid-filter \
  --pdf-engine=xelatex -o OptiVest-Final-Report.pdf
```

Use `.docx` as the output and omit `--pdf-engine` for an editable Word submission.

## Methodology Integrity

The original Phase 9B walkthrough replayed the same 249 dates used to fit the optimizer and reported fitted quantities as validation evidence. Phase 9C identified this look-ahead bias and enforced an exclusive split: 252 observations ending 29 January 2025 for estimation, followed by 249 observations from 30 January 2025 through 30 January 2026 for evaluation, with zero shared dates.

The established corrected static portfolio changed ₹10,00,000 to ₹11,01,423.96, with 10.3141% annualized realized return and 0.6777 realized Sharpe. The separate 13-period historical-mean walk-forward experiment ended at ₹10,11,596.09 with 1.1737% return, 0.0771 Sharpe, −12.0030% drawdown, and 8.0000 turnover. Transaction costs are not modeled. These results are reported as observed outcomes, not tuned demonstrations of superiority.
