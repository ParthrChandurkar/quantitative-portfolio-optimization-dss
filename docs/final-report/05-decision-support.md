# Decision Support and Explainability

*Project: AI-Driven Personalized Investment Planning and Portfolio Optimization (OptiVest)*

## From solution to evidence

An allocation alone does not reveal whether a stock was chosen for return, diversification, a minimum-holdings rule, or merely because another cap bound the problem. Phase 5 consumes the same symbols, weights, expected returns, covariance, sector labels, constraint reports, solver diagnostics and shadow prices used by optimization. It does not call a language model or invent a second scoring path.

For asset (i), return contribution is (w_i\mu_i). Marginal covariance risk is derived from ((\Sigma w)_i); normalized/component values and leave-one-out diversification effects support the narrative. Portfolio diversification combines effective number of holdings with sector breadth and is stored beside the snapshot.

## Stable reason taxonomy

| Reason code | Decision interpretation |
|---|---|
| `high_risk_adjusted_return` | Included with sufficiently strong return percentile and controlled normalized risk share. |
| `diversification_value` | Included with low average correlation and useful return. |
| `cardinality_floor` | Included primarily to satisfy minimum holdings. |
| `sector_requirement` | Included to satisfy configured sector presence. |
| `dominated` | Excluded because another asset offers at least as much return with equal/better risk/correlation evidence. |
| `sector_cap_binding` | Excluded because its sector capacity is occupied. |
| `cardinality_excluded` | Eligible, but outside the maximum selected support. |
| `single_weight_cap_indirect` | A useful position would require breaching the individual cap. |

Classification uses deterministic predicate precedence. Templates interpolate stored quantitative evidence, producing reproducible text for the same result.

## Real generated narratives

The following are verbatim system outputs from optimization run `73e0d311-51c9-4681-a4b1-9c32d9b4e9bb`:

> AXISBANK was selected for its 39.2% expected return with an efficient risk contribution; its diversification effect changes portfolio risk by -11.78%.

AXISBANK had 5.87546310 percentage points of marginal return contribution and 0.32125748 percentage points of stored marginal risk contribution.

> BPCL was selected for its 41.0% expected return with an efficient risk contribution; its diversification effect changes portfolio risk by -21.13%.

BPCL had 8.20018324 percentage points of marginal return contribution and 0.57593247 percentage points of stored marginal risk contribution.

A real exclusion illustrates cap evidence:

> HDFCBANK was excluded because Financials is at its 35% cap, currently occupied by AXISBANK, SBIN.

These narratives appear directly in the Portfolio Details screenshot in Chapter 3 and are persisted in `explanation_items` for reporting and audit.

## Scenario decision support

Seven scenario types operate on inputs and re-solve:

- market crash: (mu_i'=\mu_i+\delta\beta_i), (Sigma'=\Sigma(1+|\delta|\kappa_{vol}));
- rate increase and inflation: sector-sensitive expected-return adjustments;
- sector crash: changes only target-sector expected returns;
- budget increase/reduction: changes budget and flags whether weights remain scale-invariant or lot feasibility changes;
- risk-profile change: recomputes the risk/return control and solves again.

The real 20% crash used (kappa_{vol}=0.5). Expected return moved from 43.04% to 30.06%, volatility from 16.51% to 17.25%, and Sharpe from 2.61 to 1.74. The system attributed the material allocation change to BPCL (-10 points) and HEROMOTOCO (+10 points), rather than presenting only an aggregate loss.

Rate/inflation sensitivity coefficients are transparent expert assumptions in `sensitivity_tables.py`; they were not statistically fitted to the Kaggle data. This limitation is intentionally retained in reports and future-work recommendations.

## Audit and responsible interpretation

Constraint logs store binding flags, slack and relaxation shadow prices. Reports reuse persisted snapshot values and the same analytics service, add an academic/non-advice disclaimer, and now label fit versus out-of-sample evidence. Explanations describe why the implemented model behaved as it did; they do not prove economic causality or future performance.
