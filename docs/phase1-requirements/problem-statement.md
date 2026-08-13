# Problem Statement

## Project title

Decision Support System for Quantitative Portfolio Optimization Using Operations Research Techniques

Product name: **OptiVest**

## Background

An investor choosing among Nifty 50 equities must balance expected return against risk while also respecting practical restrictions such as available capital, sector concentration, position-size bounds, diversification, and the number of securities that can be held. These decisions are interdependent: increasing one allocation changes the capital, risk, and concentration available to every other allocation.

Common retail investment tools report holdings or offer pre-built baskets, but they do not generally formulate the investor's preferences as a constrained mathematical optimization problem. Spreadsheet implementations can demonstrate mean-variance optimization, but they are difficult to validate, reproduce, explain, and operate safely with changing data. Institutional systems provide advanced capabilities but are inaccessible for most individual investors and academic use.

The resulting decision problem is not merely to identify stocks with high historical returns. It is to determine a feasible portfolio that best satisfies a stated objective under explicit, auditable constraints, explain why the solution was selected, and show how that solution behaves when assumptions change.

## Problem definition

OptiVest shall provide a web-based decision support system that:

1. Maintains a validated Nifty 50 investment universe and the market and fundamental data required for analysis.
2. Captures an investor's budget, risk preference, diversification rules, sector limits, and position constraints.
3. Converts those inputs into a formal linear, mixed-integer linear, or nonlinear optimization model as appropriate.
4. Solves the model using SciPy, PuLP, or OR-Tools and clearly distinguishes an optimal, feasible, infeasible, failed, or timed-out result.
5. Explains the recommended allocation using quantitative evidence, active constraints, risk-budget use, and marginal contribution measures.
6. Allows the investor to apply defined market and portfolio scenarios and compare the stressed result with the original solution.
7. Presents risk, return, allocation, diversification, and benchmark analytics in a usable dashboard.
8. Preserves solution inputs and outputs so decisions can be reproduced, compared, and exported.

The system supports a decision; it does not guarantee future performance or execute trades.

## Objectives

- Produce a mathematically feasible allocation for approximately 50 Nifty securities under explicit investor constraints.
- Maximize the selected risk-adjusted objective or minimize portfolio risk for a required return, depending on the chosen model.
- Make the recommendation transparent enough for a user to understand why each asset was included, excluded, or limited.
- Support controlled what-if analysis without changing the saved baseline portfolio.
- Provide reproducible reports suitable for academic evaluation and investment review.
- Establish stable requirement identifiers that can be traced to later design, implementation, and tests.

## Stakeholders

| Stakeholder | Need |
|---|---|
| Investor or analyst | Configure, solve, understand, stress-test, save, and export a portfolio decision. |
| Project evaluator or researcher | Inspect the mathematical basis, assumptions, data lineage, reproducibility, and measured results. |
| System administrator | Operate data ingestion, monitor service health, and diagnose failed jobs without viewing user passwords. |
| Developer and QA engineer | Implement and verify behavior against stable, testable requirements. |

## System boundary

### In scope

- Responsive React and TypeScript web interface styled with Tailwind CSS.
- FastAPI REST backend with JWT access and refresh authentication.
- PostgreSQL persistence for users, market data, model configurations, optimization runs, portfolios, scenarios, and reports.
- Nifty 50 daily OHLCV, derived return and risk measures, available fundamentals, and benchmark data.
- Continuous and discrete portfolio models implemented through SciPy, PuLP, and/or OR-Tools.
- Constraint validation, optimization status reporting, explanation generation, scenario analysis, portfolio comparison, dashboards, and report export.

### Out of scope

- Brokerage integration, order placement, execution, settlement, or custody.
- Personalized tax, legal, or regulated investment advice.
- Intraday or high-frequency trading.
- Derivatives, leverage, short selling, and currencies in the initial release.
- Guaranteed forecasts or guaranteed investment returns.
- Unrestricted support for securities outside the configured Nifty 50 universe in the initial release.

## Assumptions and dependencies

- Historical data is available under terms that permit its use for this academic project.
- Nifty 50 membership changes over time; each dataset observation and optimization run is associated with an effective date.
- Expected returns and covariance are estimates based on declared data windows and methods, not known future values.
- Long-only allocation is the default model; additional bounds can narrow but cannot expand the permitted universe.
- A solution is meaningful only when its inputs, estimation window, solver, solver version, constraints, and status are retained.
- Internet connectivity is required for remote data refreshes, but previously ingested data remains available during a provider outage.

## Success criteria

The project is successful when a registered user can select a valid as-of date, configure an admissible portfolio problem, obtain a correctly classified solver result, inspect an explanation and analytics for a feasible solution, run and compare a scenario, save the portfolio, and export a reproducible report while meeting NFR-1 through NFR-8.
