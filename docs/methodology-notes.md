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

## Stretch phase: walk-forward re-estimation

The single-split result above holds one fitted target allocation throughout the entire
evaluation year. The stretch implementation adds a stricter operational test: on the
first trading date of every month it rebuilds expected returns and covariance from the
latest 252 aligned observations strictly before that date, re-solves the original
portfolio's stored constraints, and holds the new weights until the next rebalance.
The simulation contains an explicit per-period assertion that rejects any estimation
date greater than or equal to its rebalance date.

The real 49-stock comparison was run on 2026-08-15 for the same 2025-01-30 to
2026-01-30 evaluation interval and the same Rs. 1,000,000 budget. It produced 13
monthly decision periods. Results were:

| Metric | Walk-forward | Static single split |
|---|---:|---:|
| Final value | Rs. 1,011,596.09 | Rs. 1,101,423.96 |
| Annualized realized return | 1.1737% | 10.2707% |
| Realized volatility | 15.2271% | 15.1897% |
| Realized Sharpe ratio | 0.0771 | 0.6762 |
| Maximum drawdown | -12.0030% | -13.2597% |
| Empirical one-day 95% VaR | Rs. 13,476.87 | Rs. 15,760.97 |

Total one-way turnover, defined as the sum of absolute target-weight changes across
rebalance events, was 8.0000. Transaction costs are deliberately not deducted in this
version. This is a material simplification: because turnover is high, realistic costs
would reduce the walk-forward result further. The lower return is reported without
parameter tuning; it shows that frequent re-estimation can react to noisy recent means
and is not automatically superior to a disciplined static allocation.

### Per-period sanity check

The following rows were reconstructed directly from persisted run
`211b3ed5-a04f-4e1b-958e-28dc82ea7eef`; no optimizer or simulation logic was rerun or
changed.

| Period start | Period end | Holdings selected | Period return | Turnover | Cumulative value |
|---|---|---|---:|---:|---:|
| 2025-01-30 | 2025-01-31 | BHARTIARTL 20.00%, DIVISLAB 20.00%, EICHERMOT 15.00%, M&M 20.00%, SUNPHARMA 5.00%, WIPRO 20.00% | -0.32% | 0.00 | ₹9,96,847.32 |
| 2025-02-01 | 2025-02-28 | BHARTIARTL 20.00%, DIVISLAB 20.00%, EICHERMOT 15.00%, M&M 20.00%, POWERGRID 5.00%, WIPRO 20.00% | -7.95% | 0.10 | ₹9,17,584.55 |
| 2025-03-03 | 2025-03-28 | BAJFINANCE 20.00%, BHARTIARTL 20.00%, DIVISLAB 20.00%, HINDALCO 20.00%, M&M 20.00% | +6.27% | 0.80 | ₹9,75,122.66 |
| 2025-04-01 | 2025-04-30 | BAJFINANCE 20.00%, BHARTIARTL 20.00%, DIVISLAB 20.00%, EICHERMOT 15.00%, JSWSTEEL 5.00%, M&M 20.00% | +4.33% | 0.40 | ₹10,17,317.86 |
| 2025-05-02 | 2025-05-30 | BHARTIARTL 20.00%, DIVISLAB 20.00%, ICICIBANK 20.00%, M&M 20.00%, TECHM 20.00% | +3.17% | 0.80 | ₹10,49,573.64 |
| 2025-06-02 | 2025-06-30 | BAJFINANCE 15.00%, BHARTIARTL 20.00%, DIVISLAB 20.00%, HCLTECH 20.00%, HDFCLIFE 20.00%, TECHM 5.00% | +5.06% | 1.10 | ₹11,02,654.48 |
| 2025-07-01 | 2025-07-31 | BAJFINANCE 15.00%, BHARTIARTL 20.00%, DIVISLAB 20.00%, HCLTECH 20.00%, HDFCLIFE 20.00%, TECHM 5.00% | -7.13% | 0.00 | ₹10,24,087.37 |
| 2025-08-01 | 2025-08-29 | BAJFINANCE 20.00%, BHARTIARTL 20.00%, DIVISLAB 20.00%, HDFCBANK 15.00%, JSWSTEEL 20.00%, SHREECEM 5.00% | -3.27% | 0.90 | ₹9,90,627.33 |
| 2025-09-01 | 2025-09-30 | BAJFINANCE 20.00%, BHARTIARTL 20.00%, DIVISLAB 20.00%, EICHERMOT 20.00%, MARUTI 15.00%, SHREECEM 5.00% | +5.42% | 0.70 | ₹10,44,293.22 |
| 2025-10-01 | 2025-10-31 | BAJFINANCE 20.00%, EICHERMOT 20.00%, JSWSTEEL 20.00%, MARUTI 15.00%, SBIN 5.00%, SHREECEM 20.00% | +1.86% | 0.80 | ₹10,63,668.54 |
| 2025-11-03 | 2025-11-28 | BAJFINANCE 20.00%, BHARTIARTL 10.00%, EICHERMOT 20.00%, JSWSTEEL 15.00%, MARUTI 15.00%, TATASTEEL 20.00% | -2.20% | 0.60 | ₹10,40,259.59 |
| 2025-12-01 | 2025-12-31 | ADANIPORTS 20.00%, BAJAJFINSV 5.00%, BAJFINANCE 20.00%, BHARTIARTL 20.00%, EICHERMOT 15.00%, MARUTI 20.00% | -0.14% | 0.80 | ₹10,38,843.18 |
| 2026-01-01 | 2026-01-30 | BAJFINANCE 20.00%, BPCL 10.00%, EICHERMOT 20.00%, HINDALCO 20.00%, MARUTI 15.00%, SBILIFE 15.00% | -2.62% | 1.00 | ₹10,11,596.09 |

