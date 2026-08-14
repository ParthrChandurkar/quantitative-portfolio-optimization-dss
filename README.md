# OptiVest

OptiVest is a quantitative portfolio decision-support system for Indian equities. It turns investor goals and real-world constraints into an explainable allocation, then lets users stress-test the result before acting.

## Product loop

**Model → Solve → Explain → Simulate**

- Configure capital, risk appetite, sector caps, and diversification limits.
- Generate an optimized Nifty 50 allocation with a deterministic constrained solver.
- Inspect why every holding was selected and which constraints are binding.
- Simulate market shocks and compare projected drawdown and recovery.
- Export an investment committee-ready report.

## Run locally

```bash
npm install
npm run dev
```

In a second terminal, configure `backend/.env`, apply migrations, and run the API:

```bash
cd backend
alembic upgrade head
uvicorn main:app --reload
```

Open `http://localhost:5173`. The frontend defaults to
`http://localhost:8000/api/v1`; override it with `VITE_API_BASE_URL` when needed.

## Validate

```bash
npm run lint
npm run build
npm run test:coverage
```

## Stack

React 19, TypeScript, Vite, React Query, React Router, FastAPI, PostgreSQL,
SQLAlchemy, SciPy, PuLP, OR-Tools, and WeasyPrint. Financial data is loaded from the
profiled Nifty-50 dataset; page components contain no seeded portfolio or metric data.
