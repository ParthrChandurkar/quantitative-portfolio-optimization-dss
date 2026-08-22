import re
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.alerts.risk_drift_detector import detect_risk_drift
from app.alerts.templates import stock_anomaly_message
from app.alerts.types import Alert, AlertSeverity, AlertType

NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def numbers(value: Any) -> list[float]:
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        return [float(match) for match in NUMBER.findall(value)]
    if isinstance(value, dict):
        return [number for item in value.values() for number in numbers(item)]
    if isinstance(value, (list, tuple)):
        return [number for item in value for number in numbers(item)]
    return []


def assert_numeric_message_is_grounded(alert: Alert) -> None:
    grounded = numbers(alert.grounding)
    for number in numbers(alert.message):
        assert any(number == source for source in grounded), (
            number,
            alert.message,
            grounded,
        )


def test_every_numeric_alert_value_is_present_in_its_grounding() -> None:
    snapshot = SimpleNamespace(
        id=uuid4(), expected_volatility=0.42, diversification_score=40.0
    )
    profile = SimpleNamespace(
        predicted_category="moderate",
        recommended_constraints={"risk_tolerance": 0.22},
    )
    alerts = detect_risk_drift(snapshot, profile)
    anomaly_grounding = {"symbol": "TCS", "anomaly_score": 0.1842}
    alerts.append(
        Alert(
            AlertType.STOCK_ANOMALY,
            AlertSeverity.WARNING,
            stock_anomaly_message(anomaly_grounding),
            anomaly_grounding,
            stock_id=uuid4(),
        )
    )
    assert {alert.alert_type for alert in alerts} == set(AlertType)
    for alert in alerts:
        assert_numeric_message_is_grounded(alert)
