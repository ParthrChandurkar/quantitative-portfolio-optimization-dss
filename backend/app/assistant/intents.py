from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssistantIntent(StrEnum):
    EXPLAIN_STOCK_INCLUSION = "EXPLAIN_STOCK_INCLUSION"
    EXPLAIN_STOCK_EXCLUSION = "EXPLAIN_STOCK_EXCLUSION"
    PORTFOLIO_RISK_SUMMARY = "PORTFOLIO_RISK_SUMMARY"
    ALLOCATION_RATIONALE = "ALLOCATION_RATIONALE"
    HYPOTHETICAL_SHOCK = "HYPOTHETICAL_SHOCK"
    DIVERSIFICATION_QUESTION = "DIVERSIFICATION_QUESTION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class IntentPrediction:
    intent: AssistantIntent
    confidence: float
    probabilities: dict[str, float]
