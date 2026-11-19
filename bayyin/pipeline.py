"""The whole analysis in one call, and the saving of its result tables.

`run_all()` is exactly what the notebook does step by step; it is also what `python -m bayyin` runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import data, hours, models, paydays, robustness
from .config import FIG_DIR, INPUT_CSV, TABLE_DIR
from .forecast import METHODS, ForecastResult, run_forecast
from .hours import HoursResult


@dataclass
class Results:
    """Every table the analysis produces (names match the CSV files in outputs/tables)."""
    tables: dict[str, pd.DataFrame]
    forecast: ForecastResult
    hours: HoursResult
    paydays: models.PaydayAnalysis
    seasons: models.SeasonAnalysis


def run_all(input_csv: Path = INPUT_CSV) -> Results:
    """Load the cleaned file and run every step, in order. Nothing is written to disk."""
    raw = data.load_clean(input_csv)
    analysis = data.select_columns(raw)
    analysis, excluded_recurring = data.drop_automatic_charges(analysis)
    analysis, excluded_duplicates = data.merge_duplicates(analysis)
    donor_day = data.build_donor_day(analysis)
    daily = data.build_daily(donor_day, analysis)

    calendar = paydays.build_payday_calendar()
    daily = paydays.add_payday_flags(daily, calendar)
    daily = models.add_season_flags(daily)

    payday_analysis = models.analyze_paydays(daily, calendar)
    season_analysis = models.analyze_seasons(daily)
    candidates, not_supported = models.rank_candidates(season_analysis.seasons, season_analysis.weekdays,
                                                       payday_analysis.results)
    robustness_table, robustness_summary = robustness.run_robustness(daily, donor_day, analysis,
                                                                     excluded_duplicates, candidates)
    forecast = run_forecast(daily)
    hour_analysis = hours.analyze_hours(raw, analysis)

    tables = collect_tables(
        candidates=candidates, not_supported=not_supported, payday=payday_analysis, seasons=season_analysis,
        calendar=calendar, robustness_table=robustness_table, robustness_summary=robustness_summary,
        forecast=forecast, hours=hour_analysis,
        excluded_recurring=excluded_recurring, excluded_duplicates=excluded_duplicates)
    return Results(tables=tables, forecast=forecast, hours=hour_analysis, paydays=payday_analysis, seasons=season_analysis)


def collect_tables(*, candidates: pd.DataFrame, not_supported: pd.DataFrame, payday: models.PaydayAnalysis,
                   seasons: models.SeasonAnalysis, calendar: pd.DataFrame, robustness_table: pd.DataFrame,
                   robustness_summary: pd.DataFrame, forecast: ForecastResult, hours: HoursResult,
                   excluded_recurring: pd.DataFrame, excluded_duplicates: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The tables that are saved, under the names of their CSV files. Donor IDs are never included."""
    return {
        "candidate_periods": candidates, "not_supported": not_supported,
        "payday_results": payday.results, "season_results": seasons.seasons,
        "weekday_results": seasons.weekdays, "payday_calendar": calendar,
        "robustness": robustness_table, "robustness_summary": robustness_summary,
        "forecast_errors": forecast.errors.reset_index(names="Days_group"),
        "forecast_capture": forecast.capture,
        "forecast_daily": forecast.forecast[["Gregorian_Date", "Donors"] + METHODS],
        "hours_weekday_heat": hours.heat.reset_index(), "hours_top_slots": hours.top_slots,
        "excluded_recurring": excluded_recurring.drop(columns="UserID_clean"),
        "excluded_duplicates": excluded_duplicates.drop(columns="UserID_clean"),
    }


def save_tables(tables: dict[str, pd.DataFrame], table_dir: Path = TABLE_DIR) -> Path:
    """Write every result table as CSV (UTF-8 with BOM so Excel opens Arabic correctly)."""
    table_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(table_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
    return table_dir


def save_figures(results: Results, fig_dir: Path = FIG_DIR) -> None:
    """Draw and save the four figures."""
    import matplotlib.pyplot as plt

    from . import plots
    from .config import FORECAST_HORIZON

    for fig in (plots.plot_paydays(results.paydays, fig_dir),
                plots.plot_seasons_friday(results.seasons, fig_dir),
                plots.plot_forecast(results.forecast, FORECAST_HORIZON, fig_dir),
                plots.plot_hours(results.hours, fig_dir)):
        plt.close(fig)
