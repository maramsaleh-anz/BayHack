"""STEP 6 - payday calendar and the payday flags on the daily table."""
from __future__ import annotations

import pandas as pd

from .config import PAYDAY_OVERRIDES, PAYDAY_WINDOW_DAYS, WEEKEND_SHIFT

FRIDAY, SATURDAY = 4, 5  # pandas dayofweek (Monday = 0)


def build_payday_calendar(start: str = "2021-03-01", end: str = "2023-07-01") -> pd.DataFrame:
    """Payday of every program and month: baseline rule, overridden by an official announcement when we have one.

    One month of margin on each side of the study period is included on purpose.
    """
    rows = []
    for month in pd.date_range(start, end, freq="MS"):
        for program, (day_of_month, friday_shift, saturday_shift) in WEEKEND_SHIFT.items():
            rule_date = month + pd.Timedelta(days=day_of_month - 1)
            shift = {FRIDAY: friday_shift, SATURDAY: saturday_shift}.get(rule_date.dayofweek, 0)
            pay, status, source = rule_date + pd.Timedelta(days=shift), "rule", "baseline rule"
            if program == "day1_group" and shift:
                status = "check (weekend shift from secondary sources)"
            key = (program, month.strftime("%Y-%m"))
            if key in PAYDAY_OVERRIDES:
                announced, announced_source = PAYDAY_OVERRIDES[key]
                pay, status, source = pd.Timestamp(announced), "announced", announced_source
            rows.append({"Program": program, "Month": key[1], "Pay_Date": pay, "Weekday": pay.day_name(),
                         "Status": status, "Source": source})
    calendar = pd.DataFrame(rows)
    assert not calendar.duplicated(["Program", "Month"]).any()
    assert (calendar.query("Status != 'announced'")["Pay_Date"].dt.dayofweek.isin([FRIDAY, SATURDAY])).sum() == 0
    return calendar


def add_payday_flags(daily: pd.DataFrame, calendar: pd.DataFrame, window_days: int = PAYDAY_WINDOW_DAYS) -> pd.DataFrame:
    """Add, for every program, `<program>_days_since` (days since its last payday) and `<program>_window` (0/1).

    Returns a new table; the input is not changed.
    """
    daily = daily.copy()
    for program in WEEKEND_SHIFT:
        pays = calendar.loc[calendar["Program"] == program, ["Pay_Date"]].sort_values("Pay_Date")
        since = pd.merge_asof(daily[["Gregorian_Date"]], pays, left_on="Gregorian_Date", right_on="Pay_Date",
                              direction="backward")["Pay_Date"]
        daily[f"{program}_days_since"] = (daily["Gregorian_Date"] - since).dt.days.to_numpy()
        daily[f"{program}_window"] = daily[f"{program}_days_since"].between(0, window_days).astype(int)
    return daily


def paydays_inside(calendar: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Paydays that fall inside the study period, counted per program and status."""
    inside = calendar[calendar["Pay_Date"].between(daily["Gregorian_Date"].min(), daily["Gregorian_Date"].max())]
    return inside.groupby(["Program", "Status"]).size().rename("Paydays").reset_index()
