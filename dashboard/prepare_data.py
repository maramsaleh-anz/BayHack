"""Aggregate the cleaned donations into the small tables the dashboard reads (data_clean/dashboard_data/*.csv).

    python dashboard/prepare_data.py            # uses the default paths
    python dashboard/prepare_data.py --help

`model_results.csv` is derived from the analysis tables in outputs/tables/ (run `python -m bayyin` first if they are missing).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data_clean" / "ehsan_rows_2021-04_2023-06.csv"
DEFAULT_TABLES = REPO_ROOT / "outputs" / "tables"
DEFAULT_OUT = REPO_ROOT / "data_clean" / "dashboard_data"

# pandas dayofweek (Monday = 0) -> Arabic name, and the position in a Sunday-first week
WEEKDAY_AR = {6: "الأحد", 0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة", 5: "السبت"}
WEEKDAY_ORDER = {6: 1, 0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7}
RAMADAN, DHUL_HIJJAH = 9, 12   # Hijri month numbers
PERIOD_AR = {True: "رمضان", False: "باقي السنة"}


# ---------------------------------------------------------------- input
def load_donations(source: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (manual donations without duplicates, all rows). Automatic charges and duplicate copies are removed."""
    raw = pd.read_csv(source, sep=";", encoding="utf-8-sig", dtype={"UserID_clean": str},
                      parse_dates=["Gregorian_Date", "CreationTime"])
    df = raw[raw["Recurring_01"] != 1]
    df = df[~df["flag_dup_extra"].astype(bool)].copy()
    df["hour"] = df.CreationTime.dt.hour
    df["wd"] = df.CreationTime.dt.dayofweek
    df["weekday"] = df.wd.map(WEEKDAY_AR)
    df["weekday_order"] = df.wd.map(WEEKDAY_ORDER)
    return df, raw


# ---------------------------------------------------------------- tables
def weekday_hour_table(df: pd.DataFrame) -> pd.DataFrame:
    """Donations, donors and amount for every (weekday, hour), including the empty slots."""
    grouped = (df.groupby(["weekday_order", "weekday", "hour"])
               .agg(donations=("RowID", "size"), donors=("UserID_clean", "nunique"), amount=("Amount_num", "sum"))
               .reset_index())
    full = pd.MultiIndex.from_product([range(1, 8), range(24)], names=["weekday_order", "hour"]).to_frame(index=False)
    full["weekday"] = full.weekday_order.map({v: WEEKDAY_AR[k] for k, v in WEEKDAY_ORDER.items()})
    table = full.merge(grouped, how="left", on=["weekday_order", "weekday", "hour"]).fillna(0)
    for column in ["donations", "donors", "amount"]:
        table[column] = table[column].astype(int)
    return table


