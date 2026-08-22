"""Deterministic personalized portfolio drift checks."""

from __future__ import annotations

from typing import Protocol

from app.alerts.templates import diversification_drift_message, risk_drift_message
from app.alerts.types import Alert, AlertSeverity, AlertType

# A three-percentage-point buffer prevents alerts for numerical jitter or ordinary
# variation around the profile's optimizer risk ceiling.
VOLATILITY_DRIFT_TOLERANCE = 0.03
# Ten percentage points above the buffered limit represents material rather than
# moderate risk drift and is therefore critical.
CRITICAL_VOLATILITY_EXCESS = 0.10
# These policy references decrease with risk appetite: conservative investors need
# broader diversification, while aggressive profiles permit more concentration.
MIN_DIVERSIFICATION_SCORE = {
    "conservative": 75.0,
    "moderate": 65.0,
    "aggressive": 55.0,
}
CRITICAL_DIVERSIFICATION_DEFICIT = 20.0


class SnapshotLike(Protocol):
    id: object
    expected_volatility: object | None
    diversification_score: object | None


class RiskProfileLike(Protocol):
    predicted_category: str
    recommended_constraints: dict[str, object]


def detect_risk_drift(snapshot: SnapshotLike, profile: RiskProfileLike) -> list[Alert]:
    alerts: list[Alert] = []
    category = profile.predicted_category.casefold()
    target = float(profile.recommended_constraints["risk_tolerance"])
    snapshot_id = snapshot.id

    if snapshot.expected_volatility is not None:
        volatility = float(snapshot.expected_volatility)
        excess = volatility - target
        if excess > VOLATILITY_DRIFT_TOLERANCE:
            grounding = {
                "expected_volatility": volatility,
                "recommended_risk_tolerance": target,
                "profile_category": category,
                "drift_tolerance": VOLATILITY_DRIFT_TOLERANCE,
            }
            alerts.append(
                Alert(
                    AlertType.RISK_DRIFT,
                    AlertSeverity.CRITICAL
                    if excess >= CRITICAL_VOLATILITY_EXCESS
                    else AlertSeverity.WARNING,
                    risk_drift_message(grounding),
                    grounding,
                    snapshot_id=snapshot_id,
                )
            )

    reference_minimum = MIN_DIVERSIFICATION_SCORE.get(category)
    if snapshot.diversification_score is not None and reference_minimum is not None:
        score = float(snapshot.diversification_score)
        deficit = reference_minimum - score
        if deficit > 0:
            grounding = {
                "diversification_score": score,
                "reference_minimum": reference_minimum,
                "profile_category": category,
            }
            alerts.append(
                Alert(
                    AlertType.DIVERSIFICATION_DRIFT,
                    AlertSeverity.CRITICAL
                    if deficit >= CRITICAL_DIVERSIFICATION_DEFICIT
                    else AlertSeverity.WARNING,
                    diversification_drift_message(grounding),
                    grounding,
                    snapshot_id=snapshot_id,
                )
            )
    return alerts
