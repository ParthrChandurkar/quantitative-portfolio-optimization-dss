# AI Personalization Layer

*Project: AI-Driven Personalized Investment Planning and Portfolio Optimization (OptiVest)*

## Scope and Relationship to Operations Research

The AI layer is additive to the completed OR decision-support core. It does not replace feasibility constraints, solver status checks, scenario mathematics, or out-of-sample auditing. The historical-mean optimizer remains the default. ML can supply an alternative expected-return vector, recommend editable starting constraints, route questions to existing evidence, and identify conditions worth reviewing. OptiVest does not execute trades, use an external LLM, or claim regulated personalized advice.

The four deployed ML models are a gradient-boosting return regressor, a logistic-regression risk classifier, a TF-IDF/logistic-regression intent classifier, and per-stock Isolation Forest anomaly detectors. The three dedicated AI-facing experiences are questionnaire onboarding, grounded portfolio Q&A, and personalized alerts.

## AI Phase 1: ML-Based Return Forecasting Input

### Method

The forecasting pipeline constructs 12 trailing features from real PostgreSQL market data: 5-, 21-, and 63-day returns; price/SMA relationships; RSI; MACD; 21-day realized volatility; P/E; P/B; dividend yield; and beta. A scikit-learn `GradientBoostingRegressor` predicts forward 21-trading-day adjusted-close return. Every feature and target date is strictly before the exclusive cutoff, and the resulting vector is annualized and aligned to the solver universe. Covariance continues to come from the established historical pipeline, so this phase changes only `mu` when `return_estimation_method=ml_forecast`.

Training used 12,924 stock-date samples before 2025-01-29. RSI and MACD were absent in the loaded Kaggle rows and therefore became imputed, zero-importance features. No post-hoc tuning was performed after observing the evaluation result.

### Real Result

Both methods used the same constraints and disjoint evaluation dates, 2025-01-30 through 2026-01-30:

| Metric | Historical mean | ML forecast |
|---|---:|---:|
| Annualized realized return | 10.2707% | 5.8787% |
| Realized Sharpe | 0.6762 | 0.3453 |
| Realized volatility | 15.1897% | 17.0250% |
| Maximum drawdown | -13.2597% | -13.3183% |
| Final value from Rs. 10,00,000 | Rs. 1,101,423.96 | Rs. 1,058,067.44 |

The model path was technically valid and profitable over this interval but materially underperformed the simpler historical mean. This negative result is retained because it is stronger evidence of methodological honesty than tuning the comparison to make ML appear superior. Walk-forward retraining of the forecast model was not attempted.

## AI Phase 2: Risk-Tolerance Classifier and Defaults

### Method

Six questionnaire answers are encoded from lower to higher risk capacity/willingness and labeled by a documented weighted rubric. Loss reaction (weight 3.0) and horizon (2.0) carry the most influence, followed by income stability and experience (1.5 each), age and dependents (1.0 each). Scores map to Conservative, Moderate, or Aggressive. A reproducible generator produced 5,000 plausible combinations because no real investor outcomes were available.

A stratified 4,000/1,000 split compared multinomial logistic regression with random forest. Logistic regression was selected and predicts only the category. A separate policy maps it to editable risk tolerance/stock-cap/sector-cap defaults: Conservative `0.15/10%/25%`, Moderate `0.22/15%/30%`, and Aggressive `0.35/20%/35%`. This separation makes personalization visible and keeps the OR model authoritative.

### Real Result and Caveat

Logistic regression achieved 99.975% training and 100.000% held-out accuracy; random forest achieved 99.325% and 98.200%. These numbers answer only whether a model can reproduce its synthetic labeling rubric. They do not establish investor suitability, future behavior, or improved investment outcomes. Real outcome data is required for that claim.

## AI Phase 3: Grounded Portfolio Q&A

### Method

The offline assistant uses unigram/bigram TF-IDF and multinomial logistic regression to route seven intents: allocation, diversification, inclusion, exclusion, shock, risk, and unknown. The generator produced 2,100 examples (300 per intent) from transparent templates. A confidence below `0.55` triggers clarification rather than a guessed response.

The classifier does not generate financial facts. Deterministic answer templates read stored Phase 5 explanations, Phase 7 out-of-sample analytics, and current allocation data. Shock questions extract parameters and invoke the real Phase 6 transform and optimizer re-solve. Every returned number must appear exactly in the response grounding bundle; structural tests reject untraceable values.

### Real Result and Caveat

The fixed stratified split contained 1,680 training and 420 held-out examples. Both accuracies were 100.000%, with 60/60 held-out examples correctly routed for every intent. This demonstrates clean separation of the generated templates, not perfect behavior on unrestricted natural language. Real human-authored, multilingual questions are needed for a meaningful robustness estimate.

## AI Phase 4: Personalized Risk and Anomaly Alerts

### Method

Risk drift is deterministic and profile-aware: expected volatility must exceed stored tolerance by more than 0.03; an excess of at least 0.10 is critical. Diversification references are 75, 65, and 55 for Conservative, Moderate, and Aggressive profiles, with a deficit of at least 20 marked critical. The first snapshot is a baseline and cannot trigger drift.

For each held stock, a 200-tree Isolation Forest with contamination `0.02`, median imputation, seed 42, and at least 50 historical rows scores the latest 12-feature vector. Historical rows end strictly before the scored date and are sampled every five observations. Alerts are deduplicated while unacknowledged and store their exact grounding values. A live six-holding check produced zero active alerts; the system correctly permits a no-condition result.

### Performance Finalization

The original successful-optimize and feasible-scenario hooks synchronously awaited the alert checker. On the real 49-stock universe, an optimization solved in 222 ms but the HTTP response took 22.774 seconds. Profiling the six holdings attributed 12.639 seconds to training-query/feature construction, 3.699 seconds to six model fits, and 2.864 seconds to inference-query/features (19.201 seconds measured in those stages). There was no model artifact loading: Isolation Forests were freshly trained.

Finalization moved alert checks to FastAPI background tasks with a fresh async database session. The equivalent live optimize response fell to 1.431 seconds with a 183 ms solve, and alerts remain retrievable shortly afterward from `GET /me/alerts`. Reusing each stock's closing-price array removed repeated feature construction and reduced a foreground six-holding alert check to 7.416 seconds. A cross-request model cache was not added because the models are cutoff-dependent and an in-memory cache can become stale or diverge across workers; a durable keyed artifact/cache belongs in future production work.

## Evaluation Boundaries and Overall Assessment

The AI layer is complete relative to its selected academic scope, but its evidence types differ. Return forecasting and anomaly features use real market data. Risk labels and intent language are synthetic. The return model underperformed, the two classifiers reproduced their synthetic tasks extremely well, and anomaly alerts are unsupervised indicators rather than predictions of adverse events. Those limitations are part of the result, not omissions.

The integration preserves the OR core by default: `historical_mean` is unchanged, recommended constraints are editable, assistant scenarios use the real solver, and alerts observe persisted results after the response. This produces a traceable personalization layer without presenting opaque ML output as an unquestionable investment decision.