Interpretation: the run is internally consistent and does not show mechanical
thrashing. The listed turnovers sum to exactly 8.0000, average 0.6154 per period, range
from 0.00 to 1.10, and never approach the 2.0 maximum; the initial period and July have
zero turnover. Every allocation contains five or six stocks, has an effective holding
count between 5.00 and 5.71, and no stock exceeds the configured 20% cap. Performance
is not evenly weak: February (-7.95%) and July (-7.13%) are the sharpest portfolio
losses, while the relative shortfall versus the static strategy is concentrated from
July through November; February does not explain much relative underperformance because
the static portfolio also lost 7.56% that month. The selected stocks have complete
19–23-observation bad-period histories and plausible realized moves—for example HCLTECH
fell 14.42% and TECHM 11.65% in July, DIVISLAB fell 7.04% and HDFCBANK 5.70% in August,
and TATASTEEL fell 8.14% in November—so there is no missing-row, zero-return, or isolated
price-data anomaly visible in the loss concentration. The evidence therefore supports
a genuine, regime-dependent estimation/selection-noise effect rather than a compounding
or turnover-reporting bug, while refuting the narrower claim that the shortfall was
spread uniformly across all 13 periods.

## AI Phase 1: return-estimation comparison

The additive ML path was evaluated on the same static out-of-sample interval and the
same optimization constraints as the corrected Phase 9C run. The gradient-boosting
regressor was trained on 12,924 stock-date samples to predict forward 21-trading-day
adjusted-close return. Its exclusive training cutoff was 2025-01-29: every training
feature and label date was earlier than that cutoff. Both optimizers used covariance
observations from 2024-01-23 through 2025-01-29 and both portfolios were evaluated
from 2025-01-30 through 2026-01-30. The structural audit found zero overlapping
estimation/evaluation dates.

| Metric | Historical mean | ML forecast |
|---|---:|---:|
| Annualized realized return | 10.2707% | 5.8787% |
| Realized Sharpe ratio | 0.6762 | 0.3453 |
| Maximum drawdown | -13.2597% | -13.3183% |
| Realized annualized volatility | 15.1897% | 17.0250% |
| Final portfolio value | Rs. 1,101,423.96 | Rs. 1,058,067.44 |
| Fit-period expected return | 42.9119% | 29.9460% |
| Fit-period model volatility | 16.9399% | 20.7871% |
| Holdings | BHARTIARTL 20%, DIVISLAB 20%, EICHERMOT 15%, M&M 20%, SUNPHARMA 5%, WIPRO 20% | ADANIENT 20%, ASIANPAINT 20%, INDUSINDBK 20%, LTIM 20%, NTPC 20% |

The historical path exactly reproduced the established static-split final value and
allocation, confirming that adding the selectable estimator did not change the OR
baseline. The untuned ML portfolio remained profitable but underperformed: it earned
about 5.88% with higher volatility and a lower Sharpe ratio. This is reported without
post-hoc tuning. Over this single period, the selected gradient-boosting features did
not improve return estimation enough to beat the simpler historical mean. RSI and
MACD were absent in the loaded Kaggle rows and were therefore retained as imputed,
zero-importance features; the other requested technical and fundamental features were
available. This limitation and the one-period result mean the comparison demonstrates
a real selectable ML input—not evidence that ML is generally superior.
