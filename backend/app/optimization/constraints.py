"""Named C1-C7 portfolio constraints and independent feasibility checks."""

from __future__ import annotations

import numpy as np

from app.optimization.types import ConstraintReport, FloatArray, OptimizationInput

TOLERANCE = 1e-6


def c1_budget(weights: FloatArray, tolerance: float = TOLERANCE) -> ConstraintReport:
    """C1 Budget: portfolio weights sum to one."""

    total = float(np.sum(weights))
    slack = 1.0 - total
    return ConstraintReport("C1 Budget", abs(slack) <= tolerance, abs(slack) <= tolerance, slack)


def c2_non_negativity(
    weights: FloatArray, tolerance: float = TOLERANCE
) -> ConstraintReport:
    """C2 Non-negativity: a long-only portfolio has no negative weight."""

    minimum = float(np.min(weights))
    return ConstraintReport(
        "C2 Non-negativity", minimum >= -tolerance, minimum <= tolerance, minimum
    )


def c3_max_single_weight(
    weights: FloatArray, maximum: float, tolerance: float = TOLERANCE
) -> ConstraintReport:
    """C3 Maximum single-stock allocation."""

    slack = maximum - float(np.max(weights))
    return ConstraintReport("C3 Max single-stock weight", slack >= -tolerance, abs(slack) <= tolerance, slack)


def c4_sector_caps(
    weights: FloatArray,
    sectors: tuple[str, ...],
    caps: dict[str, float],
    default_cap: float,
    tolerance: float = TOLERANCE,
) -> tuple[ConstraintReport, ...]:
    """C4 Sector caps, returned as one independently auditable report per sector."""

    sector_array = np.asarray(sectors)
    reports: list[ConstraintReport] = []
    for sector in sorted(set(sectors)):
        allocation = float(np.sum(weights[sector_array == sector]))
        cap = caps.get(sector, default_cap)
        slack = cap - allocation
        reports.append(
            ConstraintReport(
                f"C4 Sector cap: {sector}",
                slack >= -tolerance,
                abs(slack) <= tolerance,
                slack,
            )
        )
    return tuple(reports)


def c5_risk_ceiling(
    weights: FloatArray,
    covariance: FloatArray,
    volatility_ceiling: float | None,
    tolerance: float = TOLERANCE,
) -> ConstraintReport:
    """C5 Risk ceiling expressed as annualized portfolio variance."""

    if volatility_ceiling is None:
        return ConstraintReport("C5 Risk ceiling", True, False, None, details="Not configured")
    variance = float(weights @ covariance @ weights)
    slack = volatility_ceiling**2 - variance
    return ConstraintReport("C5 Risk ceiling", slack >= -tolerance, abs(slack) <= tolerance, slack)


def c6_cardinality(
    weights: FloatArray,
    minimum: int | None,
    maximum: int | None,
    tolerance: float = TOLERANCE,
) -> ConstraintReport:
    """C6 Cardinality based on weights that exceed numerical tolerance."""

    count = int(np.count_nonzero(weights > tolerance))
    lower = minimum or 0
    upper = maximum if maximum is not None else len(weights)
    satisfied = lower <= count <= upper
    slack = float(min(count - lower, upper - count))
    return ConstraintReport(
        "C6 Cardinality", satisfied, count in {lower, upper}, slack, details=f"holdings={count}"
    )


def c7_linking(
    weights: FloatArray,
    included: FloatArray,
    minimum_lot: float,
    maximum: float,
    tolerance: float = TOLERANCE,
) -> ConstraintReport:
    """C7 Link selection flags to lower and upper allocation bounds."""

    lower_slack = weights - minimum_lot * included
    upper_slack = maximum * included - weights
    minimum_slack = float(min(np.min(lower_slack), np.min(upper_slack)))
    return ConstraintReport(
        "C7 Linking", minimum_slack >= -tolerance, abs(minimum_slack) <= tolerance, minimum_slack
    )


def target_return_floor(
    weights: FloatArray, expected_returns: FloatArray, target: float | None
) -> ConstraintReport:
    if target is None:
        return ConstraintReport("Target return floor", True, False, None, details="Not configured")
    slack = float(expected_returns @ weights) - target
    return ConstraintReport("Target return floor", slack >= -TOLERANCE, abs(slack) <= TOLERANCE, slack)


def check_all_constraints(
    problem: OptimizationInput,
    weights: FloatArray,
    included: FloatArray | None = None,
) -> tuple[ConstraintReport, ...]:
    reports = [
        c1_budget(weights),
        c2_non_negativity(weights),
        c3_max_single_weight(weights, problem.max_single_weight),
        *c4_sector_caps(
            weights,
            problem.sectors,
            problem.sector_caps,
            problem.default_sector_cap,
        ),
        c5_risk_ceiling(weights, problem.covariance, problem.risk_tolerance),
        target_return_floor(weights, problem.expected_returns, problem.target_return),
    ]
    if problem.min_holdings is not None or problem.max_holdings is not None:
        reports.append(c6_cardinality(weights, problem.min_holdings, problem.max_holdings))
        flags = included if included is not None else (weights > TOLERANCE).astype(float)
        reports.append(c7_linking(weights, flags, problem.min_lot_weight, problem.max_single_weight))
    return tuple(reports)


def find_structural_infeasibility(problem: OptimizationInput) -> str | None:
    """Return a concise conflicting-constraint diagnosis before invoking a solver."""

    minimum = problem.min_holdings or 1
    maximum = problem.max_holdings or problem.asset_count
    if minimum > problem.asset_count:
        return "C6 Cardinality: min_holdings exceeds the available universe"
    if minimum > maximum:
        return "C6 Cardinality: min_holdings exceeds max_holdings"
    if maximum * problem.max_single_weight < 1 - TOLERANCE:
        return "C1/C3/C6 conflict: max_holdings * max_single_weight is below 1"
    if problem.asset_count * problem.max_single_weight < 1 - TOLERANCE:
        return "C1/C3 conflict: asset_count * max_single_weight is below 1"
    if minimum * problem.min_lot_weight > 1 + TOLERANCE:
        return "C1/C6/C7 conflict: min_holdings * min_lot_weight exceeds 1"
    sector_capacity = sum(
        min(problem.sector_cap(sector), count * problem.max_single_weight)
        for sector, count in {
            sector: problem.sectors.count(sector) for sector in set(problem.sectors)
        }.items()
    )
    if sector_capacity < 1 - TOLERANCE:
        return "C1/C3/C4 conflict: aggregate sector capacity is below 1"
    return None
