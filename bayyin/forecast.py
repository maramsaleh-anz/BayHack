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
    capture: pd.DataFrame         # share of donors in the top 10% / 20% of days, as ranked by each method


# Ranking methods for the "which days to pick" test. Seasons_only knows nothing but the Hijri calendar:
# last 10 of Ramadan > Ramadan 1-20 > Dhu al-Hijjah 1-9 > every other day (ties shared evenly).
RANKERS = ["Perfect_hindsight", "Model", "Seasons_only", "Same_weekday_last_week", "Random"]
SEASON_PRIORITY = {"s_ramadan_last10": 3, "s_ramadan_1_20": 2, "s_dhul_hijjah_1_9": 1}
TOP_SHARES = (0.10, 0.20)


def top_share(donors: pd.Series, score: pd.Series, share: float) -> float:
    """Share of all donors that fall on the top `share` of days when days are ranked by `score`.

    Tied days at the cut-off count in proportion (the expected value of breaking the tie at random), so the
    result is deterministic and a method gets no credit for an arbitrary tie order.
    """
    k = round(share * len(donors))  # whole days, as on the slide (18 of 181, 36 of 181)
    by_score = pd.DataFrame({"d": donors.to_numpy(), "s": score.to_numpy()}).groupby("s")["d"].agg(["sum", "size"])
    taken = total = 0.0
    for _, row in by_score.sort_index(ascending=False).iterrows():
        use = min(row["size"], k - taken)
        if use <= 0:
            break
        total += row["sum"] * use / row["size"]
        taken += use
    return total / donors.sum()


def capture_table(forecast: pd.DataFrame) -> pd.DataFrame:
    """For all test days and for ordinary (non-season) days: % of donors in the top 10% / 20% of days per method."""
    season_rank = sum(forecast[col] * w for col, w in SEASON_PRIORITY.items())
    scores = {"Perfect_hindsight": forecast["Donors"], "Model": forecast["Model"], "Seasons_only": season_rank,
              "Same_weekday_last_week": forecast["Same_weekday_last_week"], "Random": pd.Series(0, index=forecast.index)}
    rows = []
    for group, mask in (("All test days", forecast["any_season"] >= 0), ("Ordinary days", forecast["any_season"] == 0)):
        for share in TOP_SHARES:
            row = {"Days_group": group, "Top_days": f"{share:.0%}", "Days": int(mask.sum())}
            row |= {m: round(100 * top_share(forecast.loc[mask, "Donors"], scores[m][mask], share), 1) for m in RANKERS}
            rows.append(row)
    return pd.DataFrame(rows)


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
    return ForecastResult(forecast=forecast, errors=errors, block_starts=block_starts, improvement=improvement,
                          capture=capture_table(forecast))
