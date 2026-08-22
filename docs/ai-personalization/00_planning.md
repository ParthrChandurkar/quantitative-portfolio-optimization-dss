# AI Personalization Planning

## Candidate Features Under Consideration

- ML-based questionnaire risk classification
- ML return forecasting as an additive optimizer input
- Grounded offline portfolio Q&A assistant
- Personalized portfolio drift and held-stock anomaly alerts

## Selected Features

- Leakage-safe gradient-boosting expected-return forecasting (AI Phase 1)
- Transparent rubric-trained risk-category classification and editable defaults (AI Phase 2)
- TF-IDF intent routing with deterministic, source-grounded answers (AI Phase 3)
- Profile-aware deterministic drift rules plus Isolation Forest anomalies (AI Phase 4 stretch)

## Data Requirements

- Existing Nifty-50 price, technical, and fundamental tables for return forecasting
- Synthetic questionnaire combinations labeled by the documented rubric; no real investor outcome labels are available
- Synthetic question phrasings generated from transparent intent templates; no real investor conversation corpus is claimed
- Existing 12-feature market vectors for unsupervised held-stock anomaly detection

## Model/Approach Per Feature

- Gradient boosting regression for forward 21-day stock returns
- Logistic regression selected against a random-forest baseline for rubric-category replication
- TF-IDF unigram/bigram features with logistic regression for seven-way intent classification
- Explicit profile-category drift thresholds and per-stock Isolation Forest models

## Integration Points With Existing OR Engine

- Selectable expected-return vector in the market-data adapter
- Category-to-constraint lookup pre-fills risk tolerance, stock cap, and sector cap without changing or bypassing the OR solver
- Read-only access to stored explanations and analytics, plus real Phase 6 re-solving for hypothetical shocks
- Post-optimization/scenario hooks, persisted deduplicated alerts, and the authenticated notification bell

## Evaluation Plan

- Strict out-of-sample market backtest for return forecasting
- Stratified held-out synthetic accuracy against the explicit rubric for risk classification
- Stratified held-out intent accuracy, confusion matrix, confidence fallback, and structural numeric-grounding tests
- Synthetic anomaly separation, normal-range suppression, first-snapshot suppression, deduplication, and structural numeric-grounding tests
