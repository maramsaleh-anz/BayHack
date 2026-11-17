"""Charts. Every function draws one figure, saves it to outputs/figures and returns it."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .config import (BLUE, FIG_DIR, GREY, LIGHT_GREY, ORANGE, PAYDAY_WINDOW_DAYS, PROGRAM_LABEL, WEEK_ORDER,
                     WEEKEND_SHIFT)
from .forecast import ForecastResult
from .hours import HoursResult
from .models import PaydayAnalysis, SeasonAnalysis

AXIS_GREY = "#898781"
GRID = "#e1e0d9"
BAND = "#f0efec"


def _finish(fig: plt.Figure, filename: str, fig_dir: Path) -> plt.Figure:
    fig.tight_layout()
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / filename, dpi=150)
    return fig


def _hide_spines(ax, sides=("top", "right")) -> None:
    for side in sides:
        ax.spines[side].set_visible(False)


def plot_paydays(analysis: PaydayAnalysis, fig_dir: Path = FIG_DIR) -> plt.Figure:
    """Donors vs expected around each payday (shaded = payday + 3 days; band = 95% CI)."""
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.8), sharey=True)
    for ax, program in zip(axes, WEEKEND_SHIFT):
        s = analysis.events[analysis.events["Program"] == program].groupby("day")["ratio"].agg(["mean", "sem"])
        ax.axvspan(-0.5, PAYDAY_WINDOW_DAYS + 0.5, color=BAND)
        ax.axhline(0, color=AXIS_GREY, linewidth=1)
        ax.fill_between(s.index, (s["mean"] - 1.96 * s["sem"] - 1) * 100, (s["mean"] + 1.96 * s["sem"] - 1) * 100,
                        color=BLUE, alpha=0.15, linewidth=0)
        ax.plot(s.index, (s["mean"] - 1) * 100, color=BLUE, marker="o", markersize=4)
        ax.set_title(PROGRAM_LABEL[program].split(" (")[0], fontsize=10)
        ax.set_xlabel("Days from payday (0 = payday)")
    axes[0].set_ylabel("Donors vs expected (%)")
    fig.suptitle("Donors around paydays (shaded = payday + 3 days; band = 95% CI)", x=0.01, ha="left")
    return _finish(fig, "analysis_paydays.png", fig_dir)


def plot_seasons_friday(analysis: SeasonAnalysis, fig_dir: Path = FIG_DIR) -> plt.Figure:
    """Effect of each season and each weekday on donors per day, with 95% CI."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5), gridspec_kw={"width_ratios": [1.2, 1]})
    for ax, table, title in [(axes[0], analysis.seasons, "Seasonal days"),
                             (axes[1], analysis.weekdays, "Day of week (vs Sunday)")]:
        r = table.iloc[::-1].reset_index(drop=True)
        ax.axvline(0, color=AXIS_GREY, linewidth=1)
        ax.hlines(r.index, r["CI_low_%"], r["CI_high_%"], color=BLUE, linewidth=2)
        ax.plot(r["Change_%"], r.index, "o", color=BLUE, markersize=8, markeredgecolor="white")
        for i, row in r.iterrows():
            ax.text(row["CI_high_%"], i + 0.25, f" {row['Change_%']:+.0f}%", fontsize=9, color=GREY)
        ax.set_yticks(r.index, r["Factor"])
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_xlabel("Change in donors per day (%), 95% CI")
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        _hide_spines(ax, ("top", "right", "left"))
    fig.suptitle("Donors per day vs comparable days (adjusted for sample growth, paydays and the other factors)",
                 x=0.01, ha="left")
    return _finish(fig, "analysis_seasons_friday.png", fig_dir)


def plot_forecast(result: ForecastResult, horizon: int, fig_dir: Path = FIG_DIR) -> plt.Figure:
    """Actual vs forecast donors per day on the test period."""
    f = result.forecast
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(f["Gregorian_Date"], f["Donors"], color=GREY, linewidth=1.2, label="Actual")
    ax.plot(f["Gregorian_Date"], f["Model"], color=BLUE, linewidth=2, label="Model")
    ax.plot(f["Gregorian_Date"], f["Same_weekday_last_week"], color=ORANGE, linewidth=1,
            label="Baseline: same weekday last week")
    for origin in result.block_starts[1:]:
        ax.axvline(origin, color=LIGHT_GREY, linewidth=1)
    ax.set_title(f"Donors per day: actual vs forecast up to {horizon} days ahead (Jan - Jun 2023)", loc="left")
    ax.set_ylabel("Donors per day")
    ax.set_xlabel("Grey lines: forecast points - each forecast uses only the data before it")
    ax.grid(axis="y", color=GRID)
    _hide_spines(ax)
    ax.legend(frameon=False, loc="upper left")
    return _finish(fig, "forecast_2023.png", fig_dir)


def plot_hours(hours: HoursResult, fig_dir: Path = FIG_DIR) -> plt.Figure:
    """Weekday x hour heat map, and the hour-of-day profile in Ramadan vs the rest of the year."""
    fig, axes = plt.subplots(1, 2, figsize=(15, 4), gridspec_kw={"width_ratios": [1.6, 1]})
    axes[0].imshow(hours.heat.values, aspect="auto", cmap="Greens")
    axes[0].set_yticks(range(7), WEEK_ORDER)
    axes[0].set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
    axes[0].set_title("Donations by weekday and hour", loc="left")
    axes[1].plot(hours.hour_share.index, hours.hour_share["Ramadan"] * 100, color="#c9973f", linewidth=2, label="Ramadan")
    axes[1].plot(hours.hour_share.index, hours.hour_share["Rest of year"] * 100, color="#0e4d5c", linewidth=2,
                 label="Rest of year")
    axes[1].set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
    axes[1].set_ylabel("Share of the day's donations (%)")
    axes[1].set_title("Hour of day: Ramadan vs rest of year", loc="left")
    axes[1].legend(frameon=False)
    _hide_spines(axes[1])
    return _finish(fig, "analysis_hours.png", fig_dir)
