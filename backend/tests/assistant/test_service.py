from dataclasses import asdict, replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.encoders import jsonable_encoder

from app.assistant.intents import AssistantIntent, IntentPrediction
from app.assistant.service import answer_question
from app.core.config import Settings
from app.scenarios.service import run_scenario


async def test_market_crash_answer_matches_real_scenario_service_call(
    monkeypatch, golden_problem
) -> None:
    snapshot = SimpleNamespace(id=uuid4(), optimization_run_id=uuid4())

    async def owned(*_args):
        return snapshot

    async def universe(_session):
        return golden_problem.symbols, tuple(set(golden_problem.sectors))

    recorded = {}

    async def real_scenario(_session, _user, _portfolio_id, request, _settings):
        feasible_problem = replace(
            golden_problem, target_return=None, risk_tolerance=0.50
        )
        params = {**request.params, "betas": [1.0] * feasible_problem.asset_count}
        result = run_scenario(feasible_problem, request.scenario_type, params)
        comparison = jsonable_encoder(asdict(result.comparison))
        recorded["comparison"] = comparison
        recorded["params"] = request.params
        return {"scenario_type": result.scenario_type.value, "comparison": comparison}

    monkeypatch.setattr("app.assistant.service.require_owned_snapshot", owned)
    monkeypatch.setattr("app.assistant.service._universe", universe)
    monkeypatch.setattr(
        "app.assistant.service.classify_intent",
        lambda _question: IntentPrediction(
            AssistantIntent.HYPOTHETICAL_SHOCK, 0.99, {}
        ),
    )
    monkeypatch.setattr(
        "app.assistant.service.scenario_service.run_portfolio_scenario", real_scenario
    )

    answer = await answer_question(
        object(),
        SimpleNamespace(id=uuid4()),
        Settings(),
        uuid4(),
        snapshot.id,
        "what if the market crashes by 20%",
    )
    assert recorded["params"] == {"delta": -0.2, "kappa_vol": 0.5}
    assert answer.intent is AssistantIntent.HYPOTHETICAL_SHOCK
    for value in recorded["comparison"].values():
        if isinstance(value, float):
            assert str(value) in answer.answer


async def test_low_confidence_returns_unknown_without_loading_sources(
    monkeypatch,
) -> None:
    async def owned(*_args):
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr("app.assistant.service.require_owned_snapshot", owned)
    monkeypatch.setattr(
        "app.assistant.service.classify_intent",
        lambda _question: IntentPrediction(
            AssistantIntent.PORTFOLIO_RISK_SUMMARY, 0.2, {}
        ),
    )
    result = await answer_question(
        object(),
        SimpleNamespace(id=uuid4()),
        Settings(),
        uuid4(),
        uuid4(),
        "ambiguous words",
    )
    assert result.intent is AssistantIntent.UNKNOWN
    assert result.is_fallback is True


@pytest.mark.parametrize(
    "intent",
    [
        AssistantIntent.EXPLAIN_STOCK_INCLUSION,
        AssistantIntent.EXPLAIN_STOCK_EXCLUSION,
        AssistantIntent.PORTFOLIO_RISK_SUMMARY,
        AssistantIntent.ALLOCATION_RATIONALE,
        AssistantIntent.DIVERSIFICATION_QUESTION,
    ],
)
async def test_non_scenario_intents_dispatch_to_grounded_sources(
    monkeypatch, intent
) -> None:
    snapshot = SimpleNamespace(
        id=uuid4(),
        optimization_run_id=uuid4(),
        expected_return=0.16,
        expected_volatility=0.20,
    )

    async def owned(*_args):
        return snapshot

    async def universe(_session):
        return ("TCS", "INFY"), ("IT",)

    async def narrative(*_args, **_kwargs):
        return "Stored explanation 0.16."

    async def holdings(*_args):
        return {"TCS": 0.6, "INFY": 0.4}, {"TCS": "IT", "INFY": "IT"}

    async def analytics(*_args, **_kwargs):
        return {
            "risk_metrics": {
                "realized_annualized_return": 0.1,
                "realized_annualized_volatility": 0.2,
                "max_drawdown": -0.08,
                "realized_sharpe_ratio": 0.5,
            }
        }

    monkeypatch.setattr("app.assistant.service.require_owned_snapshot", owned)
    monkeypatch.setattr("app.assistant.service._universe", universe)
    monkeypatch.setattr("app.assistant.service._stock_narrative", narrative)
    monkeypatch.setattr("app.assistant.service._holding_sources", holdings)
    monkeypatch.setattr(
        "app.assistant.service.analytics_service.get_snapshot_analytics", analytics
    )
    monkeypatch.setattr(
        "app.assistant.service.classify_intent",
        lambda _question: IntentPrediction(intent, 0.95, {}),
    )
    question = (
        "why is TCS included"
        if intent is AssistantIntent.EXPLAIN_STOCK_INCLUSION
        else "why is TCS excluded"
        if intent is AssistantIntent.EXPLAIN_STOCK_EXCLUSION
        else "portfolio question"
    )
    result = await answer_question(
        object(),
        SimpleNamespace(id=uuid4()),
        Settings(),
        uuid4(),
        snapshot.id,
        question,
    )
    assert result.intent is intent
    assert result.grounding
    assert result.is_fallback is False
