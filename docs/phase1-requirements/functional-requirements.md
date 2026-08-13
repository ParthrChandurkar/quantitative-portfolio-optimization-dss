# Functional Requirements

## FR-1 — User authentication and profile management

**Description:** The system shall allow a user to register, sign in, refresh an authenticated session, sign out, and maintain the investor-profile fields used by the application. Passwords shall never be returned by the API. Protected portfolios, runs, scenarios, and reports shall be accessible only to their owner or an authorized administrator.

**Acceptance criteria:**

- **Given** an unregistered email address and a password satisfying the published password rules, **when** the user submits registration, **then** the system creates exactly one account, stores no plaintext password, and returns an authenticated session containing an access token and a refresh token.
- **Given** a valid account and correct credentials, **when** the user signs in, **then** the API returns an access token that authorizes protected requests and a refresh token that can obtain a new access token before the refresh token expires.
- **Given** User A is authenticated, **when** User A requests a portfolio owned by User B, **then** the API returns HTTP 403 or 404 and does not disclose User B's portfolio content.

## FR-2 — Market data and investment-universe management

**Description:** The system shall ingest, validate, normalize, and retrieve dated Nifty 50 membership, daily OHLCV data, benchmark observations, available fundamentals, and derived measures. A user shall be able to select an as-of date and estimation window, and the system shall expose data freshness and validation status before optimization.

**Acceptance criteria:**

- **Given** a source file containing recognized symbol, date, OHLCV, and optional fundamental columns, **when** an administrator starts ingestion, **then** the system maps recognized columns to the canonical schema, rejects rows with an invalid symbol or date, prevents duplicate symbol-date observations, and records accepted and rejected row counts.
- **Given** an as-of date and estimation window with sufficient validated observations, **when** the user loads the universe, **then** the system returns only securities eligible on that date and calculates return and risk inputs without using observations after the as-of date.
- **Given** one or more eligible securities lack the minimum required observations, **when** optimization readiness is checked, **then** the system identifies every excluded security and its exclusion reason before the user runs the model.

## FR-3 — Portfolio problem configuration and validation

**Description:** The system shall allow a user to define capital, objective, risk profile or risk limit, required return where applicable, minimum and maximum position weights, sector caps, cardinality bounds, long-only selection, whole-share preference, estimation window, and benchmark. It shall validate individual values and cross-constraint feasibility before submitting a run.

**Acceptance criteria:**

- **Given** a long-only problem with positive capital, position bounds between 0 and 1, a maximum weight not below the minimum weight, valid sector caps, and a cardinality compatible with those bounds, **when** the user validates the configuration, **then** the system marks it valid and displays the normalized constraints that will be sent to the solver.
- **Given** a minimum weight of 20%, a maximum of five holdings, and a required cardinality of six, **when** the user validates the configuration, **then** the system rejects submission, identifies the conflicting cardinality and weight constraints, and does not create an optimization run.
- **Given** a previously saved valid configuration, **when** the user changes capital or risk profile and saves a copy, **then** the original configuration remains unchanged and the new configuration receives a distinct identifier.

## FR-4 — Constrained portfolio optimization

**Description:** The system shall formulate and solve the configured portfolio problem using SciPy for supported continuous models and PuLP or OR-Tools for models requiring binary or integer decisions. It shall enforce the budget, allocation, sector, cardinality, position, and risk/return constraints selected under FR-3 and report the solver, formulation, status, objective value, elapsed time, and constraint residuals.

**Acceptance criteria:**

