# Research Gap and Novelty

## Research gap

Portfolio optimization is well established in academic literature, and portfolio dashboards are common in consumer software. The unresolved product and engineering gap addressed by this project lies at their intersection.

### Gap 1: optimization without operational constraints

Classical mean-variance examples frequently assume continuously divisible weights and simple budget constraints. A usable equity portfolio must also consider cardinality, minimum and maximum position sizes, sector concentration, available capital, and optionally whole-share quantities. These rules can change the problem from continuous optimization to mixed-integer optimization and can make an apparently reasonable configuration infeasible.

### Gap 2: recommendation without explanation

Many systems present a target allocation without exposing why an asset was selected, which constraints limited it, or how it affects total risk. A solver result alone is insufficient for decision support because the user cannot distinguish an economically meaningful allocation from one driven by an unnoticed bound or data artifact.

### Gap 3: static analysis instead of interrogation

A one-time efficient portfolio does not answer decision questions such as how a market crash, sector shock, interest-rate change, budget change, or different risk profile affects the recommendation. A decision-support workflow must preserve a baseline, apply explicit changes, and compare consistently recalculated outcomes.

### Gap 4: weak reproducibility and data lineage

Return estimates, covariance matrices, universe membership, solver choice, and tolerances materially affect a portfolio. Spreadsheet and black-box workflows often fail to retain all of these inputs with the result. Without a complete run record, the recommendation cannot be independently reproduced or audited.

### Gap 5: separation between research model and usable system

Academic prototypes often stop at a notebook, while retail products hide the model. There is value in demonstrating the entire engineering path from versioned market data and formal constraints to an authenticated API, persistent run record, accessible dashboard, and report.

## Proposed novelty

The project's novelty is the integrated and traceable **Model → Solve → Explain → Simulate** loop for a Nifty 50 equity universe, rather than a claim to invent a new optimization algorithm.

### 1. Constraint-aware model selection

OptiVest maps a validated user configuration to an appropriate solver formulation. Continuous allocations can use SciPy optimization, while cardinality, selection indicators, or whole-share rules invoke a PuLP or OR-Tools mixed-integer model. Solver status and constraint feasibility remain first-class outputs under FR-4.

### 2. Quantitative explanation layer

Under FR-5, each selected holding is accompanied by evidence derived from the same solution: expected-return contribution, marginal or component risk, diversification effect, relevant bounds, and binding sector or risk constraints. Excluded or capped assets can be explained by eligibility, dominance, or active constraints rather than generic prose.

### 3. Re-solvable scenario comparison

Under FR-6, scenarios alter declared inputs or model assumptions and produce a separate scenario result. The system compares baseline and stressed allocations and metrics without silently overwriting the baseline, allowing counterfactual reasoning rather than a static loss calculator.

### 4. Reproducible decision records

Every saved run under FR-8 records its data snapshot, estimation settings, constraints, objective, solver identity and version, random seed where applicable, status, allocations, and metrics. This connects a user-facing recommendation to an auditable research artifact.

### 5. Unified research and product architecture

The React/TypeScript interface, FastAPI service, PostgreSQL data model, and pluggable SciPy/PuLP/OR-Tools engine separate presentation, domain validation, optimization, and persistence. This makes alternative estimators or solvers comparable without changing the requirement semantics.

## Evaluation questions

The implementation shall support evaluation of the following questions:

1. Can the system produce a feasible continuous allocation for 50 assets within the performance target in NFR-1?
2. Can every reported allocation be reproduced from its saved run record within the tolerance in NFR-8?
3. Can a user identify the dominant reason for the inclusion or limitation of every holding using FR-5 outputs?
4. Does a scenario comparison preserve the baseline while consistently recalculating affected allocations and metrics under FR-6?
5. Do constraint validation and solver-status handling prevent an infeasible result from being presented as an optimal recommendation under FR-4?

## Responsible interpretation

OptiVest produces model-based decision evidence, not certain predictions or personalized regulated advice. Historical relationships may fail under new market regimes. Reports must state the estimation period, assumptions, limitations, and the fact that projected returns are not guaranteed.

