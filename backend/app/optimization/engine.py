"""Public optimization entry point and isolated solver dispatch policy."""

from __future__ import annotations

from dataclasses import replace

from app.optimization.constraints import find_structural_infeasibility
from app.optimization.explain_hooks import compute_explanation_hooks
from app.optimization.ortools_solver import solve_ortools
from app.optimization.pulp_solver import solve_mad
from app.optimization.scipy_solver import solve_continuous
from app.optimization.types import (
    OptimizationInput,
    OptimizationResult,
    OptimizationStatus,
    SolverName,
)


def select_solver(problem: OptimizationInput) -> SolverName:
    """Auto uses SciPy without cardinality and PuLP when C6/C7 are active."""

    if problem.solver is not SolverName.AUTO:
        return problem.solver
    if problem.min_holdings is not None or problem.max_holdings is not None:
        return SolverName.PULP
    return SolverName.SCIPY


def _infeasible(problem: OptimizationInput, solver: SolverName, message: str) -> OptimizationResult:
    return OptimizationResult(
        status=OptimizationStatus.INFEASIBLE,
        solver_used=solver,
        weights={},
        objective_value=None,
        expected_return=None,
        expected_variance=None,
        expected_volatility=None,
        solve_time_ms=0,
        message=message,
        metadata={"conflicting_constraint": message.split(":", maxsplit=1)[0]},
    )


def solve(problem: OptimizationInput) -> OptimizationResult:
    """Solve FR-4 and attach FR-5 numerical explanation evidence on success."""

    solver = select_solver(problem)
    conflict = find_structural_infeasibility(problem)
    if conflict is not None:
        return _infeasible(problem, solver, conflict)
    if solver is SolverName.SCIPY:
        result = solve_continuous(problem)
    elif solver is SolverName.PULP:
        result = solve_mad(problem)
    elif solver is SolverName.ORTOOLS:
        result = solve_ortools(problem)
    else:
        return _infeasible(problem, solver, f"Solver: unsupported solver {solver}")

    if not result.is_feasible:
        return result
    weights = result.weight_vector(problem.symbols)
    shadow_prices = {
        str(name): float(value)
        for name, value in result.metadata.get("shadow_prices", {}).items()
    }
    hooks = compute_explanation_hooks(problem, weights, shadow_prices)
    return replace(result, explanation_hooks=hooks)
