"""Steps 1-5: from the cleaned file to the donor-day table and the daily table."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from hijridate import Gregorian

from .config import ANALYSIS_COLS, CALENDAR_COLS, INPUT_CSV, TEMP_COLS


def load_clean(path: Path = INPUT_CSV) -> pd.DataFrame:
    """Read the cleaned file (semicolon separated, UTF-8 with BOM)."""
    with open(path, encoding="utf-8-sig") as f:
        header = f.readline()
    assert "Recurring_01" in header and "flag_dup_extra" in header, \
        "This is not the final cleaned file - run CELL 1-8 in the cleaning notebook and download it again"
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype={"UserID_clean": str}, parse_dates=["Gregorian_Date"])


def select_columns(raw: pd.DataFrame) -> pd.DataFrame:
    """STEP 1 - keep only the columns the analysis needs (plus the ones used to clean)."""
    df = raw[ANALYSIS_COLS + TEMP_COLS].copy()
    assert len(df) == len(raw) and df["Amount_num"].sum() == raw["Amount_num"].sum()
    assert df["RowID"].is_unique
    return df


def drop_automatic_charges(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """STEP 2 - remove automatic charges (Recurring_01 = 1): their time is set by the system, not the donor.

    Returns (kept rows, excluded rows).
    """
    is_auto = df["Recurring_01"] == 1
    excluded = df[is_auto].copy()
    kept = df[~is_auto].drop(columns="Recurring_01").reset_index(drop=True)
    assert len(kept) + len(excluded) == len(df)
    assert kept["Amount_num"].sum() + excluded["Amount_num"].sum() == df["Amount_num"].sum()
    return kept, excluded


def merge_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """STEP 3 - merge duplicate copies (flag_dup_extra): one transaction per group, first row kept.

    Returns (kept rows with a `Copies_merged` column, excluded rows).
    """
    is_extra = df["flag_dup_extra"].astype(bool)
    excluded = df[is_extra].copy()
    kept = df[~is_extra].reset_index(drop=True)
    kept["Copies_merged"] = kept["dup_group_size"].astype(int)  # 1 = no duplicate
    kept = kept.drop(columns=["flag_dup_extra", "dup_group", "dup_group_size"])
    assert len(kept) + len(excluded) == len(df)
    assert kept["Amount_num"].sum() + excluded["Amount_num"].sum() == df["Amount_num"].sum()
    assert kept["Copies_merged"].sum() == len(df)
    return kept, excluded


def build_donor_day(analysis: pd.DataFrame) -> pd.DataFrame:
    """STEP 4 - one row per donor per day (all donations of the same donor on the same date combined)."""
    donor_day = (analysis
                 .groupby(["UserID_clean", "Gregorian_Date"])
                 .agg(Donations=("RowID", "size"), Amount=("Amount_num", "sum"),
                      Initiatives=("InitiativeName_clean", "nunique"), **{c: (c, "first") for c in CALENDAR_COLS})
                 .reset_index())
    assert not donor_day.duplicated(["UserID_clean", "Gregorian_Date"]).any()
    assert donor_day["Donations"].sum() == len(analysis)
    assert donor_day["Amount"].sum() == analysis["Amount_num"].sum()
    return donor_day


def build_daily(donor_day: pd.DataFrame, analysis: pd.DataFrame) -> pd.DataFrame:
    """STEP 5 - one row per calendar day. Days without data stay EMPTY (NaN), not 0."""
    days = pd.date_range(donor_day["Gregorian_Date"].min(), donor_day["Gregorian_Date"].max(), freq="D")
    hijri = [Gregorian(d.year, d.month, d.day).to_hijri() for d in days]
    daily = pd.DataFrame({"Gregorian_Date": days, "Weekday": days.day_name(),
                          "Hijri_Year": [h.year for h in hijri], "Hijri_Month": [h.month for h in hijri],
                          "Hijri_Month_Name": [h.month_name("ar") for h in hijri], "Hijri_Day": [h.day for h in hijri]})
    totals = donor_day.groupby("Gregorian_Date").agg(Donors=("UserID_clean", "size"), Donations=("Donations", "sum"),
                                                     Amount=("Amount", "sum"))
    daily = daily.merge(totals, left_on="Gregorian_Date", right_index=True, how="left")
    daily["has_data"] = daily["Donors"].notna()
    assert daily["Donors"].sum() == len(donor_day) and daily["Donations"].sum() == len(analysis)
    assert daily["Amount"].sum() == analysis["Amount_num"].sum()
    return daily
