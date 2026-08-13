"""Documented sector sensitivity assumptions used by deterministic shocks."""

# These coefficients are transparent scenario-calibration assumptions, not values fitted
# to the Kaggle dataset. A coefficient is the annual expected-return change per unit
# increase in the macro factor. They should be reviewed against empirical estimates once
# the real dataset has completed EDA and validation.
RATE_SENSITIVITY: dict[str, float] = {
    "Financials": 1.35,
    "Financial Services": 1.35,
    "Real Estate": 1.50,
    "Automobile": 1.20,
    "Auto": 1.20,
    "Infrastructure": 1.10,
    "Cement": 1.05,
    "IT": 0.75,
    "Energy": 0.70,
    "Metals": 0.90,
    "Power": 0.80,
    "Telecom": 0.65,
    "Consumer Durables": 0.90,
    "FMCG": 0.35,
    "Pharma": 0.30,
    "Healthcare": 0.30,
}

INFLATION_SENSITIVITY: dict[str, float] = {
    "Financials": 0.90,
    "Financial Services": 0.90,
    "Real Estate": 1.15,
    "Automobile": 1.25,
    "Auto": 1.25,
    "Infrastructure": 1.10,
    "Cement": 1.30,
    "IT": 0.55,
    "Energy": 0.25,
    "Metals": 0.40,
    "Power": 0.50,
    "Telecom": 0.60,
    "Consumer Durables": 1.20,
    "FMCG": 0.45,
    "Pharma": 0.35,
    "Healthcare": 0.35,
}

DEFAULT_RATE_SENSITIVITY = 0.75
DEFAULT_INFLATION_SENSITIVITY = 0.75
DEFAULT_KAPPA_VOL = 0.5

