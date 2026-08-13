"""Public deterministic FR-5 explanation-bundle construction service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.explainability.diversification_score import (
    DiversificationScore,
    calculate_diversification_score,
)
from app.explainability.portfolio_summary import build_portfolio_summary
from app.explainability.reason_taxonomy import (
    PrimaryReason,
    ReasonEvidence,
    classify_reason,
)
from app.explainability.shadow_price_insights import (
    ShadowPriceInsight,
    build_shadow_price_insights,
)
from app.explainability.templates import (
    cardinality_excluded,
    cardinality_floor,
    diversification_value,
    dominated,
    high_risk_adjusted_return,
    sector_cap_binding,
    sector_requirement,
    single_weight_cap_indirect,
)
from app.optimization.types import OptimizationResult


@dataclass(frozen=True, slots=True)
class ExplanationItem:
    """Matches Phase 2 ``explanation_items`` and Phase 3 rationale display fields."""

    symbol: str
    decision: str
    primary_reason: PrimaryReason
    marginal_return_contribution: float
    marginal_risk_contribution: float
    binding_constraint: str | None
    narrative_text: str
    rationale: str
    model_score: int


@dataclass(frozen=True, slots=True)
class ExplainabilityBundle:
    summary: str
    included: tuple[ExplanationItem, ...]
    notable_exclusions: tuple[ExplanationItem, ...]
    constraint_insights: tuple[ShadowPriceInsight, ...]
    diversification: DiversificationScore


def _required_context(result: OptimizationResult) -> dict[str, Any]:
    context = result.metadata.get("explainability_context")
    if not isinstance(context, dict):
        raise TypeError("optimization result lacks explainability_context metadata")
    required = {"symbols", "expected_returns", "covariance", "sectors", "max_single_weight"}
    missing = sorted(required - context.keys())
    if missing:
        raise ValueError(f"explainability_context is missing: {', '.join(missing)}")
    return context


def _percentiles(values: np.ndarray) -> np.ndarray:
    order = np.argsort(np.argsort(values, kind="stable"), kind="stable")
    denominator = max(len(values) - 1, 1)
    return order.astype(float) / denominator


def _average_correlations(covariance: np.ndarray) -> np.ndarray:
    volatility = np.sqrt(np.clip(np.diag(covariance), 0, None))
    denominator = np.outer(volatility, volatility)
    correlation = np.divide(
        covariance,
        denominator,
        out=np.zeros_like(covariance),
        where=denominator > 1e-15,
    )
    if len(correlation) == 1:
        return np.zeros(1)
    return (np.sum(correlation, axis=1) - np.diag(correlation)) / (len(correlation) - 1)


def _dominant_index(index: int, weights: np.ndarray, returns: np.ndarray) -> int | None:
    candidates = np.flatnonzero((weights > 1e-6) & (returns >= returns[index]))
    if candidates.size == 0:
        candidates = np.flatnonzero(weights > 1e-6)
    return int(candidates[np.argmax(weights[candidates])]) if candidates.size else None


def _binding_constraint(symbol: str, sector: str, result: OptimizationResult) -> str | None:
    for report in result.constraint_reports:
        if report.is_binding and (sector in report.constraint_name or symbol in report.constraint_name):
            return report.constraint_name
    return None


def _narrative(
    reason: PrimaryReason,
    symbol: str,
    index: int,
    context: dict[str, Any],
    weights: np.ndarray,
    returns: np.ndarray,
    risk_share: float,
) -> str:
    sectors = tuple(context["sectors"])
    sector = sectors[index]
    if reason is PrimaryReason.HIGH_RISK_ADJUSTED_RETURN:
        return high_risk_adjusted_return(symbol, float(returns[index]), -risk_share)
    if reason is PrimaryReason.DIVERSIFICATION_VALUE:
        return diversification_value(symbol, float(returns[index]), -risk_share)
    if reason is PrimaryReason.CARDINALITY_FLOOR:
        return cardinality_floor(symbol, int(context.get("min_holdings") or 1))
    if reason is PrimaryReason.SECTOR_REQUIREMENT:
        return sector_requirement(symbol, sector)
    if reason is PrimaryReason.DOMINATED:
        dominant_index = _dominant_index(index, weights, returns)
        dominant = context["symbols"][dominant_index] if dominant_index is not None else "another candidate"
        return dominated(symbol, str(dominant))
    if reason is PrimaryReason.SECTOR_CAP_BINDING:
        occupants = tuple(
            context["symbols"][i]
            for i in range(len(weights))
            if weights[i] > 1e-6 and sectors[i] == sector
        )
        cap = float(context.get("sector_caps", {}).get(sector, context.get("default_sector_cap", 0.35)))
        return sector_cap_binding(symbol, sector, cap, occupants)
    if reason is PrimaryReason.SINGLE_WEIGHT_CAP_INDIRECT:
        return single_weight_cap_indirect(symbol, float(context["max_single_weight"]))
    return cardinality_excluded(symbol, int(context.get("max_holdings") or len(weights)))


def build_explanations(result: OptimizationResult) -> ExplainabilityBundle:
    """Convert one feasible engine result into structured, repeatable explanations."""

    if not result.is_feasible or result.explanation_hooks is None:
        raise ValueError("explanations require a feasible result with explanation hooks")
    context = _required_context(result)
    symbols = tuple(str(value) for value in context["symbols"])
    sectors = tuple(str(value) for value in context["sectors"])
    returns = np.asarray(context["expected_returns"], dtype=float)
    covariance = np.asarray(context["covariance"], dtype=float)
    weights = result.weight_vector(symbols)
    return_percentiles = _percentiles(returns)
    correlations = _average_correlations(covariance)
    hooks = result.explanation_hooks
    forced_floor = set(context.get("cardinality_floor_symbols", ()))
    forced_sectors = set(context.get("sector_requirement_symbols", ()))
    items: list[ExplanationItem] = []
    for index, symbol in enumerate(symbols):
        included = weights[index] > 1e-6
        diagnostic = hooks.excluded_stock_diagnostics.get(symbol)
        evidence = ReasonEvidence(
            included=included,
            expected_return=float(returns[index]),
            return_percentile=float(return_percentiles[index]),
            normalized_risk_share=float(hooks.normalized_risk_shares.get(symbol, 0.0)),
            average_correlation=float(correlations[index]),
            forced_by_cardinality_floor=symbol in forced_floor,
            forced_by_sector_requirement=symbol in forced_sectors,
            raw_exclusion_diagnostic=diagnostic,
            meaningful_position_exceeds_weight_cap=diagnostic == "single-weight-cap-indirect",
        )
        reason = classify_reason(evidence)
        narrative = _narrative(
            reason,
            symbol,
            index,
            context,
            weights,
            returns,
            evidence.normalized_risk_share,
        )
        score = round(
            100
            * max(
                0.0,
                min(
                    1.0,
                    0.6 * evidence.return_percentile
                    + 0.4 * (1 - evidence.normalized_risk_share),
                ),
            )
        )
        items.append(
            ExplanationItem(
                symbol=symbol,
                decision="included" if included else "excluded",
                primary_reason=reason,
                marginal_return_contribution=float(
                    hooks.marginal_return_contributions.get(symbol, 0.0)
                ),
                marginal_risk_contribution=float(
                    hooks.marginal_risk_contributions.get(symbol, 0.0)
                ),
                binding_constraint=_binding_constraint(symbol, sectors[index], result),
                narrative_text=narrative,
                rationale=narrative,
                model_score=score,
            )
        )
    included_items = tuple(item for item in items if item.decision == "included")
    excluded_items = tuple(item for item in items if item.decision == "excluded")
    diversification = calculate_diversification_score(weights, sectors)
    if result.expected_return is None or result.expected_volatility is None:
        raise ValueError("feasible result is missing risk-return metrics")
    summary = build_portfolio_summary(
        result.expected_return,
        result.expected_volatility,
        result.weights,
        dict(zip(symbols, sectors, strict=True)),
    )
    shadow_prices = {
        str(key): float(value)
        for key, value in result.metadata.get("shadow_prices", {}).items()
    }
    return ExplainabilityBundle(
        summary,
        included_items,
        excluded_items,
        build_shadow_price_insights(result.constraint_reports, shadow_prices),
        diversification,
    )
