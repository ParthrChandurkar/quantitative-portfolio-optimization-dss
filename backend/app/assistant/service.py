"""Authenticated orchestration for the offline grounded portfolio assistant."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import answer_templates
from app.assistant.answer_templates import GroundingItem
from app.assistant.intents import AssistantIntent
from app.assistant.slot_extraction import extract_slots
from app.assistant.train_intent_classifier import classify_intent
from app.core.config import Settings
from app.db.models import (
    AssistantQueryLog,
    ExplanationItem,
    PortfolioHolding,
    PortfolioSnapshot,
    Sector,
    Stock,
    User,
)
from app.explainability.diversification_score import calculate_diversification_score
from app.explainability.portfolio_summary import build_portfolio_summary
from app.schemas.scenarios import ScenarioRunRequest
from app.services import analytics_service, scenario_service
from app.services.portfolio_service import (
    latest_snapshot,
    require_owned_portfolio,
    require_owned_snapshot,
)

DEFAULT_CONFIDENCE_THRESHOLD = 0.55


@dataclass(frozen=True, slots=True)
class AssistantAnswer:
    answer: str
    intent: AssistantIntent
    confidence: float
    grounding: tuple[GroundingItem, ...]
    is_fallback: bool

    def payload(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "intent": self.intent.value,
            "confidence": self.confidence,
            "grounding": [asdict(item) for item in self.grounding],
            "is_fallback": self.is_fallback,
        }


async def _universe(session: AsyncSession) -> tuple[tuple[str, ...], tuple[str, ...]]:
    rows = (
        await session.execute(
            select(Stock.symbol, Sector.name)
            .join(Sector, Stock.sector_id == Sector.id)
            .order_by(Stock.symbol)
        )
    ).all()
    return tuple(row[0] for row in rows), tuple(sorted({row[1] for row in rows}))


async def _holding_sources(
    session: AsyncSession, snapshot: PortfolioSnapshot
) -> tuple[dict[str, float], dict[str, str]]:
    rows = (
        await session.execute(
            select(Stock.symbol, Sector.name, PortfolioHolding.weight)
            .join(PortfolioHolding, PortfolioHolding.stock_id == Stock.id)
            .join(Sector, Stock.sector_id == Sector.id)
            .where(PortfolioHolding.snapshot_id == snapshot.id)
            .order_by(Stock.symbol)
        )
    ).all()
    return (
        {symbol: float(weight) for symbol, _, weight in rows},
        {symbol: sector for symbol, sector, _ in rows},
    )


async def _stock_narrative(
    session: AsyncSession,
    snapshot: PortfolioSnapshot,
    symbol: str,
    *,
    included: bool,
) -> str | None:
    statement = (
        select(ExplanationItem.narrative_text)
        .join(Stock, ExplanationItem.stock_id == Stock.id)
        .where(
            ExplanationItem.optimization_run_id == snapshot.optimization_run_id,
            Stock.symbol == symbol,
        )
    )
    if included:
        statement = statement.where(ExplanationItem.decision != "excluded")
    else:
        statement = statement.where(ExplanationItem.decision == "excluded")
    return await session.scalar(statement)


async def answer_question(
    session: AsyncSession,
    user: User,
    settings: Settings,
    portfolio_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    question_text: str,
    *,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> AssistantAnswer:
    snapshot = await require_owned_snapshot(session, portfolio_id, snapshot_id, user.id)
    prediction = classify_intent(question_text)
    if (
        prediction.confidence < confidence_threshold
        or prediction.intent is AssistantIntent.UNKNOWN
    ):
        fallback = answer_templates.unknown_fallback()
        return AssistantAnswer(
            fallback.answer,
            AssistantIntent.UNKNOWN,
            prediction.confidence,
            fallback.grounding,
            True,
        )

    universe, sectors = await _universe(session)
    slots = extract_slots(
        question_text,
        universe,
        sectors,
        include_shock=prediction.intent is AssistantIntent.HYPOTHETICAL_SHOCK,
    )
    template = None
    if prediction.intent in {
        AssistantIntent.EXPLAIN_STOCK_INCLUSION,
        AssistantIntent.EXPLAIN_STOCK_EXCLUSION,
    }:
        included = prediction.intent is AssistantIntent.EXPLAIN_STOCK_INCLUSION
        if slots.stock_symbol is not None:
            narrative = await _stock_narrative(
                session, snapshot, slots.stock_symbol, included=included
            )
            if narrative is not None:
                template = answer_templates.stock_explanation(
                    slots.stock_symbol, narrative, included=included
                )
    elif prediction.intent is AssistantIntent.PORTFOLIO_RISK_SUMMARY:
        analytics = await analytics_service.get_snapshot_analytics(
            session, user, portfolio_id, snapshot_id, settings
        )
        weights, sector_map = await _holding_sources(session, snapshot)
        summary = None
        if (
            snapshot.expected_return is not None
            and snapshot.expected_volatility is not None
        ):
            summary = build_portfolio_summary(
                float(snapshot.expected_return),
                float(snapshot.expected_volatility),
                weights,
                sector_map,
            )
        template = answer_templates.portfolio_risk_summary(
            analytics["risk_metrics"], summary
        )
    elif prediction.intent is AssistantIntent.ALLOCATION_RATIONALE:
        weights, sector_map = await _holding_sources(session, snapshot)
        if (
            snapshot.expected_return is not None
            and snapshot.expected_volatility is not None
        ):
            summary = build_portfolio_summary(
                float(snapshot.expected_return),
                float(snapshot.expected_volatility),
                weights,
                sector_map,
            )
            template = answer_templates.allocation_rationale(summary)
    elif prediction.intent is AssistantIntent.DIVERSIFICATION_QUESTION:
        weights, sector_map = await _holding_sources(session, snapshot)
        ordered = tuple(weights)
        score = calculate_diversification_score(
            np.asarray([weights[symbol] for symbol in ordered], dtype=float),
            tuple(sector_map[symbol] for symbol in ordered),
        )
        template = answer_templates.diversification_question(asdict(score))
    elif prediction.intent is AssistantIntent.HYPOTHETICAL_SHOCK:
        assert slots.scenario_type is not None
        scenario = await scenario_service.run_portfolio_scenario(
            session,
            user,
            portfolio_id,
            ScenarioRunRequest(
                base_snapshot_id=snapshot_id,
                scenario_type=slots.scenario_type,
                params=slots.scenario_params,
            ),
            settings,
        )
        if scenario["comparison"] is not None:
            template = answer_templates.hypothetical_shock(
                scenario["scenario_type"], scenario["comparison"]
            )
    if template is None:
        template = answer_templates.unknown_fallback()
        return AssistantAnswer(
            template.answer,
            AssistantIntent.UNKNOWN,
            prediction.confidence,
            template.grounding,
            True,
        )
    return AssistantAnswer(
        template.answer,
        prediction.intent,
        prediction.confidence,
        template.grounding,
        template.is_fallback,
    )


async def answer_latest_question(
    session: AsyncSession,
    user: User,
    settings: Settings,
    portfolio_id: uuid.UUID,
    question_text: str,
) -> AssistantAnswer:
    await require_owned_portfolio(session, portfolio_id, user.id)
    snapshot = await latest_snapshot(session, portfolio_id)
    if snapshot is None:
        raise ValueError("assistant requires a solved portfolio snapshot")
    answer = await answer_question(
        session, user, settings, portfolio_id, snapshot.id, question_text
    )
    session.add(
        AssistantQueryLog(
            user_id=user.id,
            portfolio_id=portfolio_id,
            question_text=question_text,
            classified_intent=answer.intent.value,
            confidence=Decimal(str(answer.confidence)),
            answer_text=answer.answer,
        )
    )
    await session.commit()
    return answer
