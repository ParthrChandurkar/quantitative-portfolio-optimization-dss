# OptiVest

OptiVest is an explainable decision-support system for constrained Nifty-50 portfolio optimization. It combines real daily market data, SciPy/PuLP/OR-Tools models, scenario re-solving, out-of-sample analytics, and audit-ready PDF reports in one authenticated web application. All monetary values are Indian rupees (INR).

> Academic decision support only. OptiVest does not execute trades and is not personalized investment advice.

![OptiVest analytics](docs/final-report/screenshots/05-analytics-out-of-sample.png)

## What is implemented

- PostgreSQL storage for 49 stocks and 287,263 dated price, fundamental, and technical rows; the ETL is idempotent and rejects the documented 47 zero-OHLC source rows.
- Continuous mean-variance QP with SciPy, cardinality-constrained mean absolute deviation with PuLP/CBC, and CP-SAT support selection with OR-Tools.
- Stable constraint checks, binding-constraint logs, marginal contributions, deterministic explanations, seven re-solved scenario families, historical analytics, and generated PDFs.
- JWT access/refresh authentication, ownership checks, React Query server state, and a structurally enforced out-of-sample split.

## Technology stack

| Layer | Technology |
|---|---|
| Web | React 19, TypeScript 5.9, Vite, React Router, React Query |
| API | Python 3.11+, FastAPI, Pydantic, JWT, Argon2 |
| Data | PostgreSQL 16, SQLAlchemy 2 async ORM, Alembic, asyncpg |
| OR and analytics | NumPy, SciPy SLSQP, PuLP/CBC, OR-Tools CP-SAT |
| Reports/tests | Jinja2, WeasyPrint, pytest, pytest-cov, Vitest, Testing Library |

## Repository layout

```text
backend/                  FastAPI, data, OR, analytics, reports, tests
data/raw/                 Local Kaggle CSVs (ignored because of size)
data/PROFILE_REPORT.md    Real-data reconciliation evidence
docs/final-report/        Final B.Tech report chapters and screenshots
docs/phase1-requirements/ Formal FR/NFR source documents
src/                      Deployable React frontend (repository-root Vite app)
```

The frontend lives at repository root rather than a separate `frontend/` directory; `src/` is the real Phase 3/9B application.

## Local setup

Prerequisites: Node.js 20+, Python 3.11+, Docker Desktop, and Git.

### Database and backend

```bash
cd backend
docker compose up -d postgres
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[test]"
copy .env.example .env                 # Windows
# cp .env.example .env                 # Linux/macOS
alembic upgrade head
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Compose exposes PostgreSQL on host port `5433`. Keep `DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5433/optivest` in `backend/.env` and replace the development JWT secret outside local use.

### Frontend

```bash
npm install
# Optional .env.local:
# VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## Real Kaggle data ingestion

Download `kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals` and place both CSVs in `data/raw/`. The dated historical file is loaded; the summary file remains an aggregate reference.

```bash
kaggle datasets download \
  -d kalyan197/nifty50-stocks1999-2026-daily-ohlcv-and-fundamentals \
  -p data/raw --unzip

cd backend
python -m app.etl.load_nifty_dataset ../data/raw/nifty50_historical_data.csv
```

Re-running performs natural-key upserts. The reconciled run produced 49 stocks and 287,263 rows in each dated table; see [the profile report](data/PROFILE_REPORT.md).

## Tests and achieved coverage

```bash
cd backend
pytest --cov=app --cov-report=term-missing --cov-report=html
# open backend/htmlcov/index.html

cd ..
npm test
npm run test:coverage
```

Set `REAL_DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5433/optivest` to include the two loaded-PostgreSQL integration tests. The 15 August 2026 fresh run produced 158 passed and 2 environment-gated skips, 88.56% combined backend coverage, and 32/32 frontend tests with 83.49% statement and 96.29% line coverage. The configured 90% backend global target is not yet met. On Windows, WeasyPrint 66 requires a modern Pango runtime; the application registers `C:\msys64\mingw64\bin` automatically when that runtime is installed.

## Final report and conversion

- [Final report chapters](docs/final-report/)
- [Methodology integrity notes](docs/methodology-notes.md)
- [Requirements](docs/phase1-requirements/)

With Pandoc, XeLaTeX, and `mermaid-filter` installed:

```bash
pandoc docs/final-report/0*.md \
  --from=gfm+tex_math_dollars --toc --number-sections \
  --resource-path=docs/final-report --filter mermaid-filter \
  --pdf-engine=xelatex -o OptiVest-Final-Report.pdf
```

Use `.docx` as the output and omit `--pdf-engine` for an editable Word submission.

## Build history

| Phase | Commit | Delivered capability |
|---|---|---|
| Foundation | `d443e94` | Initial repository |
| Phase 3 UI prototype | `26a4cfc` | Dashboard and page design |
| Phase 1 | `4287582` | Requirements and traceability |
| Phase 2 | `ca62e2a` | PostgreSQL schema and ETL |
| Phase 4 | `1184953` | Optimization engine |
| Phase 5 | `c7cfdb8` | Explainability layer |
| Dataset acquisition | `c3b65e2` | Raw-data provenance |
| Phase 6 | `dec020c` | Scenario simulator |
| Data checkpoint | `0037ac6` | Real profiling and full load |
| Phase 7 | `08b5601` | Analytics and real backtest |
| Phase 8 | `95d1ca0` | PDF generation |
| Phase 9 | `66cfb74` | Authenticated API and typed client |
| Phase 9B | `43a89a9` | All pages connected to live data |
| Phase 9C | `d5fea96` | Out-of-sample split and labels |

## Methodology warning

The Phase 9B replay reused all 249 evaluation dates during fitting. Phase 9C identified the look-ahead bias and enforced disjoint windows. The corrected portfolio changed ₹10,00,000 to ₹11,01,423.96 with 10.3141% annualized realized return and 0.6777 realized Sharpe. See [Methodology Integrity](docs/final-report/07-methodology-integrity.md).
