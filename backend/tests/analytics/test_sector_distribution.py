from __future__ import annotations

import numpy as np
import pytest

from app.analytics.sector_distribution import aggregate_sector_distribution
from app.optimization.types import ConstraintReport


def test_sector_weights_caps_and_binding_flags() -> None:
    rows = aggregate_sector_distribution(
        np.asarray([0.20, 0.30, 0.10, 0.40]),
        ("IT", "IT", "Energy", "FMCG"),
        {"IT": 0.50, "FMCG": 0.35},
        0.30,
        (
            ConstraintReport("C4 Sector cap: IT", True, True, 0.0),
            ConstraintReport("C4 Sector cap: Energy", True, False, 0.20),
        ),
    )
    by_sector = {row.sector: row for row in rows}
    assert by_sector["IT"].allocation == 0.50
    assert by_sector["IT"].is_binding
    assert by_sector["Energy"].remaining_capacity == pytest.approx(0.20)
    assert by_sector["FMCG"].exceeds_cap