def daily_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar day (days without donations stay empty): donors, donations, amount and the Hijri date."""
    donor_day = (df.groupby(["UserID_clean", "Gregorian_Date"])
                 .agg(n=("RowID", "size"), amt=("Amount_num", "sum")).reset_index())
    daily = donor_day.groupby("Gregorian_Date").agg(donors=("UserID_clean", "size"), donations=("n", "sum"),
                                                    amount=("amt", "sum"))
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max()))
    daily.index.name = "date"
    hijri = df.groupby("Gregorian_Date").agg(hijri_month=("Hijri_Month", "first"),
                                             hijri_month_name=("Hijri_Month_Name", "first"),
                                             hijri_day=("Hijri_Day", "first"))
    daily = daily.join(hijri).reset_index()
    daily["date"] = daily.date.dt.strftime("%Y-%m-%d")
    return daily


def weekday_table(days: pd.DataFrame) -> pd.DataFrame:
    """Average donors and donations per day of the week (days with data only)."""
    d = days.assign(wd=pd.to_datetime(days.date).dt.dayofweek)
    table = d.groupby("wd").agg(avg_donors=("donors", "mean"), avg_donations=("donations", "mean"),
                                days=("donors", "size")).reset_index()
    table["weekday"] = table.wd.map(WEEKDAY_AR)
    table["weekday_order"] = table.wd.map(WEEKDAY_ORDER)
    table = table.sort_values("weekday_order").drop(columns="wd")
    table[["avg_donors", "avg_donations"]] = table[["avg_donors", "avg_donations"]].round(1)
    return table[["weekday_order", "weekday", "avg_donors", "avg_donations", "days"]]


def hijri_month_table(days: pd.DataFrame) -> pd.DataFrame:
    """Average donors per day in each Hijri month (all days, seasons included)."""
    table = (days.groupby(["hijri_month", "hijri_month_name"])
             .agg(avg_donors=("donors", "mean"), days=("donors", "size"), donations=("donations", "sum"),
                  amount=("amount", "sum")).reset_index())
    table["avg_donors"] = table.avg_donors.round(1)
    table["hijri_month"] = table.hijri_month.astype(int)
    return table


def day_of_month_table(days: pd.DataFrame) -> pd.DataFrame:
    """Average donors per Gregorian day of the month, outside Ramadan and Dhu al-Hijjah."""
    d = days.assign(dom=pd.to_datetime(days.date).dt.day)
    off_season = d[~d.hijri_month.isin([RAMADAN, DHUL_HIJJAH])]
    table = off_season.groupby("dom").agg(avg_donors=("donors", "mean"), days=("donors", "size")).reset_index()
    table["avg_donors"] = table.avg_donors.round(1)
    return table


def ramadan_days_table(days: pd.DataFrame) -> pd.DataFrame:
    """Average donors on each day of Ramadan."""
    table = (days[days.hijri_month == RAMADAN].groupby("hijri_day")
             .agg(avg_donors=("donors", "mean"), days=("donors", "size")).reset_index())
    table["avg_donors"] = table.avg_donors.round(1)
    table["hijri_day"] = table.hijri_day.astype(int)
    return table


def top_projects_table(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    return (df.groupby("Title_clean")
            .agg(donations=("RowID", "size"), donors=("UserID_clean", "nunique"), amount=("Amount_num", "sum"))
            .sort_values("donations", ascending=False).head(limit).reset_index()
            .rename(columns={"Title_clean": "project"}))


def hourly_table(df: pd.DataFrame, days: pd.DataFrame) -> pd.DataFrame:
    """Donations per hour of the day, per day, and as a share of the day: Ramadan vs the rest of the year."""
    period = (df.Hijri_Month == RAMADAN).map(PERIOD_AR)
    day_counts = days.assign(period=(days.hijri_month == RAMADAN).map(PERIOD_AR)).groupby("period").size()
    by_hour = df.assign(period=period).groupby(["period", "hour"]).size().unstack(0).reindex(range(24), fill_value=0)
    table = pd.DataFrame({"hour": range(24)})
    table["ramadan_per_day"] = (by_hour[PERIOD_AR[True]].values / day_counts[PERIOD_AR[True]]).round(2)
    table["other_per_day"] = (by_hour[PERIOD_AR[False]].values / day_counts[PERIOD_AR[False]]).round(2)
    table["ramadan_share"] = (by_hour[PERIOD_AR[True]] / by_hour[PERIOD_AR[True]].sum()).round(4).values
    table["other_share"] = (by_hour[PERIOD_AR[False]] / by_hour[PERIOD_AR[False]].sum()).round(4).values
    table["all_donations"] = by_hour.sum(axis=1).values
    return table


def summary_table(df: pd.DataFrame, raw: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    manual = raw[raw.Recurring_01 != 1]
    return pd.DataFrame([{
        "donations": len(df), "donors": df.UserID_clean.nunique(), "amount": int(df.Amount_num.sum()),
        "days_with_data": int(daily.donors.notna().sum()), "avg_donors_per_day": round(daily.donors.mean(), 1),
        "median_donors_per_day": float(daily.donors.median()), "start": daily.date.min(), "end": daily.date.max(),
        "excluded_recurring": int((raw.Recurring_01 == 1).sum()),
        "merged_duplicates": int(manual.flag_dup_extra.astype(bool).sum()),
    }])


# ---------------------------------------------------------------- model results (from the analysis tables)
# English factor (as in outputs/tables) -> (key used by the dashboard, Arabic name)
SEASON_NAMES = {
    "Ramadan, days 1-20": ("ramadan_1_20", "رمضان (الأيام 1–20)"),
    "Ramadan, last 10 days": ("ramadan_last10", "العشر الأواخر من رمضان"),
    "Eid al-Fitr (Shawwal 1-3)": ("eid_fitr", "عيد الفطر (شوال 1–3)"),
    "Dhu al-Hijjah 1-9 (incl. Arafah)": ("dhul_hijjah_1_9", "ذو الحجة 1–9 (مع عرفة)"),
    "Eid al-Adha + Tashreeq (10-13)": ("eid_adha", "عيد الأضحى والتشريق (10–13)"),
    "Muharram": ("muharram", "محرم"),
}
WEEKDAY_NAMES = {f"{en} (vs Sunday)": (en.lower(), f"{ar} (مقارنة بالأحد)") for en, ar in [
    ("Monday", "الاثنين"), ("Tuesday", "الثلاثاء"), ("Wednesday", "الأربعاء"), ("Thursday", "الخميس"),
    ("Friday", "الجمعة"), ("Saturday", "السبت")]}
PAYDAY_NAMES = {
    "State salaries (27th)": ("salary_27", "رواتب الدولة (27)"),
    "Civil/military pensions (25th)": ("pension_25", "التقاعد المدني والعسكري (25)"),
    "Citizen Account (10th)": ("citizen_10", "حساب المواطن (10)"),
    "Day-1 payments (GOSI pensions, Saned, social security)": ("day1_group", "صرف أول الشهر (التأمينات، ساند، الضمان)"),
}
KINDS = {"season": "موسم", "weekday": "يوم الأسبوع", "payday": "الرواتب (يوم الصرف + 3 أيام)"}
CONCLUSIONS_AR = {
    "Clear rise": "ارتفاع واضح", "Clear drop": "انخفاض واضح", "No clear difference": "لا فرق واضح",
    "Not consistent (model and check disagree)": "غير متسق (النموذج والتحقق مختلفان)",
    "Rise, but mostly the salary days (overlap)": "ارتفاع، لكنه يتداخل مع أيام الرواتب",
    "Not confirmed by the event view": "لم تؤكده المقارنة الثانية", "No clear rise": "لا ارتفاع واضح",
}


def model_results_table(tables_dir: Path) -> pd.DataFrame:
    """The dashboard's list of effects: ranked candidates first, then the others from the highest to the lowest change."""
    read = lambda name: pd.read_csv(tables_dir / f"{name}.csv", encoding="utf-8-sig")
    rank_of = read("candidate_periods").set_index("Factor")["Rank"]
    rows = []
    for table, key_column, names, kind in [(read("season_results"), "Factor", SEASON_NAMES, "season"),
                                           (read("weekday_results"), "Factor", WEEKDAY_NAMES, "weekday"),
                                           (read("payday_results"), "Payment", PAYDAY_NAMES, "payday")]:
        for _, r in table.iterrows():
            key, name = names[r[key_column]]
            rows.append({"key": key, "type": KINDS[kind], "factor": name, "change_pct": r["Change_%"],
                         "ci_low": r["CI_low_%"], "ci_high": r["CI_high_%"], "conclusion": CONCLUSIONS_AR[r["Conclusion"]],
                         "rank": rank_of.get(r[key_column])})
    result = pd.DataFrame(rows)
    ranked = result[result["rank"].notna()].sort_values("rank")
    others = result[result["rank"].isna()].sort_values("change_pct", ascending=False)
    result = pd.concat([ranked, others], ignore_index=True)
    result["rank"] = result["rank"].astype("Int64")
    return result


# ---------------------------------------------------------------- main
def prepare(source: Path = DEFAULT_INPUT, tables_dir: Path = DEFAULT_TABLES, out_dir: Path = DEFAULT_OUT) -> list[Path]:
    """Write every dashboard table. Returns the files written."""
    df, raw = load_donations(source)
    daily = daily_table(df)
    days = daily.dropna(subset=["donors"])
    tables = {
        "weekday_hour": weekday_hour_table(df), "hourly": hourly_table(df, days), "daily": daily,
        "weekday": weekday_table(days), "hijri_month": hijri_month_table(days), "day_of_month": day_of_month_table(days),
        "ramadan_days": ramadan_days_table(days), "top_projects": top_projects_table(df),
        "summary": summary_table(df, raw, daily), "model_results": model_results_table(tables_dir),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, table in tables.items():
        path = out_dir / f"{name}.csv"
        table.to_csv(path, index=False)
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="the cleaned donations CSV")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES, help="analysis tables (outputs/tables)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where the dashboard tables are written")
    args = parser.parse_args(argv)
    files = prepare(args.input, args.tables, args.out)
    print(f"Wrote {len(files)} tables to {args.out}")


if __name__ == "__main__":
    main()
