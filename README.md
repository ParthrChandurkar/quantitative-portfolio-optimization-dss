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

Open `http://localhost:5173`.

## Validate

```bash
npm run lint
npm run build
```

## Stack

React 19, TypeScript, Vite, Lucide icons, and a custom responsive design system. The current repository is a frontend product prototype with seeded Nifty-style market data; the architecture is ready for a FastAPI/PostgreSQL optimization service.
