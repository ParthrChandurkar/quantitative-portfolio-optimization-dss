# OptiVest Portfolio Optimization

OptiVest is an academic decision-support application for constructing, comparing, and explaining investment portfolios. It combines mathematical optimization, historical market data, scenario analysis, model-assisted personalization, and report generation behind a React and FastAPI interface.

OptiVest does not execute trades and does not provide investment advice.

## Features

- Portfolio construction with continuous and cardinality-constrained solvers
- Risk questionnaire and model-assisted preference defaults
- Efficient-frontier and portfolio analytics
- Scenario shocks and portfolio re-optimization
- Historical out-of-sample evaluation
- Return forecasting, anomaly detection, and grounded assistant intents
- Ownership-aware resources and JWT authentication
- PDF report generation

## Architecture

The React client calls a FastAPI API under `backend/`. The backend separates optimization, explainability, scenarios, analytics, reporting, machine learning, personalization, assistant, and alert services. SQLAlchemy models persist market data, users, portfolios, model metadata, scenarios, and reports in PostgreSQL. Alembic manages schema revisions.

See [`docs/diagrams/README.md`](docs/diagrams/README.md) for the architecture diagrams and regeneration notes, and [`docs/methodology-notes.md`](docs/methodology-notes.md) for methodological constraints.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, React Router, React Query |
| API | Python 3.11+, FastAPI, Pydantic |
| Data | PostgreSQL, SQLAlchemy, Alembic, asyncpg |
| Optimization | SciPy SLSQP, PuLP/CBC, OR-Tools CP-SAT |
| Machine learning | scikit-learn |
| Authentication | JWT access and refresh tokens, Argon2 |
| Reports | Jinja2 and WeasyPrint |
| Testing | pytest, Vitest, Testing Library |

## Getting Started

Prerequisites: Node.js 20 or newer, Python 3.11 or newer, Docker, and Git.

Start PostgreSQL and the backend:

```powershell
Set-Location backend
docker compose up -d postgres
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Copy-Item .env.example .env
alembic upgrade head
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The development database is exposed on port `5433`. Replace the example JWT secret before using a shared environment.

Start the frontend from the repository root:

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

The API documentation is available at `http://127.0.0.1:8000/docs` and the frontend at `http://127.0.0.1:5173`.

## Data

The raw market dataset is not committed. Follow [`data/README.md`](data/README.md) for acquisition, expected schema, ingestion, and reconciliation guidance. Do not present row counts or model performance as current unless they are regenerated from the checked-out data and environment.

## Testing

Backend:

```bash
cd backend
pytest
```

Database-gated integration tests require `REAL_DATABASE_URL` pointing to a disposable or development PostgreSQL database.

Frontend:

```bash
npm run test:coverage
npm run build
```

## Limitations

- Results depend on historical inputs and modelling assumptions; they do not predict future returns.
- The repository requires a separately acquired dataset for full ingestion and analysis.
- Optimization feasibility depends on the chosen constraints and available assets.
- Windows PDF generation with WeasyPrint may require an installed Pango runtime.

