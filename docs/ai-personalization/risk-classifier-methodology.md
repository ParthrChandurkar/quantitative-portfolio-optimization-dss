# Risk-Tolerance Classifier Methodology

## What the Ground Truth Means

The ground truth is the explicit weighted-points policy in
`backend/app/personalization/label_rubric.py`. It is not derived from the Kaggle stock
dataset, observed investor decisions, portfolio outcomes, or financial-advice labels.
The six answers are encoded from 1 (lower risk capacity/willingness) to 4 (higher),
then weighted as follows: age 1.0, investment horizon 2.0, income stability 1.5,
reaction to a 20% loss 3.0, investment experience 1.5, and financial dependents 1.0.
Scores up to 21 are Conservative, scores above 21 and up to 31 are Moderate, and
scores above 31 are Aggressive. The loss reaction and horizon deliberately carry the
largest weights.

## Synthetic Training Data

There are no real labeled investor outcomes in this project. The generator creates
5,000 plausible questionnaire combinations with a fixed random seed. It samples age
around working-age users; conditions horizon and experience on age; makes dependents
more common in middle age; and conditions loss reaction on experience. Every sampled
row is labeled by the rubric above and saved to
`backend/app/personalization/data/synthetic_risk_labels.csv`.

These distributions are modeling assumptions for covering plausible combinations.
They are not claimed to describe the Indian investor population.

## Model Comparison and Selected Classifier

The fixed dataset was split into 4,000 training rows and 1,000 held-out test rows with
class stratification and random seed 42. Both required candidates were trained without
post-hoc tuning:

| Classifier | Training accuracy | Held-out accuracy |
|---|---:|---:|
| Logistic regression | 99.975% | 100.000% |
| Random forest | 99.325% | 98.200% |

Logistic regression was selected because it achieved the higher held-out accuracy.
Its saved artifact contains per-class coefficients, candidate metrics, feature order,
split sizes, and an explicit label-source statement.

These accuracies mean “how accurately did the classifier reproduce the deterministic
rubric on held-out synthetic combinations?” They do **not** measure real-world
predictive accuracy, investor suitability, future behavior, or investment outcomes.

## Category-to-Constraint Policy

The model predicts only a category. A separate lookup table maps it to editable OR
defaults:

| Category | Risk tolerance | Maximum stock weight | Default sector cap |
|---|---:|---:|---:|
| Conservative | 0.15 | 10% | 25% |
| Moderate | 0.22 | 15% | 30% |
| Aggressive | 0.35 | 20% | 35% |

This separation keeps the optimization policy independently auditable. The onboarding
screen displays the category, confidence, and exact defaults. Users may edit every
constraint before solving; the classifier never locks or silently applies a value.

## Reproduction

From `backend/`:

```bash
python -m app.personalization.generate_training_data
python -m app.personalization.train_risk_classifier
pytest tests/personalization tests/api/test_personalization.py --cov=app.personalization
```

The fresh phase test run passed 10 personalization/API tests and measured 92.08%
coverage for `app.personalization`, exceeding the 85% target. The complete backend run
passed 188 tests with 3 environment-dependent integration skips.
