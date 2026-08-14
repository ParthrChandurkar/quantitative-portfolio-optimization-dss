# Phase 9B Frontend Integration Verification

The deployable frontend remains at repository-root `src/` because the Vite project was
created at the repository root in Phase 3. It is now split into `src/pages/` modules.
The former `src/data.ts` fixture module has been removed.

## Page reconciliation

| Page | Live client operations |
|---|---|
| Dashboard | `GET /portfolios` |
| Portfolio Builder | `GET/POST /portfolios`, `POST /portfolios/{id}/optimize`, status polling |
| Portfolio Details | `GET /portfolios/{id}` with persisted holdings and explanations |
| Scenario Simulator | `GET /portfolios`, `POST /portfolios/{id}/scenarios` |
| Analytics | `GET /portfolios/{id}/snapshots/{sid}/analytics` |
| Reports | `POST .../reports`, `GET /reports`, binary report download |
| Settings/Profile | `GET /me`, `PATCH /me` |

Every query page uses the shared React Query client context and the same loading and
error components. A 401 redirects to the authentication route; 403, server, and
network errors receive consistent messages.

## Fixture removal proof

`src/data.ts` was deleted. A search of `src/pages`, `src/components`, and `src/App.tsx`
finds no imports from a fixture/data module and no hardcoded portfolio, holding, stock,
curve, benchmark, or metrics arrays. Static arrays that remain are UI-only navigation,
report-template choices, and a color palette; all financial values are API responses.

## Live walkthrough result

> **Phase 9C correction:** this walkthrough replayed 249 dates that were also used to
> fit the optimizer, so the ₹1,507,469.92 result below is in-sample and must not be
> cited as validation performance. See [methodology-notes.md](methodology-notes.md) for
> the corrected disjoint-window result.

On 2026-08-14, the complete API workflow ran against PostgreSQL and the 49-stock loaded
universe. A ₹1,000,000 SciPy optimization solved in 146 ms with six holdings, 43.0367%
model expected return, 16.5110% volatility, 2.6065 Sharpe ratio, and 76.5 diversification
score. A 20% market-crash re-solve produced 30.0604% expected return, 17.2461%
volatility, and 1.7430 Sharpe ratio. The 249-point periodic-rebalance backtest changed
₹1,000,000 to ₹1,507,469.92, with 16.5310% realized volatility and -9.1470% maximum
drawdown. The generated Portfolio Summary was a valid 17,586-byte PDF.

The in-app browser-control surface was unavailable during this run, so these values are
verified from the same live HTTP endpoints used by the frontend plus frontend render and
mutation tests; they are not claimed as a visual browser click-through.
