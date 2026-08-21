"""Compare historical-mean and ML mu on the established 2025 OOS split.

Run from ``backend`` with::

    python -m scripts.compare_return_estimation_methods
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from app.analytics.backtest import BacktestMode, RebalanceFrequency, run_backtest
from app.analytics.risk_metrics import (
    maximum_drawdown,
    realized_annualized_return,
    realized_annualized_volatility,
    sharpe_ratio,
)
from app.core.config import Settings
from app.db.models import OptimizationRun
from app.db.session import AsyncSessionFactory
from app.ml.train_forecast_model import train_forecast_model
from app.optimization.engine import solve
from app.services.problem_service import problem_from_run

SPLIT_DATE = date(2025, 1, 30)
EVALUATION_END_DATE = date(2026, 1, 30)
MODEL_CUTOFF = SPLIT_DATE - timedelta(days=1)
BUDGET_INR = 1_000_000.0


def _weights(result) -> dict[str, float]:
    return {
        symbol: float(weight)
        for symbol, weight in result.weights.items()
        if weight > 1e-6
    }


def _metrics(backtest) -> dict[str, float]:
    annual_return = realized_annualized_return(backtest.returns)
    volatility = realized_annualized_volatility(backtest.returns)
    return {
        "annualized_return": annual_return,
        "sharpe_ratio": sharpe_ratio(annual_return, 0.0, volatility),
        "max_drawdown": maximum_drawdown(backtest.values),
        "annualized_volatility": volatility,
        "final_value_inr": float(backtest.values[-1]),
    }


async def compare(*, artifact_dir: Path | None = None) -> dict[str, object]:
    settings = Settings()
    async with AsyncSessionFactory() as session:
        base_run = await session.scalar(
            select(OptimizationRun)
            .where(OptimizationRun.status == "solved")
            .order_by(OptimizationRun.run_at.desc())
            .limit(1)
        )
        if base_run is None:
            raise RuntimeError("comparison requires an existing solved optimization run")
        train_kwargs = {} if artifact_dir is None else {"artifact_dir": artifact_dir}
        training = await train_forecast_model(
            session,
            MODEL_CUTOFF,
            forward_days=21,
            **train_kwargs,
        )
        methods: dict[str, object] = {}
        audits: dict[str, object] = {}
        for method in ("historical_mean", "ml_forecast"):
            context = await problem_from_run(
                session,
                settings,
                base_run,
                symbols=None,
                as_of_date=SPLIT_DATE - timedelta(days=1),
                lookback_days=252,
                return_estimation_method=method,
            )
            result = await asyncio.to_thread(solve, context.problem)
            if not result.is_feasible:
                raise RuntimeError(f"{method} solve failed: {result.message}")
            backtest = await run_backtest(
                session,
                result.weights,
                BUDGET_INR,
                SPLIT_DATE,
                EVALUATION_END_DATE,
                BacktestMode.PERIODIC_REBALANCE,
                RebalanceFrequency.MONTHLY,
                estimation_end_date=SPLIT_DATE,
                estimation_dates=context.estimation_dates,
            )
            methods[method] = {
                **_metrics(backtest),
                "holdings": _weights(result),
                "fit_expected_return": result.expected_return,
                "fit_volatility": result.expected_volatility,
            }
            audits[method] = {
                "estimation_start": min(context.estimation_dates).isoformat(),
                "estimation_end": max(context.estimation_dates).isoformat(),
                "evaluation_start": backtest.points[0].trade_date.isoformat(),
                "evaluation_end": backtest.points[-1].trade_date.isoformat(),
                "overlap_count": len(
                    set(context.estimation_dates).intersection(
                        point.trade_date for point in backtest.points
                    )
                ),
            }
        return {
            "model": {
                "artifact": str(training.artifact_path),
                "exclusive_training_cutoff": MODEL_CUTOFF.isoformat(),
                "training_rows": training.training_row_count,
                "forward_days": training.forward_days,
                "feature_importances": training.feature_importances,
            },
            "methodology": {
                "evaluation_start": SPLIT_DATE.isoformat(),
                "evaluation_end": EVALUATION_END_DATE.isoformat(),
                "rebalance_frequency": "monthly",
                "budget_inr": BUDGET_INR,
                "audits": audits,
            },
            "results": methods,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    payload = asyncio.run(compare())
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    if arguments.output is not None:
        arguments.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
