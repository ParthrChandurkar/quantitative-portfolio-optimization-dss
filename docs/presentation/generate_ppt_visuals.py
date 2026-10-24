"""Generate OptiVest visuals for a faculty-review PowerPoint.

The script creates ten 16:9, white-background figures in both PNG and SVG.
All numeric values are copied from ``docs/methodology-notes.md`` and the
documented live scenario walkthrough; they are not synthetic demo results.

Install the only presentation dependency if it is not already available:

    python -m pip install matplotlib

Run from the repository root:

    python docs/presentation/generate_ppt_visuals.py

Optionally choose another output directory or one output format:

    python docs/presentation/generate_ppt_visuals.py --output-dir my_slides --format png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Callable, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter


# OptiVest presentation palette.
INK = "#111827"
MUTED = "#64748B"
GRID = "#E2E8F0"
GREEN = "#10B981"
GREEN_LIGHT = "#ECFDF5"
BLUE = "#2563EB"
BLUE_LIGHT = "#EFF6FF"
AMBER = "#F59E0B"
AMBER_LIGHT = "#FFFBEB"
RED = "#EF476F"
PURPLE = "#7C3AED"
SLATE = "#94A3B8"
WHITE = "#FFFFFF"

SLIDE_SIZE = (13.333, 7.5)
PNG_DPI = 240


def new_slide(title: str, subtitle: str = "") -> tuple[Figure, Axes]:
    """Return a clean 16:9 canvas with a consistent title treatment."""
    fig, ax = plt.subplots(figsize=SLIDE_SIZE, facecolor=WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.text(0.055, 0.925, title, fontsize=23, fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.055, 0.884, subtitle, fontsize=10.5, color=MUTED)
    return fig, ax


def add_footer(fig: Figure, text: str) -> None:
    fig.text(0.055, 0.035, text, fontsize=7.8, color=MUTED)


def add_box(
    ax: Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    title: str,
    lines: Iterable[str],
    *,
    edge: str = INK,
    face: str = WHITE,
    title_color: str = INK,
    linewidth: float = 1.8,
) -> None:
    """Draw a rounded architecture card using axes-relative coordinates."""
    x, y = xy
    card = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        linewidth=linewidth,
        edgecolor=edge,
        facecolor=face,
        transform=ax.transAxes,
        zorder=2,
    )
    ax.add_patch(card)
    ax.text(
        x + 0.018,
        y + height - 0.042,
        title,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.5,
        fontweight="bold",
        color=title_color,
        zorder=3,
    )
    ax.text(
        x + 0.018,
        y + height - 0.088,
        "\n".join(lines),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.2,
        linespacing=1.55,
        color=INK,
        zorder=3,
    )


def connect(
    ax: Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = MUTED,
    dashed: bool = False,
) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.7,
        linestyle="--" if dashed else "-",
        color=color,
        transform=ax.transAxes,
        connectionstyle="arc3,rad=0",
        zorder=1,
    )
    ax.add_patch(arrow)


def technical_box(
    ax: Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    header: str,
    title: str,
    lines: Iterable[str],
    *,
    face: str = "#FAFAFA",
    fontsize: float = 7.0,
) -> None:
    """Draw a monochrome engineering-diagram box with a header band."""
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.004,rounding_size=0.008",
        linewidth=1.05,
        edgecolor="#202020",
        facecolor=face,
        transform=ax.transAxes,
        zorder=2,
    )
    ax.add_patch(patch)
    header_height = min(0.04, height * 0.22)
    ax.plot(
        [x, x + width],
        [y + height - header_height, y + height - header_height],
        color="#202020",
        linewidth=0.85,
        transform=ax.transAxes,
        zorder=3,
    )
    ax.text(
        x + width / 2,
        y + height - header_height / 2,
        header,
        ha="center",
        va="center",
        fontsize=6.5,
        fontweight="bold",
        color="#111111",
        transform=ax.transAxes,
        zorder=4,
    )
    body_top = y + height - header_height - 0.017
    if title:
        ax.text(
            x + 0.012,
            body_top,
            title,
            ha="left",
            va="top",
            fontsize=8.0,
            fontweight="bold",
            color="#111111",
            transform=ax.transAxes,
            zorder=4,
        )
        body_top -= 0.039
    ax.text(
        x + 0.012,
        body_top,
        "\n".join(f"• {line}" for line in lines),
        ha="left",
        va="top",
        fontsize=fontsize,
        linespacing=1.45,
        color="#202020",
        transform=ax.transAxes,
        zorder=4,
    )


def architecture_figure() -> Figure:
    """Visual 1: formal monochrome architecture matching an academic report style."""
    fig, ax = plt.subplots(figsize=SLIDE_SIZE, facecolor=WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.025, 0.965, "OPTIVEST SYSTEM ARCHITECTURE", fontsize=13, fontweight="bold", color="#111111", transform=ax.transAxes)
    ax.text(0.975, 0.965, "solid: application / process flow    - - -: data or optional AI input", fontsize=6.5, ha="right", color="#333333", transform=ax.transAxes)

    # 01 — source and ingestion
    technical_box(ax, (0.025, 0.58), 0.145, 0.29, "DATA SOURCE", "Nifty-50 Market Data", ["287,310 source rows", "49-stock universe", "OHLCV, fundamentals", "technical indicators"], fontsize=6.7)
    technical_box(ax, (0.025, 0.25), 0.145, 0.25, "DATA ENGINEERING", "ETL & Quality Pipeline", ["header reconciliation", "zero-OHLC validation", "daily-return calculation", "natural-key upserts"], fontsize=6.7)
    connect(ax, (0.097, 0.58), (0.097, 0.51), color="#222222")

    # 02 — governed database platform with internal layers
    platform = FancyBboxPatch((0.205, 0.25), 0.33, 0.62, boxstyle="round,pad=0.004,rounding_size=0.008", linewidth=1.05, edgecolor="#202020", facecolor="#FAFAFA", transform=ax.transAxes)
    ax.add_patch(platform)
    ax.plot([0.205, 0.535], [0.825, 0.825], color="#202020", linewidth=0.85, transform=ax.transAxes)
    ax.text(0.370, 0.848, "GOVERNED DATA PLATFORM — POSTGRESQL", ha="center", va="center", fontsize=7.6, fontweight="bold", transform=ax.transAxes)
    ax.text(0.370, 0.795, "SCHEMA-BASED DATA LAYERS", ha="center", fontsize=6.2, fontweight="bold", color="#444444", transform=ax.transAxes)
    technical_box(ax, (0.222, 0.58), 0.137, 0.17, "MARKET", "", ["stocks + sectors", "prices + returns", "fundamentals + indicators"], fontsize=6.2)
    technical_box(ax, (0.378, 0.58), 0.137, 0.17, "DECISIONS", "", ["runs + snapshots", "holdings + constraints", "scenarios + reports"], fontsize=6.2)
    technical_box(ax, (0.222, 0.36), 0.137, 0.16, "AUDIT", "", ["explanation evidence", "walk-forward runs", "temporal boundaries"], fontsize=6.2)
    technical_box(ax, (0.378, 0.36), 0.137, 0.16, "AI & PROFILE", "", ["risk profiles", "model registry", "alerts + query logs"], fontsize=6.2)
    governance = FancyBboxPatch((0.222, 0.275), 0.293, 0.055, boxstyle="round,pad=0.004,rounding_size=0.006", linewidth=0.9, edgecolor="#202020", facecolor="#F2F2F2", transform=ax.transAxes)
    ax.add_patch(governance)
    ax.text(0.369, 0.302, "UUID keys • indexed dates • constraints • reproducible history", ha="center", va="center", fontsize=5.8, transform=ax.transAxes)
    connect(ax, (0.17, 0.375), (0.195, 0.375), color="#222222")

    # 03 — OR and AI computation
    technical_box(ax, (0.565, 0.55), 0.195, 0.32, "OPERATIONS RESEARCH", "Portfolio Optimization Engine", ["mean-variance QP", "MAD mixed-integer model", "SciPy / PuLP / OR-Tools", "budget, stock, sector limits", "scenario shock and re-solve", "binding-constraint evidence"], fontsize=6.5)
    technical_box(ax, (0.565, 0.25), 0.195, 0.23, "AI PERSONALIZATION", "Machine-Learning Pipeline", ["Gradient Boosting forecast", "Logistic Regression profile", "TF-IDF intent classifier", "Isolation Forest alerts"], fontsize=6.5)
    connect(ax, (0.535, 0.66), (0.555, 0.66), color="#222222")
    connect(ax, (0.535, 0.41), (0.555, 0.37), color="#555555", dashed=True)
    connect(ax, (0.662, 0.48), (0.662, 0.54), color="#555555", dashed=True)

    # 04 — API, UI and outputs
    technical_box(ax, (0.795, 0.68), 0.18, 0.19, "APPLICATION API", "FastAPI Backend", ["JWT + ownership checks", "Pydantic contracts", "async SQLAlchemy services"], fontsize=6.5)
    technical_box(ax, (0.795, 0.43), 0.18, 0.19, "WEB APPLICATION", "React + TypeScript", ["portfolio builder", "details and explanations", "scenarios + analytics"], fontsize=6.5)
    technical_box(ax, (0.795, 0.18), 0.18, 0.19, "DECISION DELIVERY", "Personalized DSS", ["optimized holdings", "PDF reports", "grounded Q&A + alerts"], fontsize=6.5)
    connect(ax, (0.76, 0.70), (0.785, 0.77), color="#222222")
    connect(ax, (0.885, 0.68), (0.885, 0.63), color="#222222")
    connect(ax, (0.885, 0.43), (0.885, 0.38), color="#222222")

    # Technology strip
    strip = FancyBboxPatch((0.025, 0.045), 0.95, 0.085, boxstyle="round,pad=0.004,rounding_size=0.008", linewidth=1.0, edgecolor="#202020", facecolor="#FAFAFA", transform=ax.transAxes)
    ax.add_patch(strip)
    ax.text(0.04, 0.108, "TECHNOLOGY STACK", fontsize=6.7, fontweight="bold", transform=ax.transAxes)
    stack = [
        (0.04, "Frontend: React 19 + TypeScript\nState: React Query"),
        (0.25, "Backend: Python + FastAPI\nORM: SQLAlchemy 2.0"),
        (0.47, "Database: PostgreSQL + Alembic\nAuth: JWT"),
        (0.68, "OR: SciPy + PuLP + OR-Tools\nML: scikit-learn"),
        (0.86, "Reports: WeasyPrint\nTests: pytest + Vitest"),
    ]
    for x, text_value in stack:
        ax.text(x, 0.078, text_value, fontsize=5.7, va="center", linespacing=1.35, transform=ax.transAxes)
    return fig


def allocation_figure() -> Figure:
    """Visual 2: standard pie chart for portfolio allocation."""
    fig, _ = new_slide("")
    ax = fig.add_axes([0.08, 0.08, 0.62, 0.84])
    labels = ["BHARTIARTL", "DIVISLAB", "EICHERMOT", "M&M", "SUNPHARMA", "WIPRO"]
    weights = [20, 20, 15, 20, 5, 20]
    colors = ["#2F6CAD", "#4F86C6", "#73A1D1", "#0F9D79", "#E3A42F", "#8B6CB8"]
    wedges, _, _ = ax.pie(
        weights,
        colors=colors,
        startangle=90,
        counterclock=False,
        autopct=lambda value: f"{value:.0f}%",
        pctdistance=0.72,
        textprops={"fontsize": 9, "color": WHITE, "fontweight": "bold"},
        wedgeprops={"edgecolor": WHITE, "linewidth": 2},
    )
    ax.set_aspect("equal")
    legend_ax = fig.add_axes([0.69, 0.20, 0.27, 0.60])
    legend_ax.axis("off")
    legend_ax.legend(wedges, labels, loc="center left", frameon=False, fontsize=10, labelspacing=1.35)
    return fig


def scenario_figure() -> Figure:
    """Visual 3: grouped horizontal bars before and after a market shock."""
    fig, _ = new_slide("")
    ax = fig.add_axes([0.10, 0.12, 0.84, 0.80])
    stocks = ["AXISBANK", "BPCL", "HEROMOTOCO", "HINDALCO", "SBIN", "TATASTEEL"]
    original = [15, 20, 10, 20, 20, 15]
    stressed = [15, 10, 20, 20, 20, 15]
    y = list(range(len(stocks)))
    height = 0.34
    ax.barh([value + height / 2 for value in y], original, height=height, color="#9AA8BA", edgecolor="#667386", label="Original")
    ax.barh([value - height / 2 for value in y], stressed, height=height, color="#0F9D79", edgecolor="#087257", label="After re-optimization")
    ax.set_yticks(y, stocks)
    ax.invert_yaxis()
    ax.set_xlim(0, 22)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}%"))
    ax.set_xlabel("Portfolio weight", color=MUTED)
    ax.set_xticks([0, 5, 10, 15, 20])
    ax.grid(axis="x", color=GRID, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="y", labelsize=9, colors=INK, length=0)
    ax.tick_params(axis="x", colors=MUTED)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.02), frameon=False, ncol=2)
    return fig


def out_of_sample_figure() -> Figure:
    """Visual 4: grouped vertical bars comparing fitted and unseen outcomes."""
    fig, _ = new_slide("")
    ax = fig.add_axes([0.11, 0.12, 0.80, 0.80])
    categories = ["Annualized return", "Annualized volatility"]
    fitted = [42.9119, 16.9399]
    unseen = [10.3141, 15.2203]
    x = list(range(len(categories)))
    width = 0.32
    ax.bar([value - width / 2 for value in x], fitted, width=width, color="#8C8C8C", edgecolor="#5F5F5F", label="Training-period estimate")
    ax.bar([value + width / 2 for value in x], unseen, width=width, color="#2F6CAD", edgecolor="#1D4775", label="Later unseen result")
    ax.set_xticks(x, categories)
    ax.set_ylabel("Percent")
    ax.set_ylim(0, 48)
    ax.grid(axis="y", color="#D7DCE2", linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    return fig


def walk_forward_figure() -> Figure:
    """Visual 5: line graph of the persisted walk-forward portfolio value."""
    fig, _ = new_slide("")
    ax = fig.add_axes([0.09, 0.15, 0.84, 0.76])
    periods = ["Start", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan-26"]
    values = [
        1_000_000.00,
        996_847.32,
        917_584.55,
        975_122.66,
        1_017_317.86,
        1_049_573.64,
        1_102_654.48,
        1_024_087.37,
        990_627.33,
        1_044_293.22,
        1_063_668.54,
        1_040_259.59,
        1_038_843.18,
        1_011_596.09,
    ]
    values_lakh = [value / 100_000 for value in values]
    ax.plot(periods, values_lakh, color="#2F6CAD", linewidth=2.5, marker="o", markersize=6, markerfacecolor=WHITE, markeredgewidth=1.6, label="Walk-forward portfolio value")
    ax.axhline(10, color="#777777", linewidth=1.2, linestyle="--", label="Starting investment")
    ax.fill_between(range(len(periods)), values_lakh, 10, color="#2F6CAD", alpha=0.10)
    ax.set_ylabel("Portfolio value (INR lakh)")
    ax.set_xlabel("Rebalance period")
    ax.set_ylim(8.8, 11.3)
    ax.grid(axis="y", color="#D7DCE2", linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=35)
    ax.legend(frameon=False, loc="upper left")
    return fig


def monthly_returns_figure() -> Figure:
    """Visual 6: monthly walk-forward return bars from the persisted run."""
    fig, _ = new_slide("")
    ax = fig.add_axes([0.09, 0.14, 0.84, 0.78])
    periods = ["Jan-25", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan-26"]
    returns = [-0.32, -7.95, 6.27, 4.33, 3.17, 5.06, -7.13, -3.27, 5.42, 1.86, -2.20, -0.14, -2.62]
    colors = ["#178A68" if value >= 0 else "#C94A52" for value in returns]
    ax.bar(periods, returns, color=colors, edgecolor=["#0C654C" if value >= 0 else "#91343A" for value in returns], width=0.68)
    ax.axhline(0, color="#333333", linewidth=1.0)
    ax.set_ylabel("Period return (%)")
    ax.set_xlabel("Rebalance period")
    ax.set_ylim(-9, 8)
    ax.grid(axis="y", color="#D7DCE2", linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=35)
    return fig


def daily_returns_distribution_figure() -> Figure:
    """Visual 7: histogram computed directly from real Nifty-50 daily returns."""
    dataset = Path(__file__).parents[2] / "data" / "raw" / "nifty50_historical_data.csv"
    daily_returns: list[float] = []
    with dataset.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            raw_return = row.get("Daily_Return", "").strip()
            if not raw_return:
                continue
            value = float(raw_return) * 100
            if -10 <= value <= 10:
                daily_returns.append(value)

    fig, _ = new_slide("")
    ax = fig.add_axes([0.10, 0.14, 0.83, 0.78])
    ax.hist(
        daily_returns,
        bins=80,
        range=(-10, 10),
        color="#2F6CAD",
        edgecolor=WHITE,
        linewidth=0.35,
    )
    ax.axvline(0, color="#202020", linewidth=1.2, linestyle="--")
    ax.set_xlabel("Daily stock return (%)")
    ax.set_ylabel("Number of observations")
    ax.set_xlim(-10, 10)
    ax.grid(axis="y", color="#D7DCE2", linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    return fig


def project_workflow_figure() -> Figure:
    """Visual 8: ten-stage project workflow for presentation and report use."""
    fig, ax = plt.subplots(figsize=SLIDE_SIZE, facecolor=WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    steps = [
        (
            "1. Requirements and constraint definition",
            "Define investor inputs, optimization objectives, budget rules,\nstock limits, sector caps and measurable system requirements.",
        ),
        (
            "2. Nifty-50 dataset reconciliation",
            "Inspect the 287,310-row price history and 49-stock summary;\nreconcile actual CSV headers with the system's mapped database fields.",
        ),
        (
            "3. ETL and PostgreSQL integration",
            "Reject invalid zero-OHLC rows, calculate daily returns and load\nprices, fundamentals and indicators through idempotent upserts.",
        ),
        (
            "4. Investor profiling and portfolio inputs",
            "Collect budget, return goal and risk answers; use the trained risk\nclassifier to recommend visible defaults that the investor can edit.",
        ),
        (
            "5. Return and covariance estimation",
            "Estimate expected returns and asset covariance from historical prices;\noptionally supply Gradient Boosting forecasts through a declared input method.",
        ),
        (
            "6. Operations Research formulation",
            "Express budget, long-only, stock-weight, sector and holdings rules\nas QP, LP/MILP or hybrid optimization constraints.",
        ),
        (
            "7. Solver execution and feasibility checks",
            "Solve with SciPy, PuLP or OR-Tools; verify full investment, bounds,\nsector caps, target return and constraint residuals.",
        ),
        (
            "8. Explainability and scenario re-optimization",
            "Generate evidence-backed selection reasons and re-solve after market,\nsector, inflation, rate, budget or risk-profile shocks.",
        ),
        (
            "9. Out-of-sample and walk-forward validation",
            "Test only on later unseen dates, enforce zero date overlap and compare\na fixed portfolio with periodic re-estimation and rebalancing.",
        ),
        (
            "10. Personalized decision-support delivery",
            "Present holdings, risk-return analytics, scenarios, grounded Q&A,\nalerts and downloadable PDF reports through the web application.",
        ),
    ]

    box_width = 0.435
    box_height = 0.145
    left_x, right_x = 0.045, 0.52
    y_positions = [0.81, 0.62, 0.43, 0.24, 0.05]
    blue_edge = "#4B98F7"
    blue_fill = "#F7FAFE"
    final_edge = "#10B981"
    final_fill = "#F2FCF8"

    for index, (heading, description) in enumerate(steps):
        column_x = left_x if index < 5 else right_x
        y = y_positions[index % 5]
        is_final = index == 9
        card = FancyBboxPatch(
            (column_x, y),
            box_width,
            box_height,
            boxstyle="round,pad=0.009,rounding_size=0.012",
            linewidth=1.35 if is_final else 1.05,
            edgecolor=final_edge if is_final else blue_edge,
            facecolor=final_fill if is_final else blue_fill,
            transform=ax.transAxes,
        )
        ax.add_patch(card)
        ax.text(
            column_x + 0.018,
            y + box_height - 0.034,
            heading,
            ha="left",
            va="top",
            fontsize=10.2,
            fontweight="bold",
            color="#123B6D" if not is_final else "#087257",
            transform=ax.transAxes,
        )
        ax.text(
            column_x + 0.018,
            y + box_height - 0.078,
            description,
            ha="left",
            va="top",
            fontsize=7.7,
            linespacing=1.45,
            color="#172033",
            transform=ax.transAxes,
        )

    return fig


def ml_portfolio_performance_figure() -> Figure:
    """Visual 9: compact report figure comparing both estimation methods."""
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 5.4), facecolor=WHITE)
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.11, top=0.96, wspace=0.34, hspace=0.46)
    colors = ["#2F6CAD", "#E08B3E"]
    edge_colors = ["#1D4775", "#A65E23"]
    labels = ["Historical\nmean", "ML\nforecast"]
    metrics = [
        ("Realized return", [10.2707, 5.8787], "%", (0, 12)),
        ("Realized volatility", [15.1897, 17.0250], "%", (0, 20)),
        ("Maximum drawdown", [-13.2597, -13.3183], "%", (-15, 0)),
        ("Realized Sharpe ratio", [0.6762, 0.3453], "", (0, 0.8)),
    ]

    for ax, (metric, values, suffix, limits) in zip(axes.flat, metrics):
        bars = ax.bar(labels, values, color=colors, edgecolor=edge_colors, linewidth=1.0, width=0.58)
        ax.set_title(metric, fontsize=10.5, fontweight="bold", color=INK, pad=7)
        ax.set_ylim(*limits)
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.grid(axis="y", color="#D7DCE2", linewidth=0.7, linestyle=(0, (3, 3)))
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=8.5)
        ax.tick_params(axis="y", labelsize=8)
        for bar, value in zip(bars, values):
            if value >= 0:
                y = value + (limits[1] - limits[0]) * 0.025
                va = "bottom"
            else:
                y = value - (limits[1] - limits[0]) * 0.025
                va = "top"
            displayed = f"{value:.2f}{suffix}"
            ax.text(bar.get_x() + bar.get_width() / 2, y, displayed, ha="center", va=va, fontsize=8.5, fontweight="bold", color=INK)
    return fig


def risk_classifier_performance_figure() -> Figure:
    """Visual 10: compact accuracy dot plot for the report column."""
    fig, ax = plt.subplots(figsize=(8.2, 4.6), facecolor=WHITE)
    fig.subplots_adjust(left=0.23, right=0.96, bottom=0.20, top=0.88)
    classifiers = ["Random Forest", "Logistic Regression"]
    training = [99.325, 99.975]
    held_out = [98.200, 100.000]
    y = [0, 1]

    for row, train_value, test_value in zip(y, training, held_out):
        ax.plot([train_value, test_value], [row, row], color="#CBD5E1", linewidth=4.0, solid_capstyle="round", zorder=1)
    ax.scatter(training, y, s=115, color="#8795A8", edgecolor="#5F6B7A", linewidth=1.0, label="Training accuracy", zorder=3)
    ax.scatter(held_out, y, s=115, color="#0F9D79", edgecolor="#087257", linewidth=1.0, label="Held-out accuracy", zorder=3)

    for row, value in zip(y, training):
        ax.annotate(f"{value:.3f}%", (value, row), xytext=(0, 11), textcoords="offset points", ha="center", fontsize=9, color="#526071")
    for row, value in zip(y, held_out):
        ax.annotate(f"{value:.3f}%", (value, row), xytext=(0, -17), textcoords="offset points", ha="center", fontsize=9, fontweight="bold", color="#087257")

    ax.set_yticks(y, classifiers)
    ax.set_xlim(97.5, 100.25)
    ax.set_ylim(-0.55, 1.55)
    ax.set_xlabel("Accuracy (%)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.1f}%"))
    ax.grid(axis="x", color="#D7DCE2", linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=10)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, 1.16), ncol=2)
    return fig


FIGURES: list[tuple[str, Callable[[], Figure]]] = [
    ("01_system_architecture", architecture_figure),
    ("02_portfolio_allocation", allocation_figure),
    ("03_market_crash_reallocation", scenario_figure),
    ("04_out_of_sample_performance", out_of_sample_figure),
    ("05_walk_forward_comparison", walk_forward_figure),
    ("06_walk_forward_monthly_returns", monthly_returns_figure),
    ("07_daily_returns_distribution", daily_returns_distribution_figure),
    ("08_project_workflow", project_workflow_figure),
    ("09_ml_portfolio_performance", ml_portfolio_performance_figure),
    ("10_risk_classifier_performance", risk_classifier_performance_figure),
]


def save_figure(fig: Figure, destination: Path, output_format: str) -> None:
    options: dict[str, object] = {"bbox_inches": "tight", "facecolor": WHITE}
    if output_format == "png":
        options["dpi"] = PNG_DPI
    fig.savefig(destination.with_suffix(f".{output_format}"), **options)


def generate(output_dir: Path, requested_format: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    formats = ("png", "svg") if requested_format == "both" else (requested_format,)
    for filename, factory in FIGURES:
        figure = factory()
        for output_format in formats:
            save_figure(figure, output_dir / filename, output_format)
        plt.close(figure)
        print(f"Created {filename}: {', '.join(formats)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("generated"),
        help="Directory for the generated slide visuals.",
    )
    parser.add_argument(
        "--format",
        choices=("png", "svg", "both"),
        default="both",
        help="Output format (default: both).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    generate(arguments.output_dir, arguments.format)
