"""OR-Tools CP-SAT support selection followed by a restricted SciPy QP."""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter

import numpy as np
from ortools.sat.python import cp_model

from app.optimization.scipy_solver import solve_continuous
from app.optimization.types import (
    OptimizationInput,
    OptimizationResult,
    OptimizationStatus,
    SolverName,
)


def select_support(problem: OptimizationInput, candidate_weights: np.ndarray) -> tuple[int, ...]:
    """Solve C6 selection using CP-SAT, maximizing continuous-QP candidate weight."""

    model = cp_model.CpModel()
    selected = [model.new_bool_var(f"selected_{index}") for index in range(problem.asset_count)]
    minimum = problem.min_holdings or 1
    maximum = problem.max_holdings or problem.asset_count
    model.add(sum(selected) >= minimum)
    model.add(sum(selected) <= maximum)
    scores = np.rint(candidate_weights * 1_000_000).astype(int)
    model.maximize(sum(int(scores[index]) * selected[index] for index in range(problem.asset_count)))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = problem.time_limit_seconds
    status = solver.solve(model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return ()
    return tuple(index for index, flag in enumerate(selected) if solver.value(flag))


def solve_ortools(problem: OptimizationInput) -> OptimizationResult:
    """Run the specified two-stage CP-SAT support and restricted-QP heuristic."""

    started = perf_counter()
    unconstrained = replace(problem, min_holdings=None, max_holdings=None, solver=SolverName.SCIPY)
    candidate = solve_continuous(unconstrained)
    if not candidate.is_feasible:
        return replace(candidate, solver_used=SolverName.ORTOOLS)
    support = select_support(problem, candidate.weight_vector(problem.symbols))
    if not support:
        return OptimizationResult(
            OptimizationStatus.INFEASIBLE,
            SolverName.ORTOOLS,
            {},
            None,
            None,
            None,
            None,
            int((perf_counter() - started) * 1000),
            message="C6 Cardinality: CP-SAT found no support set",
        )
    restricted = solve_continuous(problem, support_indices=support, enforce_min_lot=True)
    metadata = {
        **restricted.metadata,
        "support": [problem.symbols[index] for index in support],
        "method": "CP-SAT support selection + restricted SciPy QP",
    }
    return replace(
        restricted,
        solver_used=SolverName.ORTOOLS,
        solve_time_ms=int((perf_counter() - started) * 1000),
        metadata=metadata,
    )
