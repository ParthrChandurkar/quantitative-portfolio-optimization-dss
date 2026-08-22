from types import SimpleNamespace
from uuid import uuid4

from app.alerts.risk_drift_detector import detect_risk_drift
from app.alerts.types import AlertSeverity, AlertType


def profile(category: str = "moderate", risk_tolerance: float = 0.22):
    return SimpleNamespace(
        predicted_category=category,
        recommended_constraints={"risk_tolerance": risk_tolerance},
    )


def test_normal_profile_variation_does_not_alert() -> None:
    snapshot = SimpleNamespace(
        id=uuid4(), expected_volatility=0.24, diversification_score=70.0
    )
    assert detect_risk_drift(snapshot, profile()) == []


def test_clear_volatility_excess_generates_grounded_risk_alert() -> None:
    snapshot = SimpleNamespace(
        id=uuid4(), expected_volatility=0.31, diversification_score=70.0
    )
    alerts = detect_risk_drift(snapshot, profile())
    assert len(alerts) == 1
    assert alerts[0].alert_type is AlertType.RISK_DRIFT
    assert alerts[0].severity is AlertSeverity.WARNING
    assert alerts[0].grounding["expected_volatility"] == 0.31
    assert alerts[0].grounding["recommended_risk_tolerance"] == 0.22


def test_diversification_reference_is_personalized_by_category() -> None:
    snapshot = SimpleNamespace(
        id=uuid4(), expected_volatility=0.30, diversification_score=50.0
    )
    alerts = detect_risk_drift(snapshot, profile("conservative", 0.15))
    assert {alert.alert_type for alert in alerts} == {
        AlertType.RISK_DRIFT,
        AlertType.DIVERSIFICATION_DRIFT,
    }
    assert all(alert.severity is AlertSeverity.CRITICAL for alert in alerts)
