# Methodology Integrity: Look-Ahead Bias Audit

## Why this audit matters

A backtest is invalid as validation when the optimizer uses returns from the same dates on which its chosen weights are evaluated. The resulting replay answers “how did a portfolio selected with future knowledge fit that history?” rather than “how did a portfolio selected at the time perform afterward?”

Phase 9C examined exact cached/aligned dates instead of assuming a 252-row lookback and a one-year chart were separate.

## Finding

The Phase 9B covariance cache `09282fd9-3226-4d19-b950-b46398dd3b02` had `as_of_date=2026-01-30`, lookback 252, and aligned observations from 27 January 2025 through 30 January 2026. The displayed backtest contained 249 observations from 30 January 2025 through 30 January 2026.

Their intersection was all 249 evaluation dates. Zero evaluation observations were unseen during fitting. The ₹15,07,469.92 ending wealth was therefore an in-sample replay, not out-of-sample evidence.

## Implemented correction

`estimation_end_date` is now a split boundary:

```mermaid
flowchart LR
    A[Prices strictly before split] --> B[Estimate mu and Sigma]
    B --> C[Re-solve configured problem]
    C --> D[Fixed fitted weights]
    D --> E[Evaluate dates on/after split]
    A -. set intersection must be empty .- E
```

The market-data layer returns its actual aligned `observation_dates`. `validate_out_of_sample_dates` rejects empty windows, any estimation date on/after the split, any evaluation date before the split, or a non-empty set intersection. The API exposes start/end/count/split/overlap as a methodology audit. The UI and every PDF label fit and OOS metrics permanently.

The structural test does not assert that returns “look reasonable”; it asserts

$$
\max(D_{fit}) < d_{split} \le \min(D_{eval}),\qquad
D_{fit}\cap D_{eval}=\varnothing.
$$

## Before and after

| Measure | Biased Phase 9B headline | Corrected Phase 9C OOS | Interpretation |
|---|---:|---:|---|
| Fit dates | 2025-01-27–2026-01-30 | 2024-01-23–2025-01-29 | Corrected fit ends before split. |
| Evaluation dates | 2025-01-30–2026-01-30 | 2025-01-30–2026-01-30 | Same 249-date evaluation horizon. |
| Overlap | 249 dates | 0 dates | Core validity correction. |
| Headline return | 43.04% fitted expected return | 10.3141% realized annualized return | The old 43.04% was a model estimate, not realized OOS return. |
| Headline Sharpe | 2.6065 fitted model Sharpe | 0.6777 realized OOS Sharpe | Same important distinction. |
| Ending ₹10 lakh wealth | ₹15,07,469.92 | ₹11,01,423.96 | Old wealth replay had future-informed selection. |
| Realized volatility | 16.5310% | 15.2203% | Evaluation-series estimates. |
| Maximum drawdown | -9.1470% | -13.2597% | Corrected period shows a deeper drawdown. |

The requested shorthand “43.0%/2.61/₹15.07L versus 10.31%/0.68/₹11.01L” is retained, but its metric types are labeled honestly: 43.0% and 2.61 were fitted model quantities, whereas 10.31% and 0.68 are realized out-of-sample quantities.

## Corrected real run

Cache `4e0d4bd4-9c3e-4221-9dfe-45bd0f236762` contains 252 fit observations ending 29 January 2025. The solver selected BHARTIARTL 20%, DIVISLAB 20%, EICHERMOT 15%, M&M 20%, SUNPHARMA 5% and WIPRO 20%. Evaluation began 30 January 2025 and ended 30 January 2026 with 249 observations.

No tuning was performed after observing OOS results. The decrease in return/Sharpe and increase in drawdown were accepted and reported. This is stronger evidence of research discipline than preserving an attractive but invalid result.

## Remaining limitations

- The fixed-split and walk-forward runs still test one evaluation year; they do not establish generalization across market cycles.
- Constituents and survivorship characteristics follow the provided 49-symbol dataset.
- Arithmetic historical mean is a noisy expected-return estimator.
- Transaction costs, taxes, liquidity and slippage are absent.
- Monthly rebalancing uses target weights but does not model execution frictions.

The stretch phase subsequently implemented monthly/weekly/quarterly/annual walk-forward
re-estimation with an assertion at every decision date. Its untuned monthly real-data
run returned 1.1737% with 0.0771 Sharpe and -12.0030% drawdown versus the reconstructed
static strategy's 10.2707%, 0.6762 and -13.2597%. Multiple disjoint market-regime folds
and cost-aware evaluation remain the highest-priority methodology extensions.
