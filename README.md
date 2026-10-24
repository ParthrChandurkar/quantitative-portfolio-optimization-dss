# OptiVest — AI-Driven Portfolio Optimization

OptiVest is an academic investment decision-support system for building, stress-testing, explaining, and evaluating equity portfolios. It combines machine learning with constrained mathematical optimization and presents the results through a React dashboard backed by FastAPI and PostgreSQL.

> **Academic-use notice:** OptiVest does not execute trades or provide financial advice. All forecasts, scenarios, and historical results depend on the supplied data and modelling assumptions.

![OptiVest dashboard](docs/final-report/screenshots/01-dashboard.png)

## What OptiVest does

- Converts an investor questionnaire into visible, editable portfolio constraints.
- Estimates expected return and covariance from historical Nifty-50 data.
- Builds long-only portfolios with stock, sector, cardinality, budget, and diversification limits.
- Supports continuous QP, MILP, and hybrid optimization paths.
- Explains selected and excluded holdings using evidence from the solved portfolio.
- Applies parameterized market shocks and re-runs the optimizer to produce a feasible stressed portfolio.
- Tests performance on later unseen dates and supports repeated walk-forward evaluation.
- Generates portfolio analytics, alerts, grounded assistant answers, and downloadable PDF reports.

## System architecture

![OptiVest system architecture](docs/diagrams/system-architecture.svg)

The React client communicates with a versioned FastAPI service. The backend coordinates authentication, personalization, market-data access, optimization, scenarios, analytics, explainability, alerts, and reporting. PostgreSQL stores the market universe and every persisted decision artifact, while Alembic manages schema changes.

Detailed architecture assets and editable Mermaid sources are available in [`docs/diagrams`](docs/diagrams/README.md).

## Decision workflow

1. **Investor profiling** — questionnaire responses produce a model-assisted risk class and recommended limits.
2. **Constraint review** — the user can inspect and edit risk tolerance, maximum stock weight, and sector limits.
3. **Input estimation** — historical data produces expected returns and covariance; an optional ML forecast may replace the declared return vector.
4. **Optimization** — the OR engine solves the selected constrained portfolio formulation and records feasibility evidence.
5. **Explanation** — holdings, exclusions, diversification, and active limits are explained from persisted solve results.
6. **Stress testing** — scenario transformations modify return, covariance, or constraints before a complete re-solve.
7. **Temporal validation** — snapshot and walk-forward analytics test only on later dates and audit date separation.
8. **Delivery** — the dashboard, assistant, alerts, and PDF reports reuse the same stored evidence.

## AI, machine learning, and Operations Research

| Component | Technique | Role |
| --- | --- | --- |
| Risk personalization | Logistic Regression | Classifies questionnaire responses into investor risk profiles |
| Return forecasting | Gradient Boosting | Produces an optional expected-return estimate for optimization |
| Assistant routing | TF-IDF intent classifier | Routes portfolio questions to grounded, deterministic answer services |
| Portfolio alerts | Isolation Forest | Flags unusual portfolio-risk observations |
| Portfolio construction | SciPy SLSQP, PuLP/CBC, OR-Tools CP-SAT | Enforces constraints and calculates feasible allocations |

Machine learning supplies declared inputs or classifications; it does not bypass the optimization engine. The final allocation remains controlled by explicit mathematical constraints and solver feasibility checks.

## Product views

| Portfolio construction | Explainable holdings |
| --- | --- |
| ![Portfolio Builder](docs/final-report/screenshots/02-portfolio-builder.png) | ![Portfolio explanations](docs/final-report/screenshots/03-portfolio-details-why.png) |

