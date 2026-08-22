# Introduction

*Project: AI-Driven Personalized Investment Planning and Portfolio Optimization (OptiVest)*

## Project Scope: OR Foundation + AI Personalization Layer

The implemented system is a complete Operations Research decision-support foundation comprising continuous and mixed-integer portfolio optimization, quantitative explanations, scenario re-solving, and static plus walk-forward validated analytics. AI Phase 1 adds a trained, leakage-safe gradient-boosting expected-return estimator as a selectable alternative to the unchanged historical-mean input. AI Phase 2 adds a questionnaire-based classifier trained to reproduce an explicit synthetic-label rubric and uses its predicted category to recommend visible, editable OR constraints. AI Phase 3 adds an offline TF-IDF intent classifier whose deterministic answers expose their stored explanation, analytics, or scenario grounding. No external generative model is used. Broader behavior- and outcome-trained personalization remains future work and is not attributed to the present system.

## Project context and problem

Choosing a Nifty-50 portfolio is a coupled decision: increasing one allocation changes the capital, risk budget, concentration, and sector capacity available to every other stock. Ranking securities by return cannot enforce a budget identity, position bounds, sector caps, cardinality, or a required risk/return level.

OptiVest converts investor preferences into an explicit operations-research problem, classifies the solver outcome, explains the allocation, re-solves controlled scenarios, evaluates it on real prices, and preserves the result. It supports decisions; it neither executes trades nor guarantees returns. Brokerage execution, intraday trading, derivatives, leverage, tax advice, and regulated advice are outside scope.

## Research gap

| Existing approach | Capability | Remaining limitation |
|---|---|---|
| Zerodha Console | Holdings, transactions and performance | Describes an account; does not solve a transparent constrained OR model. |
| Groww/Smallcase | Retail investing and curated baskets | Logic is not a user-configurable solver with visible binding constraints. |
| Excel Markowitz templates | Covariance and frontier demonstrations | Fragile manual formulas; weak lineage, auth, histories, tests and scenarios. |
| Bloomberg/Aladdin | Institutional construction and risk | Cost, infrastructure and proprietary behavior limit academic accessibility. |
| Generic robo-advisors | Risk questionnaire and model portfolios | Universe, constraints, diagnostics and counterfactuals are normally hidden. |

The gap is at the intersection of transparent optimization and a usable, reproducible product—not the absence of portfolio theory.

## Novel contribution

The contribution is an integrated **Model → Solve → Explain → Simulate → Validate** loop:

1. validated configuration selects continuous QP, MILP/MAD or hybrid CP-SAT/QP;
2. every result carries a solver status and independently recomputed constraints;
3. narratives are derived from the numerical solution;
4. scenarios transform inputs and re-solve rather than scaling wealth;
5. exact estimation and evaluation dates are separated for out-of-sample validation; and
6. API, UI, database, tests and reports retain the decision trail.

Finding and correcting look-ahead bias in Phase 9C strengthens the contribution: methodology integrity is implemented behavior, not report-only prose.

## Achieved objectives

- Maintain 49 stocks and 287,263 accepted rows per dated data table.
- Solve constrained allocations and distinguish pending, solved, infeasible, failed and time-limited outcomes.
- Explain selections/exclusions with return, risk, diversification, cardinality and cap evidence.
- Compare seven scenario families against a preserved baseline.
- Present fit estimates beside realized out-of-sample analytics.
- Generate downloadable methodology-labeled PDFs in rupees.
- Answer supported portfolio questions through an offline, confidence-gated NLP router with auditable source fields.

The formal FR/NFR baseline remains in `docs/phase1-requirements/`; this report describes what was actually built.
