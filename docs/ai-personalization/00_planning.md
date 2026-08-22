# AI Personalization Implementation Record

## Candidate Features Under Consideration

The original candidates were ML-based expected-return estimation, questionnaire risk classification, grounded portfolio Q&A, and personalized risk/anomaly alerts. All four were selected and implemented. Open-ended generative advice, trade execution, and outcome-trained suitability prediction were deliberately excluded.

## Selected Features

Four production ML models are present:

1. a `GradientBoostingRegressor` forecasting forward 21-trading-day stock return;
2. multinomial logistic regression classifying questionnaire answers as Conservative, Moderate, or Aggressive;
3. a TF-IDF unigram/bigram plus logistic-regression classifier routing questions among seven assistant intents; and
4. one Isolation Forest per held stock for unusual 12-feature market-state detection.

Three dedicated AI-facing product experiences expose these capabilities: personalized questionnaire onboarding with editable OR defaults, a confidence-gated grounded portfolio assistant, and an alert bell containing deduplicated profile-drift and held-stock anomaly notifications. The return forecast is additionally exposed as the selectable `ml_forecast` optimization input while `historical_mean` remains the default.

## Data Requirements

**Return forecasting.** This model uses the real PostgreSQL-loaded Nifty dataset: adjusted prices, returns, moving-average relationships, RSI, MACD, realized volatility, P/E, P/B, dividend yield, and beta. Training produced 12,924 stock-date rows strictly before the evaluation split. RSI and MACD were absent in the loaded source rows and were median-imputed; they consequently had zero importance in the fitted artifact.

**Risk classification.** No real investor outcomes or suitability labels were available. A reproducible generator produced 5,000 plausible six-answer questionnaire combinations, each labeled by the documented weighted-points rubric. These samples test rubric replication, not whether a person will tolerate losses in reality.

**Intent classification and assistant.** The intent model uses 2,100 synthetic question phrasings generated from 15 transparent patterns per intent, with symbol, sector, shock, and conversational substitutions. Answers themselves use real stored portfolio explanations, analytics, allocations, and Phase 6 scenario results; no investor conversation corpus or external LLM is used.

**Risk and anomaly alerts.** Deterministic drift rules use the user's stored risk profile and latest portfolio snapshot. Isolation Forest uses the real market database and the same 12-feature vectors as the return model, sampled every five observations for each held stock. Alert messages retain the exact computed values in a grounding payload.

## Model/Approach Per Feature

**ML expected returns.** A scikit-learn gradient-boosting regressor learns forward 21-day adjusted-close returns from leakage-safe trailing features. The market adapter selects its annualized forecast vector only when `return_estimation_method=ml_forecast`; covariance construction and every downstream OR constraint remain unchanged.

**Personalized risk defaults.** Multinomial logistic regression was selected over a random-forest candidate after a fixed stratified split. It predicts only the three-category rubric label. A separate auditable policy maps that category to risk tolerance, maximum stock weight, and sector cap, and the user can edit all three before solving.

**Grounded Q&A.** TF-IDF unigram/bigram features feed multinomial logistic regression for seven-way intent routing. A `0.55` confidence threshold activates the `UNKNOWN` fallback. Deterministic templates then render only retrieved values; shock questions call the real scenario transformation and optimizer rather than inventing an answer.

**Personalized alerts.** Risk and diversification drift use explicit category-aware thresholds. Held-stock unusualness is scored by a 200-tree Isolation Forest with contamination `0.02`, median imputation, seed 42, and a minimum of 50 historical vectors. Statistical unusualness is not interpreted as fraud, news, or guaranteed loss.

## Integration Points With Existing OR Engine

- `return_estimation_method` swaps only the expected-return vector (`mu`); the historical default and solver behavior are preserved.
- Risk classification pre-fills visible OR constraints through a category-to-policy lookup; it never locks or silently changes a solve.
- The assistant reads Phase 5 explanations and Phase 7 analytics, and its shock intent invokes the real Phase 6 re-solve.
- Alert checks consume persisted profiles, snapshots, holdings, and market features. Successful optimization and feasible scenario endpoints now enqueue them as FastAPI background work in a fresh database session, so alerts appear shortly afterward through `GET /me/alerts` without extending the solve response.

## Evaluation Results

**Forecast result.** On the zero-overlap 2025-01-30 to 2026-01-30 evaluation window, the historical-mean portfolio returned 10.2707% with 0.6762 Sharpe and finished at Rs. 1,101,423.96. The untuned ML portfolio returned 5.8787% with 0.3453 Sharpe and finished at Rs. 1,058,067.44; volatility was also higher (17.0250% versus 15.1897%). The selectable ML path worked, but it did not beat the simpler baseline on this period.

**Risk-classifier result.** On 4,000 synthetic training and 1,000 held-out rubric-labeled rows, logistic regression achieved 99.975% training accuracy and 100.000% held-out accuracy; random forest achieved 99.325% and 98.200%. This is rubric-replication accuracy, not real-world suitability or outcome accuracy.

**Assistant result.** The stratified 1,680/420 synthetic split produced 100.000% training and held-out intent accuracy with no held-out confusion. That shows the generated templates are separable, not that unrestricted investor language will be classified perfectly. Confidence fallback and structural numeric-grounding tests remain the important safety controls.

**Alert result and performance.** Tests cover anomaly separation, normal suppression, first-snapshot suppression, deduplication, and exact numeric grounding. A live six-holding check produced zero active alerts, which is a valid no-condition result. Before finalization, a real 49-stock optimize solved in 222 ms but returned in 22.774 s because the alert check was awaited. Background dispatch reduced the response to 1.431 s (183 ms solve). Alert analysis itself fell from a profiled 19.201 s to 7.416 s after eliminating repeated full-price-array construction; it remains eventual background work rather than a latency blocker.
