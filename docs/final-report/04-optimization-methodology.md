# Optimization Methodology

## Notation and estimation

For (n) assets, let (w_i) be portfolio weight, (mu_i) annual expected return, (Sigma) annual covariance, (B) budget in INR, (s(i)) the sector of asset (i), (y_i\in\{0,1\}) its selection flag, and (r_{ti}) observed return in period (t).

For aligned daily adjusted-close returns (r_t), the implementation uses the arithmetic estimators

$$
\mu = 252\,\operatorname{mean}(r_t), \qquad
\Sigma = 252\,\operatorname{cov}(r_t).
$$

The exact aligned dates are persisted in `covariance_cache`; Phase 9C requires every estimation date to precede the evaluation split.

## Continuous mean-variance QP (SciPy SLSQP)

When a target return (R^*) is supplied, OptiVest solves

$$
\min_w \quad w^T\Sigma w
$$

subject to the implemented constraints

$$
\begin{aligned}
\text{C1: }&\sum_{i=1}^{n}w_i=1,\\
\text{C2: }&w_i\ge 0,\\
\text{C3: }&w_i\le w_{\max},\\
\text{C4: }&\sum_{i:s(i)=q}w_i\le c_q &&\forall q,\\
&\mu^T w\ge R^*.
\end{aligned}
$$

When a volatility ceiling (sigma_{\max}) replaces the return floor, the objective and risk constraint are

$$
\max_w \quad \mu^T w,qquad
\text{C5: }w^T\Sigma w\le \sigma_{\max}^2.
$$

Portfolio model metrics are

$$
\mu_p=\mu^Tw,\qquad \sigma_p=\sqrt{w^T\Sigma w},\qquad
S=\frac{\mu_p-r_f}{\sigma_p}.
$$

SLSQP receives C1 as an equality and all floors/caps as inequalities. After solving, the framework-independent checker recomputes C1–C5 with tolerance (10^{-6}); a numerically invalid point is not labeled optimal.

## Cardinality-constrained MILP/MAD (PuLP/CBC)

With selection variables, OptiVest implements the Konno–Yamazaki mean absolute deviation model. Let (ar r_i=T^{-1}\sum_t r_{ti}), centered portfolio deviation (d_t=\sum_i(r_{ti}-\bar r_i)w_i), and non-negative (z_t) linearize (|d_t|):

$$
\min_{w,y,z}\quad \frac{1}{T}\sum_{t=1}^{T}z_t
$$

$$
z_t\ge d_t,\qquad z_t\ge-d_t,\qquad z_t\ge0.
$$

C1–C4 and the return floor remain, with

$$
\begin{aligned}
\text{C6: }&K_{\min}\le\sum_i y_i\le K_{\max},\\
\text{C7: }&w_{\min}y_i\le w_i\le w_{\max}y_i,\\
&y_i\in\{0,1\}.
\end{aligned}
$$

If the user supplies a risk tolerance instead of (R^*), CBC maximizes (mu^Tw) subject to the linearized MAD ceiling. Shadow prices are obtained from the continuous relaxation and labeled accordingly.

## OR-Tools hybrid

The OR-Tools path first solves the unconstrained continuous QP, scales its candidate weights into CP-SAT scores, selects a support satisfying C6, then runs a restricted SciPy QP with C7 enforced. It is explicitly a support-selection heuristic, not a claim that CP-SAT directly solves the quadratic model.

## Structural feasibility checks

Before any solver call, OptiVest detects conflicts including (K_{\max}w_{\max}<1), (nw_{\max}<1), (K_{\min}w_{\min}>1), invalid cardinality ordering, and aggregate sector capacity below one. The returned status distinguishes optimal, feasible, infeasible, time-limit and failed states.

## Deterministic five-stock worked example

The Phase 4 fixture uses ₹25,00,000, target return 14%, maximum weight 40%, IT cap 40%, and diagonal annual covariance from volatilities RELIANCE 22%, TCS 18%, HDFCBANK 16%, INFY 21%, ITC 14%.

For the continuous QP, the actual solver output was:

| Asset | Weight | INR allocation |
|---|---:|---:|
| RELIANCE | 12.9477% | ₹3,23,693.28 |
| TCS | 22.2633% | ₹5,56,581.72 |
| HDFCBANK | 22.6305% | ₹5,65,761.83 |
| INFY | 17.4299% | ₹4,35,747.99 |
| ITC | 24.7286% | ₹6,18,215.19 |

The result exactly meets the 14% return floor (within solver tolerance), has variance (0.0062667011), volatility 7.91625%, and all constraints pass. The cardinality fixture dispatches to PuLP/CBC and returns RELIANCE 6.6667%, TCS 40%, HDFCBANK 40%, ITC 13.3333%, INFY 0%, with 14.00% expected return and 9.92147% covariance-reported volatility.

## Corrected real six-stock example

The genuine Phase 9C fit used cache `4e0d4bd4-9c3e-4221-9dfe-45bd0f236762`: 252 aligned observations from 23 January 2024 through 29 January 2025, all strictly before the 30 January 2025 split.

| Asset | Fitted weight | INR at ₹10,00,000 |
|---|---:|---:|
| BHARTIARTL | 20.00% | ₹2,00,000 |
| DIVISLAB | 20.00% | ₹2,00,000 |
| EICHERMOT | 15.00% | ₹1,50,000 |
| M&M | 20.00% | ₹2,00,000 |
| SUNPHARMA | 5.00% | ₹50,000 |
| WIPRO | 20.00% | ₹2,00,000 |

Fit-period expected return was 42.9119% and model volatility 16.9399%. These are estimates, not validation results. Applying the fixed weights monthly over 249 subsequent observations through 30 January 2026 produced ₹11,01,423.96, 10.3141% annualized realized return, 15.2203% realized volatility, 0.6777 realized Sharpe, and -13.2597% maximum drawdown.

The large gap between forecast and realization is reported rather than tuned away.
