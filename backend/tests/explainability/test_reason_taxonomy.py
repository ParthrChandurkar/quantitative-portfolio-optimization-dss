from __future__ import annotations

import pytest

from app.explainability.reason_taxonomy import (
    PrimaryReason,
    ReasonEvidence,
    classify_excluded,
    classify_included,
    classify_reason,
    is_cardinality_excluded,
    is_cardinality_floor,
    is_diversification_value,
    is_dominated,
    is_high_risk_adjusted_return,
    is_sector_cap_binding,
    is_sector_requirement,
    is_single_weight_cap_indirect,
)


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        (
            ReasonEvidence(True, 0.18, 0.9, 0.15, 0.4),
            PrimaryReason.HIGH_RISK_ADJUSTED_RETURN,
        ),
        (
            ReasonEvidence(True, 0.13, 0.5, 0.20, -0.10),
            PrimaryReason.DIVERSIFICATION_VALUE,
        ),
        (
            ReasonEvidence(True, 0.10, forced_by_cardinality_floor=True),
            PrimaryReason.CARDINALITY_FLOOR,
        ),
        (
            ReasonEvidence(True, 0.10, forced_by_sector_requirement=True),
            PrimaryReason.SECTOR_REQUIREMENT,
        ),
        (
            ReasonEvidence(False, 0.10, raw_exclusion_diagnostic="dominated"),
            PrimaryReason.DOMINATED,
        ),
        (
            ReasonEvidence(False, 0.16, raw_exclusion_diagnostic="sector-cap-blocked"),
            PrimaryReason.SECTOR_CAP_BINDING,
        ),
        (
            ReasonEvidence(False, 0.15, raw_exclusion_diagnostic="cardinality-excluded"),
            PrimaryReason.CARDINALITY_EXCLUDED,
        ),
        (
            ReasonEvidence(False, 0.15, meaningful_position_exceeds_weight_cap=True),
            PrimaryReason.SINGLE_WEIGHT_CAP_INDIRECT,
        ),
    ],
)
def test_each_reason_category_is_classified_exactly(
    evidence: ReasonEvidence, expected: PrimaryReason
) -> None:
    assert classify_reason(evidence) is expected


def test_predicates_are_independently_callable() -> None:
    included = ReasonEvidence(True, 0.15, 0.8, 0.1, 0.3)
    excluded = ReasonEvidence(False, 0.10, raw_exclusion_diagnostic="dominated")
    assert is_high_risk_adjusted_return(included)
    assert not is_diversification_value(included)
    assert not is_cardinality_floor(included)
    assert not is_sector_requirement(included)
    assert is_dominated(excluded)
    assert not is_sector_cap_binding(excluded)
    assert not is_cardinality_excluded(excluded)
    assert not is_single_weight_cap_indirect(excluded)


def test_wrong_decision_classifier_is_rejected() -> None:
    with pytest.raises(ValueError, match="included evidence"):
        classify_included(ReasonEvidence(False, 0.1))
    with pytest.raises(ValueError, match="excluded evidence"):
        classify_excluded(ReasonEvidence(True, 0.1))


def test_unmatched_evidence_has_deterministic_fallbacks() -> None:
    assert classify_included(ReasonEvidence(True, 0.1, average_correlation=0.8)) is PrimaryReason.HIGH_RISK_ADJUSTED_RETURN
    assert classify_excluded(ReasonEvidence(False, 0.1)) is PrimaryReason.CARDINALITY_EXCLUDED

