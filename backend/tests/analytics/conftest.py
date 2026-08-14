from __future__ import annotations

import numpy as np
import pytest

from app.optimization.types import OptimizationInput, SolverName


@pytest.fixture
def analytics_universe() -> OptimizationInput:
    return OptimizationInput(
        symbols=("A", "B", "C", "D"),
        expected_returns=np.asarray([0.06, 0.10, 0.14, 0.18]),
        covariance=np.diag([0.01, 0.0144, 0.0225, 0.0324]),
        sectors=("Banking", "IT", "Energy", "FMCG"),
        budget=100_000.0,
        target_return=0.10,
        max_single_weight=0.60,
        sector_caps={"Banking": 0.60, "IT": 0.60, "Energy": 0.60, "FMCG": 0.60},
        default_sector_cap=0.60,
        solver=SolverName.SCIPY,
        risk_free_rate=0.04,
    )
