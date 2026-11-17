"""Robustness: re-run the main model 9 times, changing ONE choice each time.

A period stays a candidate only if its rise is clear (CI fully above 0) in every variant.
"""
from __future__ import annotations

import pandas as pd

from .config import CANDIDATE_TERMS, PAYDAY_WINDOW_DAYS, ROBUSTNESS_VARIANTS, TREND_DF, WEEKEND_SHIFT
from .models import base_formula, fit_poisson, pct_change


def run_robustness(daily: pd.DataFrame, donor_day: pd.DataFrame, analysis: pd.DataFrame,
                   excluded_duplicates: pd.DataFrame, candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (robustness: one row per variant and period, robustness_summary: one row per period)."""
    # Alternative outcomes, built from the same tables as the main analysis
    amount_cap = donor_day["Amount"].quantile(0.99)
    amount_capped = donor_day.assign(A=donor_day["Amount"].clip(upper=amount_cap)).groupby("Gregorian_Date")["A"].sum()
    with_duplicates = (pd.concat([analysis[["Gregorian_Date"]], excluded_duplicates[["Gregorian_Date"]]])
                       .groupby("Gregorian_Date").size())

    def windows_for(days_after: int) -> pd.DataFrame:
        windows = pd.DataFrame(index=daily.index)
        for program in WEEKEND_SHIFT:
            windows[f"{program}_window"] = daily[f"{program}_days_since"].between(0, days_after).astype(int)
        return windows

    def fit_variant(outcome="Donors", window_days=PAYDAY_WINDOW_DAYS, trend_df=TREND_DF, start=None) -> dict:
        d = daily.drop(columns=[c for c in daily.columns if c.endswith("_window")]).join(windows_for(window_days))
        d = d[d["has_data"]].copy()
        if outcome == "Donations":
            d["y"] = d["Donations"]
        elif outcome == "Amount_capped":
            d["y"] = d["Gregorian_Date"].map(amount_capped)
        elif outcome == "Donations_with_dups":
            d["y"] = d["Gregorian_Date"].map(with_duplicates)
        else:
            d["y"] = d["Donors"]
        if start:
            d = d[d["Gregorian_Date"] >= start]
        d["y"] = d["y"].round().astype(int)
        d["t"] = (d["Gregorian_Date"] - d["Gregorian_Date"].min()).dt.days
        windows = [c for c in d.columns if c.endswith("_window")]
        model = fit_poisson(base_formula(outcome="y", windows=windows, trend_df=trend_df), d)
        ci = model.conf_int()
        return {label: (pct_change(model.params[term]), pct_change(ci.loc[term, 0]))
                for label, term in CANDIDATE_TERMS.items()}

    rows = []
    for variant, options in ROBUSTNESS_VARIANTS.items():
        for label, (change, ci_low) in fit_variant(**options).items():
            rows.append({"Variant": variant, "Factor": label, "Change_%": round(change, 1),
                         "CI_low_%": round(ci_low, 1), "Clear_rise": ci_low > 0})
    robustness = pd.DataFrame(rows)

    summary = (robustness.groupby("Factor", sort=False)
               .agg(Min_change_pct=("Change_%", "min"), Max_change_pct=("Change_%", "max"),
                    Survived=("Clear_rise", "sum"), Variants=("Clear_rise", "size"))
               .reset_index())
    summary.insert(1, "Main_change_pct", summary["Factor"].map(candidates.set_index("Factor")["Change_%"]))
    summary["Survived"] = summary["Survived"].astype(int).astype(str) + " of " + summary["Variants"].astype(str)
    summary = summary.drop(columns="Variants")

    assert len(robustness) == len(ROBUSTNESS_VARIANTS) * len(CANDIDATE_TERMS)
    return robustness, summary
