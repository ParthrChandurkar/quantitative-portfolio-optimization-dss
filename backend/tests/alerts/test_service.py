from decimal import Decimal

from sqlalchemy import func, select

from app.alerts.service import check_alerts
from app.db.models import (
    Alert,
    OptimizationRun,
    Portfolio,
    PortfolioSnapshot,
    User,
    UserRiskProfile,
)


async def seeded_context(session, *, snapshots: int = 2):
    user = User(email="alert@example.com", password_hash="hash", full_name="Alert User")
    portfolio = Portfolio(user=user, name="Alert Portfolio")
    profile = UserRiskProfile(
        user=user,
        questionnaire_answers={"source": "test"},
        predicted_category="moderate",
        category_confidence=Decimal("0.95"),
        recommended_constraints={"risk_tolerance": 0.22},
    )
    session.add_all([user, portfolio, profile])
    for index in range(snapshots):
        run = OptimizationRun(
            portfolio=portfolio,
            solver_used="SciPy",
            budget=Decimal(100000),
            max_single_weight=Decimal("0.20"),
            min_holdings=1,
            sector_constraints={},
            status="solved",
        )
        session.add(
            PortfolioSnapshot(
                portfolio=portfolio,
                optimization_run=run,
                label=f"Snapshot {index}",
                expected_volatility=Decimal("0.31"),
                diversification_score=Decimal(70),
                is_baseline=index == 0,
            )
        )
    await session.commit()
    return user, portfolio


async def test_first_snapshot_is_baseline_and_never_alerts(session) -> None:
    user, portfolio = await seeded_context(session, snapshots=1)
    assert await check_alerts(session, user.id, portfolio.id) == []
    assert await session.scalar(select(func.count()).select_from(Alert)) == 0


async def test_repeated_check_deduplicates_unacknowledged_condition(session) -> None:
    user, portfolio = await seeded_context(session)
    first = await check_alerts(session, user.id, portfolio.id)
    second = await check_alerts(session, user.id, portfolio.id)
    assert len(first) == len(second) == 1
    assert first[0].id == second[0].id
    assert await session.scalar(select(func.count()).select_from(Alert)) == 1
