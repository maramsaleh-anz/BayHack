"""The statistical analyses: paydays, seasons / day of week, and the ranking of candidate periods.

All models are Poisson regressions of the number of donors per day, with robust (HAC) errors because days are not
independent. Results are associations in this sample, not proof of cause.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from .config import (HAC_MAXLAGS, PAYDAY_MODEL_SEASONS, PAYDAY_WINDOW_DAYS, PAYDAY_WINDOWS, PROGRAM_LABEL, SEASONS,
                     WEEKDAY_TERM, WEEKEND_SHIFT, trend_term)

# ---------------------------------------------------------------- small helpers


def add_season_flags(daily: pd.DataFrame) -> pd.DataFrame:
    """Add one 0/1 column per season (see config.SEASONS) and `any_season`. Returns a new table."""
    daily = daily.copy()
    for column, (_, rule) in SEASONS.items():
        daily[column] = rule(daily["Hijri_Month"], daily["Hijri_Day"]).astype(int)
    daily["any_season"] = daily[list(SEASONS)].max(axis=1)
    return daily


def model_frame(daily: pd.DataFrame) -> pd.DataFrame:
    """Days that have data, with integer `Donors` and the time index `t` (days since the first day)."""
    data = daily[daily["has_data"]].copy()
    data["Donors"] = data["Donors"].astype(int)
    data["t"] = (data["Gregorian_Date"] - data["Gregorian_Date"].min()).dt.days
    return data


def fit_poisson(formula: str, data: pd.DataFrame, hac: bool = True, **glm_kwargs):
    """Poisson GLM. With `hac=True` (default) the errors are robust to day-to-day dependence."""
    model = smf.glm(formula, data, family=sm.families.Poisson(), **glm_kwargs)
    return model.fit(cov_type="HAC", cov_kwds={"maxlags": HAC_MAXLAGS}) if hac else model.fit()


def pct_change(coefficient: float) -> float:
    """A log-scale coefficient as a percentage change (not rounded)."""
    return (np.exp(coefficient) - 1) * 100


def base_formula(outcome: str = "Donors", seasons=SEASONS, windows=(), trend_df: int | None = None) -> str:
    """`outcome ~ weekday + trend + seasons (+ windows)`, as a formula string."""
    terms = [WEEKDAY_TERM, trend_term() if trend_df is None else trend_term(trend_df), *seasons, *windows]
    return f"{outcome} ~ " + " + ".join(terms)


# ---------------------------------------------------------------- 1) paydays


@dataclass
class PaydayAnalysis:
    results: pd.DataFrame   # one row per payment program
    events: pd.DataFrame    # donors vs expected, day by day around each payday (for the chart)


def analyze_paydays(daily: pd.DataFrame, calendar: pd.DataFrame) -> PaydayAnalysis:
    """Do donors rise after paydays?

    Compares days in each payday window (payday + 3 days) with comparable days outside it, controlling for day of week,
    sample growth (smooth trend) and religious seasons. A second, simpler "event view" checks every payday separately.
    """
    data = model_frame(daily)
    controls = list(PAYDAY_MODEL_SEASONS)
    model = fit_poisson(base_formula(seasons=controls, windows=PAYDAY_WINDOWS), data)
    ci = model.conf_int()

    # Event view: donors vs expected (model WITHOUT payday windows) around each payday
    base = fit_poisson(base_formula(seasons=controls), data, hac=False)
    ratio = (data["Donors"] / base.fittedvalues).set_axis(data["Gregorian_Date"])
    event_rows = []
    for program in WEEKEND_SHIFT:
        for payday in calendar.loc[calendar["Program"] == program, "Pay_Date"]:
            for k in range(-5, 8):
                event_rows.append({"Program": program, "Payday": payday, "day": k,
                                   "ratio": ratio.get(payday + pd.Timedelta(days=k))})
    events = pd.DataFrame(event_rows).dropna()
    per_payday = events[events["day"].between(0, PAYDAY_WINDOW_DAYS)].groupby(["Program", "Payday"])["ratio"].mean()
    event_stats = per_payday.groupby("Program").agg(["mean", "sem", "size"])  # one value per payday

    rows = []
    for window in PAYDAY_WINDOWS:
        program = window.replace("_window", "")
        stats = event_stats.loc[program]
        rows.append({
            "Payment": PROGRAM_LABEL[program],
            "Window_days": int(data[window].sum()),
            "Overlap_with_salary_window_%": round(data.loc[data[window] == 1, "salary_27_window"].mean() * 100),
            "Change_%": round(pct_change(model.params[window]), 1),
            "CI_low_%": round(pct_change(ci.loc[window, 0]), 1),
            "CI_high_%": round(pct_change(ci.loc[window, 1]), 1),
            "p_value": round(model.pvalues[window], 4),
            "Paydays": int(stats["size"]),
            "Event_view_%": round((stats["mean"] - 1) * 100, 1),
            "Event_CI_low_%": round((stats["mean"] - 1.96 * stats["sem"] - 1) * 100, 1),
        })
    results = pd.DataFrame(rows)
    # "Clear rise" only when BOTH methods agree; a window that overlaps the salary window by 40%+ cannot be separated from it
    both = (results["CI_low_%"] > 0) & (results["Event_CI_low_%"] > 0)
    mixed = (results["Overlap_with_salary_window_%"] >= 40) & (results["Payment"] != PROGRAM_LABEL["salary_27"])
    results["Conclusion"] = np.select(
        [both & ~mixed, both & mixed, results["CI_low_%"] > 0],
        ["Clear rise", "Rise, but mostly the salary days (overlap)", "Not confirmed by the event view"],
        "No clear rise")
    assert int(model.nobs) == len(data)
    return PaydayAnalysis(results=results, events=events)


# ---------------------------------------------------------------- 2) seasons and day of week


@dataclass
class SeasonAnalysis:
    seasons: pd.DataFrame
    weekdays: pd.DataFrame
    friday_weeks: str       # plain-language second check for Friday
    days_used: int


def _effect(model, ci, term: str, label: str, days: int) -> dict:
    return {"Factor": label, "Days": days, "Change_%": round(pct_change(model.params[term]), 1),
            "CI_low_%": round(pct_change(ci.loc[term, 0]), 1), "CI_high_%": round(pct_change(ci.loc[term, 1]), 1),
            "p_value": round(model.pvalues[term], 4)}


def _conclude(table: pd.DataFrame) -> pd.DataFrame:
    table["Conclusion"] = np.select([table["CI_low_%"] > 0, table["CI_high_%"] < 0],
                                    ["Clear rise", "Clear drop"], "No clear difference")
    return table


def analyze_seasons(daily: pd.DataFrame) -> SeasonAnalysis:
    """Ramadan, seasonal days and day of week (Friday): do donors rise?

    One Poisson model with seasons + day of week + payday windows + smooth trend. Each result gets a simple second check.
    """
    assert "salary_27_window" in daily.columns, "Add the payday flags first"
    data = model_frame(daily)
    windows = [c for c in daily.columns if c.endswith("_window")]
    model = fit_poisson(base_formula(windows=windows), data)
    ci = model.conf_int()

    # Seasons: model + check vs the last 28 ordinary days before each occurrence
    seasons = _conclude(pd.DataFrame(
        [_effect(model, ci, col, label, int(data[col].sum())) for col, (label, _) in SEASONS.items()]))
    checks = []
    for column, (label, _) in SEASONS.items():
        on = data[data[column] == 1]
        for _, occurrence in on.groupby((on["Gregorian_Date"].diff().dt.days != 1).cumsum()):
            start = occurrence["Gregorian_Date"].min()
            before = data[(data["Gregorian_Date"] < start) & (data["Gregorian_Date"] >= start - pd.Timedelta(days=90))
                          & (data["any_season"] == 0)].tail(28)
            if len(before) >= 14:  # enough ordinary days before to compare
                checks.append({"Factor": label, "higher": occurrence["Donors"].mean() > before["Donors"].mean()})
    check = pd.DataFrame(checks).groupby("Factor")["higher"].agg(["sum", "size"])
    seasons["Higher_than_ordinary_days_before"] = seasons["Factor"].map(
        lambda f: f"{int(check.loc[f, 'sum'])} of {int(check.loc[f, 'size'])}")
    # Final conclusion only when the model and the check point the same way
    share_up = seasons["Factor"].map(check["sum"] / check["size"])
    agree = np.where(seasons["Conclusion"] == "Clear rise", share_up > 0.5,
                     np.where(seasons["Conclusion"] == "Clear drop", share_up < 0.5, True))
    seasons.loc[~agree, "Conclusion"] = "Not consistent (model and check disagree)"

    # Day of week: model (vs Sunday) + check: in how many weeks was Friday above the rest of its week
    weekdays = _conclude(pd.DataFrame(
        [_effect(model, ci, f"{WEEKDAY_TERM}[T.{w}]", f"{w} (vs Sunday)", int((data["Weekday"] == w).sum()))
         for w in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]]))
    weekly = data.assign(week=data["Gregorian_Date"].dt.to_period("W-SAT"))  # weeks Sunday..Saturday
    full = weekly.groupby("week").filter(lambda g: len(g) == 7)
    friday = full[full["Weekday"] == "Friday"].set_index("week")["Donors"]
    rest = full[full["Weekday"] != "Friday"].groupby("week")["Donors"].mean()
    friday_weeks = f"Friday above the average of the other 6 days in {int((friday > rest).sum())} of {len(friday)} full weeks"

    assert int(model.nobs) == len(data) and (data[list(SEASONS)].sum(axis=1) <= 1).all()
    return SeasonAnalysis(seasons=seasons, weekdays=weekdays, friday_weeks=friday_weeks, days_used=len(data))


# ---------------------------------------------------------------- 3) candidate periods


def rank_candidates(seasons: pd.DataFrame, weekdays: pd.DataFrame,
                    paydays: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Periods to TEST campaigns in: every "Clear rise", ranked by the size of the rise.

    Returns (candidates, not_supported). This ranks periods; it does not prove the best time to advertise.
    """
    all_results = pd.concat([
        seasons.assign(Type="Season"),
        weekdays.assign(Type="Day of week"),
        paydays.rename(columns={"Payment": "Factor"}).assign(Type="Payday (payday + 3 days)"),
    ], ignore_index=True)[["Type", "Factor", "Change_%", "CI_low_%", "CI_high_%", "Conclusion"]]
    candidates = (all_results[all_results["Conclusion"] == "Clear rise"]
                  .sort_values("Change_%", ascending=False).reset_index(drop=True))
    candidates.insert(0, "Rank", range(1, len(candidates) + 1))
    not_supported = all_results[all_results["Conclusion"] != "Clear rise"].reset_index(drop=True)
    assert len(candidates) + len(not_supported) == len(all_results)
    return candidates, not_supported
