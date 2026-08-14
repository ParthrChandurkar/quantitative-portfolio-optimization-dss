# Backtest Methodology Notes

## Phase 9C finding

The original Phase 9B walkthrough was look-ahead biased. The optimizer's cached
expected-return and covariance inputs used 252 aligned observations from 2025-01-27
through 2026-01-30 (`covariance_cache` ID
`09282fd9-3226-4d19-b950-b46398dd3b02`, `as_of_date` 2026-01-30). The historical
evaluation used 249 observations from 2025-01-30 through 2026-01-30. All 249
evaluation dates also appeared in the estimation window, so the overlap was 249 dates
and the earlier Rs. 1,507,469.92 ending value was not valid out-of-sample evidence.

## Corrected design

`estimation_end_date` is now an explicit temporal split boundary. OptiVest:

1. loads only price observations strictly before the split to estimate expected
   returns and covariance;
2. re-solves the configured optimization problem using that historical information;
3. evaluates the fitted weights only on observations on or after the split; and
4. raises an error if the two date sets are empty, cross the boundary, or intersect.

This separation is checked from the actual aligned estimation dates, not inferred from
row counts. The API returns a methodology audit containing both date ranges,
observation counts, the split date, and an overlap flag. The Analytics page and every
generated report permanently label saved snapshot metrics as **IN-SAMPLE FIT** and
historical results as **OUT-OF-SAMPLE BACKTEST**.

## Corrected real-data walkthrough

The validation was rerun on 2026-08-14 through the authenticated API against the real
49-stock PostgreSQL universe, using Rs. 1,000,000, a 252-observation lookback, a 20%
single-stock cap, a 35% default sector cap, and the same risk-tolerance configuration
used by the frontend.

The corrected fit used covariance cache `4e0d4bd4-9c3e-4221-9dfe-45bd0f236762`:
252 aligned observations from 2024-01-23 through 2025-01-29.
The split was 2025-01-30. Evaluation used 249 observations from 2025-01-30 through
2026-01-30. There were zero shared dates. The historically fitted allocation was
20.00% BHARTIARTL, 20.00% DIVISLAB, 15.00% EICHERMOT, 20.00% M&M, 5.00% SUNPHARMA,
and 20.00% WIPRO. Its fit-period expected return was 42.9119% and model volatility was
16.9399%.

The monthly-rebalanced out-of-sample portfolio changed Rs. 1,000,000 to
Rs. 1,101,423.96. Its geometrically annualized realized return was 10.3141%, realized
volatility was 15.2203%, realized Sharpe ratio was 0.6777 at the configured 0% risk-free
rate, maximum drawdown was -13.2597%, and empirical one-day 95% VaR was Rs. 15,800.18.
These are the untuned results of the corrected methodology. They are materially lower
than the invalid replay, as expected.

The same walkthrough also regenerated the 30-point fit-period efficient frontier, ran
a real 20% market-crash scenario, and generated and downloaded a valid 20,388-byte PDF
containing the methodology labels.

## Interpretation

The fit-period forecast and out-of-sample realized return answer different questions.
The first describes what the model estimated using information available before the
split; the second describes what the selected portfolio subsequently experienced.
Their difference is expected and must not be hidden by parameter tuning. These results
remain a historical simulation, not an investment guarantee or recommendation.
