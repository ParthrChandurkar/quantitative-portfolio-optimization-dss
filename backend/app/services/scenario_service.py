"""Owned-snapshot orchestration for Phase 6 scenario simulation."""

from __future__ import annotations

import asyncio
import uuid

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import OptimizationRun, ScenarioRun, User
from app.scenarios.service import run_scenario
from app.schemas.scenarios import ScenarioRunRequest
from app.services.analytics_service import snapshot_holdings
from app.services.portfolio_service import require_owned_snapshot
from app.services.problem_service import problem_from_run


async def run_portfolio_scenario(
    session: AsyncSession,
    user: User,
    portfolio_id: uuid.UUID,
    request: ScenarioRunRequest,
    settings: Settings,
) -> dict:
    snapshot = await require_owned_snapshot(
        session, portfolio_id, request.base_snapshot_id, user.id
    )
    run = await session.get(OptimizationRun, snapshot.optimization_run_id)
    if run is None:
        raise ValueError("snapshot optimization run is missing")
    symbols, _ = await snapshot_holdings(session, snapshot.id)
    context = await problem_from_run(session, settings, run, symbols)
    result = await asyncio.to_thread(
        run_scenario, context.problem, request.scenario_type, request.params
    )
    scenario_row = ScenarioRun(
        base_snapshot_id=snapshot.id,
        resulting_snapshot_id=None,
        scenario_type=request.scenario_type.value,
        shock_parameters=request.params,
    )
    session.add(scenario_row)
    await session.commit()
    await session.refresh(scenario_row)
    return {
        "scenario_run_id": scenario_row.id,
        "scenario_type": result.scenario_type.value,
        "params": result.params,
        "status": result.simulated_result.status.value.casefold(),
        "comparison": jsonable_encoder(result.comparison),
        "explanations": jsonable_encoder(result.explanations),
        "nominal_expected_return": result.nominal_expected_return,
        "inflation_adjusted_expected_return": result.inflation_adjusted_expected_return,
        "weights_unchanged": result.weights_unchanged,
        "pure_scale_change": result.pure_scale_change,
        "lot_feasibility_changed": result.lot_feasibility_changed,
        "scale_change_explanation": result.scale_change_explanation,
        "metadata": result.metadata,
    }
