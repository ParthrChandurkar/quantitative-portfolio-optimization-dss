from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from app.optimization.engine import select_solver, solve
from app.optimization.types import OptimizationResult, OptimizationStatus, SolverName


def stub_result(solver: SolverName, symbols: tuple[str, ...]) -> OptimizationResult:
    weight = 1 / len(symbols)
    return OptimizationResult(
        OptimizationStatus.OPTIMAL,
        solver,
        dict.fromkeys(symbols, weight),
        0.1,
        0.14,
        0.02,
        0.02**0.5,
        1,
    )


def test_auto_dispatches_scipy_without_cardinality(golden_problem) -> None:
    problem = replace(golden_problem, min_holdings=None, max_holdings=None)
    assert select_solver(problem) is SolverName.SCIPY
    with patch("app.optimization.engine.solve_continuous", return_value=stub_result(SolverName.SCIPY, problem.symbols)) as scipy, patch("app.optimization.engine.solve_mad") as pulp:
        result = solve(problem)
    scipy.assert_called_once_with(problem)
    pulp.assert_not_called()
    assert result.explanation_hooks is not None


def test_auto_dispatches_pulp_with_cardinality(golden_problem) -> None:
    assert select_solver(golden_problem) is SolverName.PULP
    with patch("app.optimization.engine.solve_mad", return_value=stub_result(SolverName.PULP, golden_problem.symbols)) as pulp:
        solve(golden_problem)
    pulp.assert_called_once_with(golden_problem)


def test_explicit_ortools_dispatch(golden_problem) -> None:
    problem = replace(golden_problem, solver=SolverName.ORTOOLS)
    with patch("app.optimization.engine.solve_ortools", return_value=stub_result(SolverName.ORTOOLS, problem.symbols)) as ortools:
        solve(problem)
    ortools.assert_called_once_with(problem)


def test_engine_returns_structured_conflict_without_solver(golden_problem) -> None:
    problem = replace(
        golden_problem, min_holdings=2, max_holdings=2, max_single_weight=0.4
    )
    with patch("app.optimization.engine.solve_mad") as solver:
        result = solve(problem)
    solver.assert_not_called()
    assert result.status is OptimizationStatus.INFEASIBLE
    assert result.metadata["conflicting_constraint"] == "C1/C3/C6 conflict"


def test_failed_result_has_no_fabricated_explanation(golden_problem) -> None:
    failed = OptimizationResult(
        OptimizationStatus.FAILED,
        SolverName.PULP,
        {},
        None,
        None,
        None,
        None,
        1,
    )
    with patch("app.optimization.engine.solve_mad", return_value=failed):
        result = solve(golden_problem)
    assert result.explanation_hooks is None
