"""Turn material binding-constraint duals into deterministic counterfactual insights."""

from __future__ import annotations

from dataclasses import dataclass

from app.optimization.types import ConstraintReport


@dataclass(frozen=True, slots=True)
class ShadowPriceInsight:
    constraint_name: str
    shadow_price: float
    assumed_relaxation: float
    projected_objective_change: float
    narrative: str


def _display_name(constraint_name: str) -> str:
    name = constraint_name.replace("C4_SectorCap_", "").replace("C4 Sector cap: ", "")
    return name.replace("_", " ")


def _future_action(constraint_name: str, delta: float) -> str:
    display = _display_name(constraint_name)
    if "SectorCap" in constraint_name or "Sector cap" in constraint_name:
        return f"relaxing your {display} sector cap by {delta:.0%}"
    if "MaxWeight" in constraint_name or "single-stock" in constraint_name:
        return f"raising the single-stock cap by {delta:.0%}"
    if "TargetReturn" in constraint_name or "return floor" in constraint_name:
        return f"lowering the target-return floor by {delta:.0%}"
    return f"relaxing {display} by {delta:.0%}"


def _shadow_price(
    report: ConstraintReport, lookup: dict[str, float]
) -> float | None:
    if report.shadow_price is not None:
        return report.shadow_price
    candidates = [report.constraint_name]
    if report.constraint_name.startswith("C4 Sector cap: "):
        sector = report.constraint_name.removeprefix("C4 Sector cap: ")
        candidates.append(f"C4_SectorCap_{sector}")
    elif report.constraint_name == "C3 Max single-stock weight":
        candidates.extend(key for key in lookup if key.startswith("C3_MaxWeight_"))
    elif report.constraint_name == "Target return floor":
        candidates.append("TargetReturnFloor")
    values = [lookup[key] for key in candidates if key in lookup]
    if not values:
        return None
    return max(values, key=abs)


def build_shadow_price_insights(
    reports: tuple[ConstraintReport, ...],
    shadow_prices: dict[str, float] | None = None,
    *,
    materiality_threshold: float = 1e-4,
    relaxation_delta: float = 0.05,
) -> tuple[ShadowPriceInsight, ...]:
    """Report material binding dual values and an exact linear sensitivity estimate."""

    lookup = shadow_prices or {}
    insights: list[ShadowPriceInsight] = []
    for report in reports:
        price = _shadow_price(report, lookup)
        if not report.is_binding or price is None or abs(price) < materiality_threshold:
            continue
        projected = price * relaxation_delta
        action = _future_action(report.constraint_name, relaxation_delta)
        narrative = (
            f"Based on the local solver sensitivity, {action} would be expected to change "
            f"the objective by approximately {projected:.6f} ({price:.6f} × {relaxation_delta:.2f})."
        )
        insights.append(
            ShadowPriceInsight(
                report.constraint_name,
                price,
                relaxation_delta,
                projected,
                narrative,
            )
        )
    return tuple(insights)
