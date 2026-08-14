# Results and Testing

## Fresh verification protocol

Results in this chapter were refreshed on 15 August 2026 after the additive walk-forward stretch phase. Backend coverage used `pytest --cov=app`; frontend coverage used `vitest run --coverage`. Targets from phase prompts are not substituted for achieved values.

On Windows, two PDF tests initially exposed an older GTK Pango DLL earlier in `PATH`. Re-running with the installed modern MSYS2 runtime (`C:\msys64\mingw64\bin`) produced the behavioral result below. This was an environment/library-symbol mismatch, not a hidden test deletion.

## Backend result

- Collected: 171 tests.
- Behavioral outcome: **168 passed, 3 skipped**.
- Combined statement+branch coverage: **89.09%** (coverage.py total).
- Statement coverage: **91.96%**.
- Branch coverage: **73.53%**.
- Configured project gate: **90% combined**; therefore the coverage command reports a failed threshold even though all non-gated tests pass.
- Warnings: 1,020 deprecation warnings from PuLP 3.x compatibility paths; they are technical debt, not assertion failures.

### Package coverage achieved

The `Cover` column below combines statements and branches, matching coverage.py's displayed package calculation.

| Backend package | Statements covered | Combined coverage |
|---|---:|---:|
| `analytics` | 92.54% | 88.27% |
| `api` | 96.48% | 96.53% |
| `core` | 94.64% | 89.68% |
| `db` | 96.90% | 96.90% |
| `etl` | 85.09% | 82.99% |
| `explainability` | 95.68% | 94.32% |
| `optimization` | 97.22% | 95.47% |
| `reports` | 95.87% | 92.96% |
| `scenarios` | 95.35% | 92.43% |
| `schemas` | 85.96% | 85.31% |
| `services` | 78.50% | 72.25% |

The global target is missed mainly by orchestration error branches in services, schema-only modules and ETL CLI/error paths. This is explicitly future test work.

### Why three tests are skipped

1. `test_one_year_five_stock_backtest_uses_real_postgres_data` is skipped unless `REAL_DATABASE_URL` is set, preventing a normal unit run from depending on a developer's database.
2. `test_real_49_stock_optimization_through_http_api` has the same gate because it creates an authenticated user and exercises the loaded 49-stock database.
3. `test_real_49_stock_walk_forward_matches_phase9c_period` performs 13 rolling fits/solves and persistence against the loaded universe.

After Docker/PostgreSQL was started and `REAL_DATABASE_URL=postgresql+asyncpg://optivest:optivest@localhost:5433/optivest` was provided, all three integration checks passed. The default skips therefore mean environment-gated, not broken or unimplemented.

## Frontend result

The stretch-phase frontend result is **35/35 passed across four test files**. The new walk-forward tab has dedicated loading, success/chart, and error-state coverage.

| Frontend page scope | Statements | Branches | Functions | Lines |
|---|---:|---:|---:|---:|
| All included pages | 84.32% | 69.07% | 74.00% | 96.42% |
| Analytics page | 85.29% | 68.75% | 75.00% | 94.73% |
| Walk-forward tab | 89.83% | 75.00% | 83.33% | 100% |
| Authentication | 84.21% | 56.25% | 66.66% | 88.23% |
| Dashboard | 94.44% | 61.11% | 85.71% | 100% |
| Portfolio Builder | 71.79% | 70.83% | 53.84% | 100% |
| Portfolio Details | 82.14% | 63.63% | 66.66% | 100% |
| Reports | 88.88% | 68.75% | 81.81% | 100% |
| Scenario Simulator | 74.07% | 79.16% | 58.33% | 100% |
| Settings | 94.11% | 71.42% | 83.33% | 100% |

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
