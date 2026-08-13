"""Solver-independent quantitative hooks for the Phase 5 explanation layer."""

from __future__ import annotations

import numpy as np

from app.optimization.constraints import TOLERANCE
from app.optimization.types import ExplanationHooks, FloatArray, OptimizationInput


def marginal_return_contributions(
    symbols: tuple[str, ...], expected_returns: FloatArray, weights: FloatArray
) -> dict[str, float]:
    """Return contribution ``mu_i * w_i`` for each asset."""

    contributions = expected_returns * weights
    return dict(zip(symbols, contributions.tolist(), strict=True))


def marginal_risk_contributions(
    symbols: tuple[str, ...], covariance: FloatArray, weights: FloatArray
) -> tuple[dict[str, float], dict[str, float]]:
    """Return exact Euler variance components and their normalized shares.

    Components are ``w_i * (Sigma @ w)_i`` and sum to ``w.T @ Sigma @ w``.
    Normalized shares divide those components by total variance and sum to one.
    """

    components = weights * (covariance @ weights)
    variance = float(weights @ covariance @ weights)
    shares = components / variance if variance > TOLERANCE else np.zeros_like(components)
    return (
        dict(zip(symbols, components.tolist(), strict=True)),
        dict(zip(symbols, shares.tolist(), strict=True)),
    )


def excluded_stock_diagnostics(
    problem: OptimizationInput, weights: FloatArray
) -> dict[str, str]:
    """Categorize every zero-weight stock using auditable deterministic rules."""

    sectors = np.asarray(problem.sectors)
    variances = np.diag(problem.covariance)
    selected_count = int(np.count_nonzero(weights > TOLERANCE))
    diagnostics: dict[str, str] = {}
    for index in np.flatnonzero(weights <= TOLERANCE):
        same_sector = sectors == sectors[index]
        dominated = np.any(
            same_sector
            & (problem.expected_returns >= problem.expected_returns[index])
            & (variances <= variances[index])
            & (
                (problem.expected_returns > problem.expected_returns[index])
                | (variances < variances[index])
            )
            & (weights > TOLERANCE)
        )
        sector_weight = float(np.sum(weights[same_sector]))
        if dominated:
            category = "dominated"
        elif abs(sector_weight - problem.sector_cap(problem.sectors[index])) <= TOLERANCE:
            category = "sector-cap-blocked"
        elif problem.max_holdings is not None and selected_count >= problem.max_holdings:
            category = "cardinality-excluded"
        else:
            category = "cardinality-excluded"
        diagnostics[problem.symbols[index]] = category
    return diagnostics


def compute_explanation_hooks(
    problem: OptimizationInput,
    weights: FloatArray,
    shadow_prices: dict[str, float] | None = None,
) -> ExplanationHooks:
    risk_components, normalized_shares = marginal_risk_contributions(
        problem.symbols, problem.covariance, weights
    )
    return ExplanationHooks(
        marginal_return_contributions(problem.symbols, problem.expected_returns, weights),
        risk_components,
        normalized_shares,
        excluded_stock_diagnostics(problem, weights),
        shadow_prices or {},
    )

