"""Sector allocation versus configured Phase 4 caps."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.optimization.types import ConstraintReport, FloatArray


@dataclass(frozen=True, slots=True)
class SectorAllocation:
    sector: str
    allocation: float
    cap: float
    remaining_capacity: float
    is_binding: bool
    exceeds_cap: bool


def aggregate_sector_distribution(
    weights: FloatArray,
    sectors: tuple[str, ...],
    sector_caps: dict[str, float],
    default_sector_cap: float,
    constraint_reports: tuple[ConstraintReport, ...] = (),
) -> tuple[SectorAllocation, ...]:
    """Aggregate aligned weights and surface the solver's binding C4 checks."""

    vector = np.asarray(weights, dtype=float)
    if vector.shape != (len(sectors),):
        raise ValueError("weights must align with sectors")
    binding_names = {
        report.constraint_name
        for report in constraint_reports
        if report.is_binding and report.constraint_name.startswith("C4 Sector cap: ")
    }
    sector_array = np.asarray(sectors)
    rows: list[SectorAllocation] = []
    for sector in sorted(set(sectors)):
        allocation = float(np.sum(vector[sector_array == sector]))
        cap = sector_caps.get(sector, default_sector_cap)
        remaining = cap - allocation
        rows.append(
            SectorAllocation(
                sector=sector,
                allocation=allocation,
                cap=cap,
                remaining_capacity=remaining,
                is_binding=f"C4 Sector cap: {sector}" in binding_names,
                exceeds_cap=remaining < -1e-6,
            )
        )
    return tuple(rows)
