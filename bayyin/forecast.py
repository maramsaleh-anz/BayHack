"""Forecast: predict donors per day up to 28 days ahead, using only the calendar and the usual level a month earlier.

Tested on Jan-Jun 2023 in 28-day blocks; every forecast uses only data before its block (no peeking).
Compared with two simple baselines: the mean of the last 28 days, and the same weekday last week.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import FORECAST_HORIZON, FORECAST_START, LEVEL_WINDOW, SEASONS, WEEKDAY_TERM
from .models import fit_poisson

METHODS = ["Model", "Mean_last_28", "Same_weekday_last_week"]


@dataclass
class ForecastResult:
    forecast: pd.DataFrame        # one row per test day, with every method's prediction
    errors: pd.DataFrame          # mean absolute error per method, for all / season / ordinary days
    block_starts: pd.DatetimeIndex
    improvement: float            # how much lower the model's error is than the 28-day mean's


def run_forecast(daily: pd.DataFrame) -> ForecastResult:
    assert "salary_27_window" in daily.columns and "s_ramadan_last10" in daily.columns, \
        "Add the payday and season flags first"
    test_end = daily["Gregorian_Date"].max()
    fc = daily.set_index("Gregorian_Date").copy()
    ordinary = fc["Donors"].where(fc["any_season"] == 0)
    # Usual level = mean donors on ordinary (non-season) days in the 56 days that end 28 days before the date:
    # known at least 28 days in advance, so it can be used for any day in a 28-day forecast block.
    fc["level"] = ordinary.shift(FORECAST_HORIZON).rolling(LEVEL_WINDOW, min_periods=14).mean()
    terms = f"{WEEKDAY_TERM} + " + " + ".join(list(SEASONS) + [c for c in fc.columns if c.endswith("_window")])

    block_starts, predictions = pd.date_range(FORECAST_START, test_end, freq=f"{FORECAST_HORIZON}D"), []
    for origin in block_starts:
        train = fc[(fc.index < origin) & fc["has_data"] & fc["level"].notna()].reset_index()
        end = origin + pd.Timedelta(days=FORECAST_HORIZON)
        test = fc[(fc.index >= origin) & (fc.index < end) & (fc.index <= test_end)].reset_index()
        model = fit_poisson(f"Donors ~ {terms}", train, hac=False, offset=np.log(train["level"]))
        past = fc[(fc.index < origin) & fc["has_data"]]
        last_week = past["Donors"].iloc[-7:]
        test["Model"] = model.predict(test, offset=np.log(test["level"]))
        test["Mean_last_28"] = past["Donors"].iloc[-28:].mean()
        test["Same_weekday_last_week"] = test["Weekday"].map(dict(zip(past.loc[last_week.index, "Weekday"], last_week)))
        test["Origin"] = origin
        predictions.append(test)
    forecast = pd.concat(predictions, ignore_index=True)
    forecast = forecast[forecast["has_data"]].copy()

    def mae(group: pd.DataFrame) -> pd.Series:
        return pd.Series({m: (group[m] - group["Donors"]).abs().mean() for m in METHODS} | {"Days": len(group)})

    errors = pd.concat({
        "All test days": mae(forecast),
        "Season days": mae(forecast[forecast["any_season"] == 1]),
        "Ordinary days": mae(forecast[forecast["any_season"] == 0]),
    }, axis=1).T.round(1)
    errors["Days"] = errors["Days"].astype(int)
    improvement = 1 - errors.loc["All test days", "Model"] / errors.loc["All test days", "Mean_last_28"]

    assert forecast["Gregorian_Date"].min() >= FORECAST_START and forecast["Model"].notna().all()
    return ForecastResult(forecast=forecast, errors=errors, block_starts=block_starts, improvement=improvement)
