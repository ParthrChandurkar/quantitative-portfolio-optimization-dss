"""Pure shock transforms for all seven supported scenario types."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from app.optimization.types import FloatArray
from app.scenarios.sensitivity_tables import (
    DEFAULT_INFLATION_SENSITIVITY,
    DEFAULT_KAPPA_VOL,
    DEFAULT_RATE_SENSITIVITY,
    INFLATION_SENSITIVITY,
    RATE_SENSITIVITY,
)
from app.scenarios.types import ScenarioType

Constraints = dict[str, Any]
Transform = Callable[
    [FloatArray, FloatArray, Constraints, Mapping[str, Any]],
    tuple[FloatArray, FloatArray, Constraints],
]


def _number(params: Mapping[str, Any], key: str) -> float:
    if key not in params or isinstance(params[key], bool):
        raise ValueError(f"{key} is required and must be numeric")
    try:
        return float(params[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} is required and must be numeric") from exc


def _bounded(value: float, minimum: float, maximum: float, name: str) -> float:
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def market_crash(
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
) -> tuple[FloatArray, FloatArray, Constraints]:
    """Beta-scale returns and increase the complete covariance matrix."""

    delta = _bounded(_number(params, "delta"), -0.50, -0.05, "delta")
    betas = np.asarray(params.get("betas"), dtype=float)
    if betas.shape != mu.shape:
        raise ValueError("betas must align with the asset universe")
    kappa = float(params.get("kappa_vol", DEFAULT_KAPPA_VOL))
    if kappa < 0:
        raise ValueError("kappa_vol must be non-negative")
    return mu + delta * betas, sigma * (1 + abs(delta) * kappa), dict(constraints)


def _sector_adjustment(
    mu: FloatArray,
    sectors: tuple[str, ...],
    delta: float,
    sensitivities: Mapping[str, float],
    default: float,
) -> FloatArray:
    coefficients = np.asarray([sensitivities.get(sector, default) for sector in sectors])
    return mu - delta * coefficients


def rate_increase(
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
) -> tuple[FloatArray, FloatArray, Constraints]:
    delta = _bounded(_number(params, "delta_r"), 0.0025, 0.03, "delta_r")
    sectors = tuple(constraints["sectors"])
    return (
        _sector_adjustment(mu, sectors, delta, RATE_SENSITIVITY, DEFAULT_RATE_SENSITIVITY),
        sigma.copy(),
        dict(constraints),
    )


def inflation(
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
) -> tuple[FloatArray, FloatArray, Constraints]:
    delta = _bounded(_number(params, "delta_pi"), 0.005, 0.05, "delta_pi")
    sectors = tuple(constraints["sectors"])
    transformed = dict(constraints)
    transformed["inflation_delta"] = delta
    return (
        _sector_adjustment(
            mu, sectors, delta, INFLATION_SENSITIVITY, DEFAULT_INFLATION_SENSITIVITY
        ),
        sigma.copy(),
        transformed,
    )


def sector_crash(
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
) -> tuple[FloatArray, FloatArray, Constraints]:
    sector = str(params.get("sector", "")).strip()
    if not sector:
        raise ValueError("sector is required")
    sectors = np.asarray(tuple(constraints["sectors"]))
    if sector not in sectors:
        raise ValueError(f"sector {sector!r} is absent from the universe")
    delta = _bounded(_number(params, "delta_s"), -0.60, -0.10, "delta_s")
    transformed_mu = mu.copy()
    transformed_mu[sectors == sector] += delta
    return transformed_mu, sigma.copy(), dict(constraints)


def _budget_change(
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
    *,
    increase: bool,
) -> tuple[FloatArray, FloatArray, Constraints]:
    new_budget = _number(params, "new_budget")
    old_budget = float(constraints["budget"])
    if new_budget <= 0:
        raise ValueError("new_budget must be positive INR")
    if increase and new_budget <= old_budget:
        raise ValueError("BUDGET_INCREASE requires new_budget above the base budget")
    if not increase and new_budget >= old_budget:
        raise ValueError("BUDGET_REDUCTION requires new_budget below the base budget")
    transformed = dict(constraints)
    transformed["budget"] = new_budget
    # Preserve the base absolute INR minimum lot. This makes any scale-driven linking
    # feasibility change explicit instead of treating a proportional model as sufficient.
    minimum_lot_inr = float(params.get("minimum_lot_inr", old_budget * float(constraints["min_lot_weight"])))
    transformed["minimum_lot_inr"] = minimum_lot_inr
    transformed["min_lot_weight"] = minimum_lot_inr / new_budget
    linking_is_active = (
        constraints.get("min_holdings") is not None
        or constraints.get("max_holdings") is not None
    )
    transformed["lot_feasibility_changed"] = bool(
        linking_is_active
        and not np.isclose(
            transformed["min_lot_weight"], constraints["min_lot_weight"], atol=1e-12
        )
    )
    return mu.copy(), sigma.copy(), transformed


def budget_increase(
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
) -> tuple[FloatArray, FloatArray, Constraints]:
    return _budget_change(mu, sigma, constraints, params, increase=True)


def budget_reduction(
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
) -> tuple[FloatArray, FloatArray, Constraints]:
    return _budget_change(mu, sigma, constraints, params, increase=False)


def risk_profile_change(
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
) -> tuple[FloatArray, FloatArray, Constraints]:
    tolerance = _number(params, "risk_tolerance")
    if tolerance <= 0:
        raise ValueError("risk_tolerance must be positive")
    transformed = dict(constraints)
    transformed["risk_tolerance"] = tolerance
    transformed["sigma_max_sq"] = tolerance**2
    transformed["target_return"] = (
        float(params["target_return"]) if params.get("target_return") is not None else None
    )
    return mu.copy(), sigma.copy(), transformed


TRANSFORMS: dict[ScenarioType, Transform] = {
    ScenarioType.MARKET_CRASH: market_crash,
    ScenarioType.RATE_INCREASE: rate_increase,
    ScenarioType.INFLATION: inflation,
    ScenarioType.SECTOR_CRASH: sector_crash,
    ScenarioType.BUDGET_INCREASE: budget_increase,
    ScenarioType.BUDGET_REDUCTION: budget_reduction,
    ScenarioType.RISK_PROFILE_CHANGE: risk_profile_change,
}


def apply_shock(
    scenario_type: ScenarioType,
    mu: FloatArray,
    sigma: FloatArray,
    constraints: Constraints,
    params: Mapping[str, Any],
) -> tuple[FloatArray, FloatArray, Constraints]:
    return TRANSFORMS[scenario_type](mu, sigma, constraints, params)
