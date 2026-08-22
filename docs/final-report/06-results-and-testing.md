# Results and Testing

*Project: AI-Driven Personalized Investment Planning and Portfolio Optimization (OptiVest)*

## Fresh verification protocol

Results in this chapter were refreshed on 22 August 2026 after AI finalization. Backend coverage used `pytest --cov=app`; frontend coverage used `vitest run --coverage`. Targets from phase prompts are not substituted for achieved values.

On Windows, two PDF tests initially exposed an older GTK Pango DLL earlier in `PATH`. Re-running with the installed modern MSYS2 runtime (`C:\msys64\mingw64\bin`) produced the behavioral result below. This was an environment/library-symbol mismatch, not a hidden test deletion.

## Backend result

- Collected: 228 tests.
- Default behavioral outcome: **225 passed, 3 skipped**.
- Real-PostgreSQL follow-up: **3/3 gated integration tests passed**, so the database-enabled behavioral total is **228/228 passed**.
- Combined statement+branch coverage: **90.05%** (coverage.py total).
- Statement coverage: **92.94%**.
- Branch coverage: **74.15%**.
- Configured project gate: **90% combined; passed**.
- Warnings: 1,108, dominated by PuLP 3.x deprecation paths; they are technical debt, not assertion failures.

### Package coverage achieved

The `Cover` column below combines statements and branches, matching coverage.py's displayed package calculation.

| Backend package | Statements covered | Combined coverage |
|---|---:|---:|
| `alerts` | 94.59% | 91.40% |
| `analytics` | 92.55% | 88.28% |
| `api` | 95.37% | 94.30% |
| `assistant` | 93.88% | 90.29% |
| `core` | 94.64% | 89.68% |
| `db` | 100.00% | 100.00% |
| `etl` | 85.09% | 82.99% |
| `explainability` | 95.68% | 94.32% |
| `ml` | 96.98% | 94.69% |
| `optimization` | 96.75% | 94.75% |
| `personalization` | 94.39% | 92.08% |
| `reports` | 95.87% | 92.96% |
| `scenarios` | 95.35% | 92.43% |
| `schemas` | 89.74% | 89.17% |
| `services` | 78.50% | 72.25% |

The global gate now passes. The weakest remaining area is orchestration/error branching in `services`; coverage does not replace the separate financial-methodology checks.

### Why three tests are skipped

1. `test_one_year_five_stock_backtest_uses_real_postgres_data` is skipped unless `REAL_DATABASE_URL` is set, preventing a normal unit run from depending on a developer's database.
2. `test_real_49_stock_optimization_through_http_api` has the same gate because it creates an authenticated user and exercises the loaded 49-stock database.
3. `test_real_49_stock_walk_forward_matches_phase9c_period` performs 13 rolling fits/solves and persistence against the loaded universe.

After Docker/PostgreSQL was started and `REAL_DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5433/optivest` was provided, all three integration checks passed. The default skips therefore mean environment-gated, not broken or unimplemented.

## Frontend result

The AI-finalization frontend result is **47/47 passed across seven test files**. The onboarding, grounded assistant, notification alerts, walk-forward tab, and original integrated pages are included.

| Frontend page scope | Statements | Branches | Functions | Lines |
|---|---:|---:|---:|---:|
| All included pages/components | 83.00% | 70.75% | 71.30% | 96.00% |
| Analytics page | 85.29% | 68.75% | 75.00% | 94.73% |
| Walk-forward tab | 89.83% | 75.00% | 83.33% | 100% |
| Authentication | 80.00% | 56.25% | 66.66% | 84.21% |
| Dashboard | 94.44% | 61.11% | 85.71% | 100% |
| Portfolio Builder | 69.56% | 75.00% | 43.75% | 100% |
| Portfolio Details | 81.48% | 63.63% | 66.66% | 95.00% |
| Reports | 88.88% | 68.75% | 81.81% | 100% |
| Scenario Simulator | 74.07% | 79.16% | 58.33% | 100% |
| Settings | 94.11% | 71.42% | 83.33% | 100% |
| Risk onboarding | 80.00% | 90.00% | 66.66% | 100% |

The configured frontend minimum is 60% for statements, branches, functions and lines; all four current aggregates exceed it. The production TypeScript/Vite build also succeeds.

## Real-data and product results

| Evidence | Actual result |
|---|---|
| Raw history profile | 287,310 rows, 25 columns, 49 symbols |
| Accepted/upserted | 287,263 dated rows per prices/fundamentals/technical table |
| Rejected | 47 zero-OHLC rows, consistently rejected on rerun |
| Idempotency | Same row counts after the second full-volume load |
| Real equal-weight integration backtest | ₹10,00,000 → ₹9,93,348.58 over 2025 |
| Corrected optimized OOS backtest | ₹10,00,000 → ₹11,01,423.96 over 249 observations |
| OOS realized metrics | 10.3141% return, 15.2203% volatility, 0.6777 Sharpe, -13.2597% drawdown |
| Monthly walk-forward OOS | ₹10,00,000 → ₹10,11,596.09; 1.1737% return, 0.0771 Sharpe, -12.0030% drawdown, 8.0000 turnover |
| Scenario | 20% crash re-solved to 30.06% return, 17.25% volatility, 1.74 Sharpe |
| Efficient frontier | 30 feasible fit-period points |
| PDF | Valid two-page, 20,388-byte portfolio summary |

## Test scope

The suite covers ORM constraints, natural-key ETL upserts/daily return, continuous and mixed-integer feasibility, dispatch/statuses, explanation predicates/templates, all seven shock transforms, scenario comparison, hand-calculated backtests, structural OOS disjointness at every walk-forward rebalance, changing rolling compositions, risk formulas, frontier feasibility, authenticated ownership, route envelopes, page loading/success/errors, mutation flows, PDF templates/storage/download and native browser-fetch invocation.

Coverage is evidence of exercised code, not proof of financial validity. Phase 9C's temporal audit supplies the separate methodology check.
