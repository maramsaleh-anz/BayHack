"""Hours (descriptive): when in the day do donors give?

Same donations as the analysis (no automatic charges, no duplicates). Times are as recorded in the source; the time zone
is not stated (the Ramadan suhoor/iftar pattern suggests Saudi time).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import WEEK_ORDER


@dataclass
class HoursResult:
    heat: pd.DataFrame        # weekday x hour: number of donations
    top_slots: pd.DataFrame   # the 5 busiest (weekday, hour) slots
    hour_share: pd.DataFrame  # share of the day's donations per hour: Ramadan vs rest of year
    busiest_hour: int
    busiest_share: float


def analyze_hours(raw: pd.DataFrame, analysis: pd.DataFrame) -> HoursResult:
    times = raw.set_index("RowID").loc[analysis["RowID"], ["CreationTime"]].reset_index()
    times["CreationTime"] = pd.to_datetime(times["CreationTime"])
    times = times.merge(analysis[["RowID", "Hijri_Month"]], on="RowID")
    times["Hour"] = times["CreationTime"].dt.hour
    times["Weekday"] = times["CreationTime"].dt.day_name()

    heat = times.pivot_table(index="Weekday", columns="Hour", values="RowID", aggfunc="size",
                             fill_value=0).reindex(WEEK_ORDER)
    top_slots = heat.stack().rename("Donations").sort_values(ascending=False).head(5).reset_index()
    hour_share = pd.DataFrame({
        "Ramadan": times[times["Hijri_Month"] == 9]["Hour"].value_counts(normalize=True),
        "Rest of year": times[times["Hijri_Month"] != 9]["Hour"].value_counts(normalize=True),
    }).reindex(range(24), fill_value=0)

    assert heat.values.sum() == len(analysis)
    overall = times["Hour"].value_counts()
    return HoursResult(heat=heat, top_slots=top_slots, hour_share=hour_share,
                       busiest_hour=int(overall.idxmax()), busiest_share=float(times["Hour"].value_counts(normalize=True).max()))
