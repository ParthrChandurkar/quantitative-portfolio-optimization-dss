# Existing Solutions Comparison

## Comparison

| Existing solution | What it does | Limitation for the proposed DSS |
|---|---|---|
| Zerodha Console | Reports brokerage holdings, transactions, account statements, tax information, and portfolio performance for a Zerodha account. | Primarily describes an existing portfolio; it does not formulate and solve a user-defined Nifty 50 LP/MILP with cardinality, sector, position, and risk constraints or explain the mathematical recommendation. |
| Groww / Smallcase | Groww provides retail investing and portfolio views; Smallcase offers curated or rules-based baskets that users can invest in and track. | Recommendations or baskets are platform-defined and are not a transparent, user-configurable OR model. Users cannot inspect solver feasibility, binding constraints, marginal contribution, or re-solve the same model under controlled shocks. |
| Excel Markowitz templates | Demonstrate return, covariance, efficient-frontier, and Solver-based mean-variance calculations in a familiar spreadsheet. | Formula changes and manual data handling are error-prone; cardinality and sector rules become difficult to maintain; access control, data lineage, run history, reproducibility, automated validation, and scalable scenario comparison are limited. |
| Bloomberg / Aladdin | Provides institutional-grade market data, portfolio construction, risk analytics, scenario analysis, compliance, and investment workflows. | Licensing, data, infrastructure, and operational complexity are unsuitable for most retail users and academic deployments; implementation details and model behavior may be proprietary and cannot serve as an inspectable teaching artifact. |
| Generic robo-advisors | Collect a risk questionnaire and recommend or manage diversified model portfolios, commonly using funds or ETFs. | The recommendation logic is usually abstracted from the user, the asset universe and constraints are not freely configurable, and the user cannot audit a Nifty 50 stock-level optimization or interrogate binding constraints and counterfactual solutions. |

## Implications for OptiVest

The comparison identifies a gap between accessible portfolio interfaces and transparent constrained optimization. OptiVest combines the accessibility of a web application with explicit operations-research modeling, solver-status visibility, holding-level explanations, reproducible data lineage, and user-controlled scenario re-solving.

OptiVest is not intended to replace a brokerage, market-data terminal, or regulated advisory service. Its differentiator is the auditable decision loop described by FR-3 through FR-9: configure the mathematical problem, solve it, explain it, simulate changes, analyze the result, preserve it, and report it.

