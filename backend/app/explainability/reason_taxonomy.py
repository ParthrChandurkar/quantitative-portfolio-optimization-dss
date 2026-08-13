"""Small deterministic predicates and classifiers for explanation reasons."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PrimaryReason(StrEnum):
    HIGH_RISK_ADJUSTED_RETURN = "high_risk_adjusted_return"
    DIVERSIFICATION_VALUE = "diversification_value"
    CARDINALITY_FLOOR = "cardinality_floor"
    SECTOR_REQUIREMENT = "sector_requirement"
    DOMINATED = "dominated"
    SECTOR_CAP_BINDING = "sector_cap_binding"
    CARDINALITY_EXCLUDED = "cardinality_excluded"
    SINGLE_WEIGHT_CAP_INDIRECT = "single_weight_cap_indirect"


@dataclass(frozen=True, slots=True)
class ReasonEvidence:
    """Normalized facts consumed by independently testable reason predicates."""

    included: bool
    expected_return: float
    return_percentile: float = 0.5
    normalized_risk_share: float = 0.0
    average_correlation: float = 0.0
    forced_by_cardinality_floor: bool = False
    forced_by_sector_requirement: bool = False
    raw_exclusion_diagnostic: str | None = None
    meaningful_position_exceeds_weight_cap: bool = False


def is_sector_requirement(evidence: ReasonEvidence) -> bool:
    return evidence.included and evidence.forced_by_sector_requirement


def is_cardinality_floor(evidence: ReasonEvidence) -> bool:
    return evidence.included and evidence.forced_by_cardinality_floor


def is_diversification_value(evidence: ReasonEvidence) -> bool:
    return (
        evidence.included
        and evidence.average_correlation <= 0.15
        and evidence.return_percentile < 0.75
    )


def is_high_risk_adjusted_return(evidence: ReasonEvidence) -> bool:
    return (
        evidence.included
        and evidence.return_percentile >= 0.60
        and evidence.normalized_risk_share <= 0.35
    )


def is_dominated(evidence: ReasonEvidence) -> bool:
    return not evidence.included and evidence.raw_exclusion_diagnostic == "dominated"


def is_sector_cap_binding(evidence: ReasonEvidence) -> bool:
    return not evidence.included and evidence.raw_exclusion_diagnostic in {
        "sector-cap-blocked",
        "sector_cap_binding",
    }


def is_cardinality_excluded(evidence: ReasonEvidence) -> bool:
    return (
        not evidence.included
        and evidence.raw_exclusion_diagnostic == "cardinality-excluded"
    )


def is_single_weight_cap_indirect(evidence: ReasonEvidence) -> bool:
    return not evidence.included and (
        evidence.raw_exclusion_diagnostic == "single-weight-cap-indirect"
        or evidence.meaningful_position_exceeds_weight_cap
    )


def classify_included(evidence: ReasonEvidence) -> PrimaryReason:
    """Classify an included asset using explicit, stable predicate precedence."""

    if not evidence.included:
        raise ValueError("included classifier requires included evidence")
    predicates = (
        (is_sector_requirement, PrimaryReason.SECTOR_REQUIREMENT),
        (is_cardinality_floor, PrimaryReason.CARDINALITY_FLOOR),
        (is_diversification_value, PrimaryReason.DIVERSIFICATION_VALUE),
        (is_high_risk_adjusted_return, PrimaryReason.HIGH_RISK_ADJUSTED_RETURN),
    )
    for predicate, reason in predicates:
        if predicate(evidence):
            return reason
    return PrimaryReason.HIGH_RISK_ADJUSTED_RETURN


def classify_excluded(evidence: ReasonEvidence) -> PrimaryReason:
    """Classify an excluded asset from solver diagnostics and cap evidence."""

    if evidence.included:
        raise ValueError("excluded classifier requires excluded evidence")
    predicates = (
        (is_dominated, PrimaryReason.DOMINATED),
        (is_sector_cap_binding, PrimaryReason.SECTOR_CAP_BINDING),
        (is_single_weight_cap_indirect, PrimaryReason.SINGLE_WEIGHT_CAP_INDIRECT),
        (is_cardinality_excluded, PrimaryReason.CARDINALITY_EXCLUDED),
    )
    for predicate, reason in predicates:
        if predicate(evidence):
            return reason
    return PrimaryReason.CARDINALITY_EXCLUDED


def classify_reason(evidence: ReasonEvidence) -> PrimaryReason:
    return classify_included(evidence) if evidence.included else classify_excluded(evidence)

