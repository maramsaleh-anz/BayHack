"""Paths, constants and analysis choices for the Bayyin analysis.

Everything that is a *choice* (not a computation) lives here, so it can be read and changed in one place.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

# ---------------------------------------------------------------- paths
REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = REPO_ROOT / "data_clean" / "ehsan_rows_2021-04_2023-06.csv"
OUT_DIR = REPO_ROOT / "outputs"
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"

# ---------------------------------------------------------------- columns of the cleaned file
ANALYSIS_COLS = ["RowID", "UserID_clean", "Gregorian_Date", "Hijri_Year", "Hijri_Month", "Hijri_Month_Name",
                 "Hijri_Day", "Hijri_Month_Complete", "InitiativeName_clean", "Amount_num"]
TEMP_COLS = ["Recurring_01", "flag_dup_extra", "dup_group", "dup_group_size"]  # used while cleaning, then dropped
CALENDAR_COLS = ["Hijri_Year", "Hijri_Month", "Hijri_Month_Name", "Hijri_Day", "Hijri_Month_Complete"]

# ---------------------------------------------------------------- paydays
# program -> (day of month, shift if the day is a Friday, shift if it is a Saturday)
WEEKEND_SHIFT: dict[str, tuple[int, int, int]] = {
    "salary_27": (27, -1, +1),        # state employees: Fri -> 26, Sat -> 28
    "pension_25": (25, -1, +1),       # civil & military retirement: Fri -> 24, Sat -> 26
    "citizen_10": (10, -1, +1),       # Citizen Account: Fri -> 9, Sat -> 11
    "day1_group": (1, -1, -2),        # GOSI pensions + Saned + social security (from Jun 2022): Fri/Sat -> Thursday (to verify)
}
# An official announcement for a specific month overrides the rule: (program, "YYYY-MM") -> (date, source)
PAYDAY_OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    ("citizen_10", "2022-07"): ("2022-07-06", "Citizen Account spokesperson via Al-Marsd (payment 56)"),
}
PROGRAM_LABEL = {
    "salary_27": "State salaries (27th)",
    "pension_25": "Civil/military pensions (25th)",
    "citizen_10": "Citizen Account (10th)",
    "day1_group": "Day-1 payments (GOSI pensions, Saned, social security)",
}
PAYDAY_WINDOW_DAYS = 3  # main window = payday + 3 days (fixed before looking at the results)
PAYDAY_WINDOWS = [f"{program}_window" for program in WEEKEND_SHIFT]

# ---------------------------------------------------------------- religious seasons (Hijri month, day)
SeasonRule = Callable[[pd.Series, pd.Series], pd.Series]
SEASONS: dict[str, tuple[str, SeasonRule]] = {
    "s_ramadan_1_20": ("Ramadan, days 1-20", lambda m, d: (m == 9) & (d <= 20)),
    "s_ramadan_last10": ("Ramadan, last 10 days", lambda m, d: (m == 9) & (d >= 21)),
    "s_eid_fitr": ("Eid al-Fitr (Shawwal 1-3)", lambda m, d: (m == 10) & (d <= 3)),
    "s_dhul_hijjah_1_9": ("Dhu al-Hijjah 1-9 (incl. Arafah)", lambda m, d: (m == 12) & (d <= 9)),
    "s_eid_adha": ("Eid al-Adha + Tashreeq (10-13)", lambda m, d: (m == 12) & d.between(10, 13)),
    "s_muharram": ("Muharram", lambda m, d: m == 1),
}
# The payday model controls for these seasons only (Muharram is not a control there; as in the original analysis).
PAYDAY_MODEL_SEASONS = [key for key in SEASONS if key != "s_muharram"]

# ---------------------------------------------------------------- model choices
HAC_MAXLAGS = 7           # days are not independent: robust (HAC) errors with a one-week memory
TREND_DF = 4              # smooth trend for the growth of the sample
WEEKDAY_TERM = "C(Weekday, Treatment('Sunday'))"
FRIDAY_TERM = "C(Weekday, Treatment('Sunday'))[T.Friday]"
WEEK_ORDER = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def trend_term(df: int = TREND_DF) -> str:
    """Formula term for the smooth trend."""
    return f"cr(t, df={df}, constraints='center')"


# ---------------------------------------------------------------- forecast
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_HORIZON = 28     # days ahead
LEVEL_WINDOW = 56         # days used for the "usual level"

# ---------------------------------------------------------------- robustness: the 5 candidate periods and the 9 variants
CANDIDATE_TERMS = {
    "Ramadan, last 10 days": "s_ramadan_last10",
    "Ramadan, days 1-20": "s_ramadan_1_20",
    "Dhu al-Hijjah 1-9 (incl. Arafah)": "s_dhul_hijjah_1_9",
    "Friday (vs Sunday)": FRIDAY_TERM,
    "State salaries (27th)": "salary_27_window",
}
ROBUSTNESS_VARIANTS: dict[str, dict] = {
    "Outcome: donations (not donors)": dict(outcome="Donations"),
    "Outcome: amount, capped at p99": dict(outcome="Amount_capped"),
    "Outcome: donations without merging duplicates": dict(outcome="Donations_with_dups"),
    "Payday window: payday only": dict(window_days=0),
    "Payday window: payday + 1 day": dict(window_days=1),
    "Payday window: payday + 5 days": dict(window_days=5),
    "Trend: less flexible (df=2)": dict(trend_df=2),
    "Trend: more flexible (df=8)": dict(trend_df=8),
    "Start in January 2022": dict(start="2022-01-01"),
}

# ---------------------------------------------------------------- chart colours
BLUE, GREY, ORANGE, LIGHT_GREY = "#2a78d6", "#52514e", "#e8692f", "#c9c7bf"