- **Given** a valid continuous long-only configuration over 50 eligible assets, **when** the user starts optimization, **then** the system returns one of the defined statuses (`OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `TIME_LIMIT`, or `FAILED`) and, for `OPTIMAL` or `FEASIBLE`, allocation weights sum to 1.000000 within an absolute tolerance of 0.000001 and satisfy every configured bound within the same tolerance.
- **Given** a valid configuration containing a cardinality or whole-share constraint, **when** optimization starts, **then** the system uses a mixed-integer-capable PuLP or OR-Tools backend and the returned portfolio contains no more or fewer holdings than the configured limits permit.
- **Given** a mathematically infeasible configuration that passes syntactic validation, **when** the solver proves infeasibility, **then** the system records status `INFEASIBLE`, returns no recommended allocation, and reports the conflicting or most relevant constraint groups instead of presenting a portfolio as optimal.

## FR-5 — Decision explanation and recommendation rationale

**Description:** For every feasible solution, the system shall generate a traceable explanation containing portfolio-level objective and risk-budget interpretation, active or binding constraints, and holding-level expected-return contribution, risk contribution, diversification effect, and reason for selection or limitation. Explanations shall be derived from stored model inputs and outputs.

**Acceptance criteria:**

- **Given** an `OPTIMAL` or `FEASIBLE` solution, **when** the user opens its explanation, **then** every non-zero holding displays its weight, expected-return contribution, risk contribution, relevant active bound or sector constraint, and at least one quantitative selection rationale consistent with the stored run.
- **Given** a holding weight is within 0.000001 of its configured maximum or a sector allocation is within 0.000001 of its cap, **when** explanations are generated, **then** that bound is labeled binding and the explanation identifies the affected holding or sector and configured limit.
- **Given** a run is `INFEASIBLE`, `TIME_LIMIT`, or `FAILED` with no feasible incumbent, **when** the user requests an explanation, **then** the system explains the run status and does not generate unsupported stock-selection rationale.

## FR-6 — Scenario simulation and re-optimization

**Description:** The system shall allow a user to create market-crash, interest-rate, inflation, sector-shock, budget-change, and risk-profile-change scenarios from a saved baseline. It shall show the scenario assumptions, recalculate affected data or constraints, re-evaluate or re-optimize as specified, and compare scenario and baseline allocations and metrics without modifying the baseline.

**Acceptance criteria:**

- **Given** a saved baseline portfolio and a 20% broad-market shock configured to revalue holdings, **when** the user runs the scenario, **then** the system stores the shock parameters and reports baseline value, stressed value, absolute loss, percentage loss, holding-level loss contribution, and the unchanged baseline values.
- **Given** a saved baseline and a changed sector cap configured for re-optimization, **when** the scenario is run, **then** the system creates a distinct linked optimization run, enforces the new cap, and displays allocation and metric deltas against the baseline.
- **Given** a scenario is missing a required shock magnitude or references a baseline the user cannot access, **when** submission occurs, **then** the system rejects it with a field-specific validation or authorization error and creates no scenario result.

## FR-7 — Portfolio analytics dashboard

**Description:** For a feasible saved or newly solved portfolio, the system shall present allocation by holding and sector, expected return, annualized volatility, Sharpe ratio, Sortino ratio when computable, beta, maximum drawdown, diversification score, risk contributions, historical performance against the selected benchmark, and data-period labels.

**Acceptance criteria:**

- **Given** a feasible portfolio with sufficient return history, **when** the analytics dashboard loads, **then** the displayed allocation totals 100% within 0.01 percentage point and every metric states its unit, estimation period, and benchmark where applicable.
- **Given** portfolio and benchmark observations share a date range, **when** cumulative performance is displayed, **then** both series start from the same normalized base value and use only intersecting trading dates in chronological order.
- **Given** a metric cannot be calculated because required observations are missing or its denominator is zero, **when** the dashboard renders, **then** it displays `Not available` and an explicit reason rather than zero, infinity, or a fabricated value.

## FR-8 — Portfolio persistence, history, and comparison

**Description:** The system shall allow a user to name and save a feasible portfolio and its complete run provenance, list and retrieve owned portfolios, archive a portfolio, and compare two accessible runs. Saving shall preserve an immutable decision record even if market data or a source configuration later changes.

**Acceptance criteria:**

- **Given** an authenticated user and a feasible run, **when** the user saves it with a valid name, **then** the system stores the allocations, metrics, data snapshot identifier, estimation settings, constraints, objective, solver metadata, and run status under a unique portfolio identifier owned by that user.
- **Given** two saved portfolios owned by the user, **when** the user compares them, **then** the system displays differences in holding and sector weights, expected return, volatility, Sharpe ratio, and model configuration using the immutable values saved with each run.
- **Given** a saved portfolio is archived, **when** the default portfolio list is requested, **then** the archived portfolio is omitted; **when** archived items are explicitly requested, **then** it is returned with its archived state and unchanged decision record.

## FR-9 — Report generation and export

**Description:** The system shall generate portfolio-summary, optimization, recommendation/explanation, and scenario reports for accessible runs. Reports shall contain data provenance, model assumptions, constraints, solver status, allocations, analytics, explanations, limitations, and generation time, and shall be downloadable in PDF with a machine-readable CSV export of tabular allocations and metrics.

**Acceptance criteria:**

- **Given** an accessible feasible portfolio, **when** the user requests an optimization report, **then** the generated PDF identifies the portfolio and run, includes the as-of date, data window, objective, all configured constraints, solver and status, allocation table totaling 100% within 0.01 percentage point, key metrics, explanation summary, and risk disclaimer.
- **Given** an accessible scenario result, **when** the user requests a scenario report, **then** the report identifies its baseline, lists every scenario parameter, and shows baseline, scenario, and delta values for allocation and supported risk-return metrics.
- **Given** a report request succeeds, **when** the user requests the corresponding CSV export, **then** the downloaded UTF-8 file contains stable column headers and numeric allocation and metric values without locale-formatted currency symbols or thousands separators.

