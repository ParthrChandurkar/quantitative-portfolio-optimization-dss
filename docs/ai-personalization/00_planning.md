# AI Personalization Planning

## Candidate Features Under Consideration

- ML-based questionnaire risk classification
- ML return forecasting as an additive optimizer input

## Selected Features

- Leakage-safe gradient-boosting expected-return forecasting (AI Phase 1)
- Transparent rubric-trained risk-category classification and editable defaults (AI Phase 2)

## Data Requirements

- Existing Nifty-50 price, technical, and fundamental tables for return forecasting
- Synthetic questionnaire combinations labeled by the documented rubric; no real investor outcome labels are available

## Model/Approach Per Feature

- Gradient boosting regression for forward 21-day stock returns
- Logistic regression selected against a random-forest baseline for rubric-category replication

## Integration Points With Existing OR Engine

- Selectable expected-return vector in the market-data adapter
- Category-to-constraint lookup pre-fills risk tolerance, stock cap, and sector cap without changing or bypassing the OR solver

## Evaluation Plan

- Strict out-of-sample market backtest for return forecasting
- Stratified held-out synthetic accuracy against the explicit rubric for risk classification