| Scenario re-optimization | Out-of-sample analytics |
| --- | --- |
| ![Scenario comparison](docs/final-report/screenshots/04-scenario-comparison.png) | ![Out-of-sample analytics](docs/final-report/screenshots/05-analytics-out-of-sample.png) |

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, React Router, TanStack Query, Lucide React |
| API | Python 3.11+, FastAPI, Pydantic, Uvicorn |
| Data | PostgreSQL 16, SQLAlchemy, Alembic, asyncpg |
| Optimization | SciPy SLSQP, PuLP/CBC, OR-Tools CP-SAT |
| Machine learning | scikit-learn, NumPy, joblib |
| Authentication | JWT access/refresh tokens and Argon2 password hashing |
| Reporting | Jinja2 and WeasyPrint |
| Testing | pytest, Hypothesis, Vitest, Testing Library, coverage.py |

## Repository structure

```text
OR-OptiVest/
├── backend/                  FastAPI application, migrations, models, and tests
├── data/                     Dataset acquisition and reconciliation guidance
├── docs/
│   ├── diagrams/             Architecture SVGs and Mermaid sources
│   ├── final-report/         Report chapters and verified screenshots
│   └── presentation/         Slide-ready PNG/SVG visuals and generator
├── notebooks/                Supporting analytical notebooks
├── src/                      React application and frontend tests
└── README.md                 Project overview and setup guide
```

## Getting started

### Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer
- Docker Desktop
- Git

### 1. Start PostgreSQL

```powershell
Set-Location backend
docker compose up -d postgres
```

The development database is exposed on `127.0.0.1:5433`.

### 2. Configure and run the API

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Copy-Item .env.example .env

$env:DATABASE_URL = "postgresql+asyncpg://optivest:optivest@127.0.0.1:5433/optivest"
python -m alembic upgrade head
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Replace the example JWT secret in `backend/.env` before using a shared or deployed environment.

### 3. Run the frontend

From the repository root in another terminal:

```powershell
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

- Application: `http://127.0.0.1:5173`
- API documentation: `http://127.0.0.1:8000/docs`

If port `8000` is already in use, run the API on another port and create an untracked `.env.local` file containing, for example:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1
```

## Dataset

The project uses the Kaggle dataset **Nifty-50 Stocks: 1999–2026 Daily OHLCV and Fundamentals**. Raw market files are intentionally excluded from Git. The checked project notes document 49 available stocks, 287,263 validated historical rows, and 47 rejected zero-OHLC records.

See [`data/README.md`](data/README.md) for the source identifier, expected checksums, schema, ingestion procedure, and reconciliation results. Do not present row counts or model performance as current unless they have been regenerated from the checked-out data and environment.

## Testing and quality checks

Backend:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
npm test
npm run lint
npm run build
```

Database-gated integration tests require `REAL_DATABASE_URL` pointing to a disposable or development PostgreSQL database.

## Documentation and visual assets

- [Documentation hub](docs/README.md)
- [Final report](docs/final-report/README.md)
- [System diagrams](docs/diagrams/README.md)
- [Presentation visuals](docs/presentation/README.md)
- [Methodology and integrity notes](docs/methodology-notes.md)
- [Research gap and novelty](docs/phase1-requirements/research-gap-and-novelty.md)

## Methodological safeguards

- Training and evaluation dates are kept separate for out-of-sample analysis.
- Walk-forward estimation uses only data available before each rebalance.
- Scenario results come from a new optimizer call, not simple portfolio-value scaling.
- Explanations and assistant answers are grounded in persisted optimization evidence.
- User-visible constraints remain editable; model outputs are recommendations, not hidden rules.

## Limitations

- Historical and forecast results do not guarantee future investment performance.
- Full ingestion and real-data analysis require the separately acquired Kaggle dataset.
- Optimization feasibility depends on the chosen limits and available stock universe.
- Transaction costs, taxes, slippage, and live order execution are outside the current scope.
- PDF generation on Windows may require a compatible Pango runtime for WeasyPrint.

## License and responsible use

No standalone software license is currently included in this repository. Treat the project as academic work unless the repository owner specifies otherwise. Dataset usage remains subject to its source license and terms.
