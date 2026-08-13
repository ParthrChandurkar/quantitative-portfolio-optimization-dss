from __future__ import annotations

from dataclasses import replace

import numpy as np

from app.optimization.ortools_solver import select_support, solve_ortools
from app.optimization.types import OptimizationStatus, SolverName


def test_cp_sat_selects_requested_top_k_support(golden_problem) -> None:
    problem = replace(golden_problem, min_holdings=3, max_holdings=3)
    support = select_support(problem, np.asarray([0.10, 0.30, 0.25, 0.05, 0.30]))
    assert set(support) == {1, 2, 4}


def test_two_stage_ortools_returns_restricted_feasible_qp(golden_problem) -> None:
    problem = replace(golden_problem, min_holdings=4, max_holdings=4, solver=SolverName.ORTOOLS)
    result = solve_ortools(problem)
    assert result.status is OptimizationStatus.OPTIMAL
    assert result.solver_used is SolverName.ORTOOLS
    assert len(result.metadata["support"]) == 4
    assert np.count_nonzero(result.weight_vector(problem.symbols) > 1e-6) == 4
    assert all(report.is_satisfied for report in result.constraint_reports)

