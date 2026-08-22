# AI-Driven Personalized Investment Planning and Portfolio Optimization

**OptiVest** is an institutional-style decision-support system for constructing personalized Nifty portfolios. It combines a real Operations Research engine—continuous and mixed-integer constrained optimization—with an additive AI layer for market-return forecasting, investor risk profiling, grounded portfolio Q&A, and personalized alerts.

![Backend tests](https://img.shields.io/badge/backend_tests-228_passing-brightgreen) ![Backend coverage](https://img.shields.io/badge/backend_coverage-90.31%25-brightgreen) ![Frontend tests](https://img.shields.io/badge/frontend_tests-47_passing-brightgreen) ![Frontend coverage](https://img.shields.io/badge/frontend_statements-83.00%25-brightgreen) ![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white) ![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)

## 📊 Quick Facts

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

## 🏛️ System Architecture

![OptiVest system architecture](docs/diagrams/system-architecture.svg)

The rendered architecture follows the real repository boundaries: the React client calls ownership-aware FastAPI services, the completed OR core and additive AI layer remain visibly separated, and both operate on the same audited PostgreSQL foundation. See the [diagram sources and regeneration commands](docs/diagrams/README.md).

## 🔄 How It Works

![OptiVest optimize request flow](docs/diagrams/optimize-request-flow.svg)

A successful optimization request builds real market inputs, runs the selected solver, generates explanations, and commits the complete snapshot before returning it. The alert check is deliberately dashed because it executes as a post-response background task and does not delay the user-facing solve result.

## 🎯 Overview

This is not a tutorial or fixture-only demonstration. The running system uses PostgreSQL data loaded from 287,310 real market rows, solves and explains portfolios over a 49-stock universe, re-solves explicit stress scenarios, validates performance on dates excluded from estimation, and generates auditable PDF reports. During development, a look-ahead-biased backtest was detected, documented, and replaced with a structurally disjoint out-of-sample evaluation.

> Academic decision support only. OptiVest does not execute trades and is not personalized investment advice. All monetary values are Indian rupees (INR).

## 🧮 Operations Research Core

- **Continuous mean-variance optimization:** SciPy SLSQP solves the constrained quadratic program, enforcing a fully invested long-only portfolio while minimizing covariance-based risk or meeting the selected return/risk objective.
- **Cardinality-constrained MILP:** PuLP with the CBC solver uses binary holding decisions and mean absolute deviation risk so minimum and maximum holding counts can be modeled explicitly.
- **Hybrid CP-SAT optimization:** OR-Tools CP-SAT selects the discrete stock support, after which continuous optimization assigns feasible weights to the selected assets.
- **Realistic investment constraints:** the model applies the budget identity, per-stock weight limits, sector caps, risk/return targets, cardinality, and minimum-lot feasibility in rupee terms.
- **Auditable decision support:** independent feasibility checks, binding-constraint logs, marginal return/risk contributions, and deterministic “Why?” narratives explain why each asset was selected or limited.
- **Seven stress scenarios:** market crash, rate increase, inflation, sector crash, budget increase, budget reduction, and risk-profile change transform `mu`, covariance, budget, or constraints before a complete re-solve.
- **Validation and trade-off analysis:** a 30-point feasible efficient frontier, buy-and-hold and periodic backtests, strict out-of-sample splits, and monthly walk-forward re-estimation use real PostgreSQL prices.

## 🤖 AI / Personalization Layer

- **ML return forecasting:** a `GradientBoostingRegressor` uses 12 trailing market features to predict forward 21-trading-day adjusted-close returns; `ml_forecast` is optional and historical mean remains the unchanged default.
- **ML risk profiling:** multinomial Logistic Regression, selected against a Random Forest baseline, maps six questionnaire answers to conservative, moderate, or aggressive profiles and recommends visible, editable OR defaults.
- **Grounded NLP assistant:** TF-IDF unigram/bigram features plus multinomial Logistic Regression route seven intents at a `0.55` confidence threshold; answers come only from stored explanations, analytics, allocations, and real scenario re-solves—no external LLM is used.
- **Personalized risk alerts:** explicit profile-drift thresholds and per-stock 200-tree Isolation Forest models (`contamination=0.02`) evaluate 12 anomaly features and create deduplicated, numerically grounded notifications in the background.
- **Evidence-first evaluation:** the ML forecast underperformed historical mean on the recorded OOS period, while synthetic-label and rubric-replication caveats for risk and intent classification remain explicit in the report.

## ✅ Verified Product Evidence

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

## 🏗️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 19, TypeScript 5.9, Vite, React Router, React Query | Typed user interface, routing, live server state, and interactive portfolio workflows |
| Backend API | Python 3.11+, FastAPI, Pydantic | Async API endpoints, request validation, and service orchestration |
| Database | PostgreSQL 16, SQLAlchemy 2 async ORM, Alembic, asyncpg | Durable market, portfolio, model, analytics, alert, and report data with versioned migrations |
| OR solvers | SciPy SLSQP, PuLP/CBC, OR-Tools CP-SAT | Continuous QP, cardinality-constrained MILP, and hybrid discrete support selection |
| ML/AI stack | scikit-learn Gradient Boosting, Logistic Regression, TF-IDF, Isolation Forest | Return forecasts, risk personalization, grounded intent routing, and anomaly detection |
| Authentication | JWT access/refresh tokens, Argon2 | Password hashing, authenticated sessions, and ownership-protected resources |
| PDF generation | Jinja2, WeasyPrint | Template-driven portfolio, analytics, and scenario reports |
| Testing | pytest, pytest-cov, Vitest, Testing Library | Backend integration/unit verification and frontend loading/success/error coverage |

## 📁 Project Structure

The frontend lives at the repository root as a Vite project; the backend is isolated under `backend/`.

```text
OptiVest/
├── src/                              React/TypeScript frontend
│   ├── pages/                        Live API-backed product screens
│   ├── components/                   Shared UI and state components
│   └── lib/api/                      Typed backend client
├── backend/
│   ├── app/
│   │   ├── api/                      FastAPI routes and schemas
│   │   ├── db/                       Async ORM models and sessions
│   │   ├── optimization/             SciPy, PuLP, and OR-Tools engines
│   │   ├── explainability/           Decision reasons and narratives
│   │   ├── scenarios/                Shock transforms and scenario re-solves
│   │   ├── analytics/                Backtests, frontier, and risk metrics
│   │   ├── reports/                  Jinja2/WeasyPrint PDF generation
│   │   ├── ml/                       Return forecasting and anomaly models
│   │   ├── personalization/          Risk-profile classifier and defaults
│   │   ├── assistant/                Grounded NLP intent service
│   │   └── alerts/                   Personalized drift/anomaly alerts
│   ├── alembic/                      Seven database migrations
│   └── tests/                        Backend unit and integration tests
├── data/
│   ├── raw/                          Local Kaggle CSVs (gitignored)
│   └── PROFILE_REPORT.md             Real-data reconciliation evidence
└── docs/
    ├── phase1-requirements/          Formal FR/NFR definitions
    ├── ai-personalization/           AI methods, results, and limitations
    └── final-report/                 Submission-ready B.Tech report
```

## 🗓️ Project Timeline

| Build stage | Verified increment | Report reference |
|---|---|---|
| Phase 1 | Problem analysis, FR/NFR definitions, comparison, novelty, and traceability | [Introduction](docs/final-report/01-introduction.md) |
| Phase 2 | PostgreSQL schema, SQLAlchemy models, Alembic migrations, and idempotent ETL | [System design](docs/final-report/02-system-design.md) |
| Phase 3 | React/TypeScript interface and the principal OptiVest workflows | [UI/UX](docs/final-report/03-ui-ux.md) |
| Phase 4 | Continuous QP, MAD MILP, CP-SAT support selection, constraints, and feasibility checks | [Optimization methodology](docs/final-report/04-optimization-methodology.md) |
| Phase 5 | Binding constraints, contribution metrics, reason taxonomy, and deterministic narratives | [Decision support](docs/final-report/05-decision-support.md) |
| Phase 6 | Seven parameterized scenario transforms followed by full optimization re-solves | [Decision support](docs/final-report/05-decision-support.md) |
| Phase 7 | Growth, real-price backtests, risk metrics, sector analysis, and efficient frontier | [Results and testing](docs/final-report/06-results-and-testing.md) |
| Phase 8 | Three auditable PDF report types with academic disclaimers | [UI/UX and reports](docs/final-report/03-ui-ux.md) |
| Phase 9 | JWT auth, API/service wiring, real frontend integration, and OOS correction | [System design](docs/final-report/02-system-design.md) |
| Phase 10 | Final report assembly, live evidence, methodology disclosure, and fresh verification | [Complete final report](docs/final-report/) |
| AI Phase 1 | Optional Gradient Boosting return forecast integrated without changing the OR default | [AI personalization layer](docs/final-report/09-ai-personalization-layer.md) |
| AI Phase 2 | Logistic Regression risk classification and editable personalized defaults | [AI personalization layer](docs/final-report/09-ai-personalization-layer.md) |
| AI Phase 3 | Grounded seven-intent portfolio assistant with real service calls | [AI personalization layer](docs/final-report/09-ai-personalization-layer.md) |
| AI Phase 4 | Profile-drift and Isolation Forest anomaly alerts with background execution | [AI personalization layer](docs/final-report/09-ai-personalization-layer.md) |
| Methodology correction | Phase 9C removed estimation/evaluation overlap and permanently labeled OOS results | [Methodology integrity](docs/final-report/07-methodology-integrity.md) |
| Walk-forward validation | Monthly re-estimation, turnover reporting, and a 13-period sanity breakdown | [Methodology notes](docs/methodology-notes.md) |

## 📚 Documentation

- [Phase requirements and implementation traceability](docs/phase1-requirements/traceability-matrix.md)
- [Complete final project report](docs/final-report/)
- [AI personalization methodologies, evaluations, and limitations](docs/ai-personalization/)
- [Methodology notes: look-ahead-bias correction and walk-forward findings](docs/methodology-notes.md) — the most important document for understanding the project’s research rigor, including mistakes found and corrected.

## 🚀 Getting Started

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

## 🗃️ Real Kaggle Data Ingestion

Download `kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals` and place both CSV files under `data/raw/`:

```bash
kaggle datasets download \
  -d kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals \
  -p data/raw --unzip

cd backend
python -m app.etl.load_nifty_dataset ../data/raw/nifty50_historical_data.csv
```

The ETL uses natural-key upserts, so rerunning it is idempotent. It accepts 287,263 dated rows and consistently rejects the documented 47 zero-OHLC source rows. See the [data profile](data/PROFILE_REPORT.md) for headers, mappings, nulls, date coverage, units, and manual return checks.

## 🧪 Testing & Coverage

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

## 📄 Final Report Conversion

With Pandoc, XeLaTeX, and `mermaid-filter` installed:

```bash
pandoc docs/final-report/0*.md \
  --from=gfm+tex_math_dollars --toc --number-sections \
  --resource-path=docs/final-report --filter mermaid-filter \
  --pdf-engine=xelatex -o OptiVest-Final-Report.pdf
```

Use `.docx` as the output and omit `--pdf-engine` for an editable Word submission.

## 🔬 Methodology & Integrity

The original Phase 9B walkthrough replayed the same 249 dates used to fit the optimizer and reported fitted quantities as validation evidence. Phase 9C identified this look-ahead bias and enforced an exclusive split: 252 observations ending 29 January 2025 for estimation, followed by 249 observations from 30 January 2025 through 30 January 2026 for evaluation, with zero shared dates.

The established corrected static portfolio changed ₹10,00,000 to ₹11,01,423.96, with 10.3141% annualized realized return and 0.6777 realized Sharpe. The separate 13-period historical-mean walk-forward experiment ended at ₹10,11,596.09 with 1.1737% return, 0.0771 Sharpe, −12.0030% drawdown, and 8.0000 turnover. Transaction costs are not modeled. These results are reported as observed outcomes, not tuned demonstrations of superiority.
