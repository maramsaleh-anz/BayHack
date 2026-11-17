"""Steps 1-5: cleaning and the donor-day / daily tables, on small hand-made data."""
import pandas as pd
import pytest

from bayyin import data


def donations(**extra) -> pd.DataFrame:
    """Six donations: 2 automatic charges, 1 duplicate copy (of row R3), 3 real ones."""
    base = {
        "RowID": ["R1", "R2", "R3", "R4", "R5", "R6"],
        "UserID_clean": ["A", "A", "B", "B", "C", "C"],
        "Gregorian_Date": pd.to_datetime(["2022-04-02", "2022-04-02", "2022-04-03", "2022-04-03", "2022-04-05", "2022-04-05"]),
        "Hijri_Year": 1443, "Hijri_Month": [9, 9, 9, 9, 9, 9], "Hijri_Month_Name": "رمضان",
        "Hijri_Day": [1, 1, 2, 2, 4, 4], "Hijri_Month_Complete": False, "InitiativeName_clean": "مشروع",
        "Amount_num": [10, 20, 30, 30, 40, 50],
        "Recurring_01": [1, 1, 0, 0, 0, 0],
        "flag_dup_extra": [False, False, False, True, False, False],
        "dup_group": [None, None, "G1", "G1", None, None],
        "dup_group_size": [1, 1, 2, 2, 1, 1],
    }
    base.update(extra)
    return pd.DataFrame(base)


def test_automatic_charges_are_separated_and_nothing_is_lost():
    kept, excluded = data.drop_automatic_charges(donations())
    assert list(excluded["RowID"]) == ["R1", "R2"]
    assert "Recurring_01" not in kept.columns
    assert kept["Amount_num"].sum() + excluded["Amount_num"].sum() == 180


def test_duplicates_are_merged_and_copies_are_counted():
    kept, _ = data.drop_automatic_charges(donations())
    kept, excluded = data.merge_duplicates(kept)
    assert list(excluded["RowID"]) == ["R4"]
    assert kept.set_index("RowID").loc["R3", "Copies_merged"] == 2     # R3 stands for two copies
    assert kept["Copies_merged"].sum() == 4                              # = rows before merging


def test_merge_stops_if_the_input_is_not_the_cleaned_file():
    bad = donations(dup_group_size=[1, 1, 1, 1, 1, 1])                   # sizes that do not add up
    kept, _ = data.drop_automatic_charges(bad)
    with pytest.raises(AssertionError):
        data.merge_duplicates(kept)


def test_donor_day_has_one_row_per_donor_per_day():
    df = donations()
    df, _ = data.drop_automatic_charges(df)
    df, _ = data.merge_duplicates(df)
    donor_day = data.build_donor_day(df)
    assert not donor_day.duplicated(["UserID_clean", "Gregorian_Date"]).any()
    assert donor_day["Donations"].sum() == len(df)


def test_daily_table_keeps_days_without_data_empty_and_adds_hijri_dates():
    df = donations()
    df, _ = data.drop_automatic_charges(df)
    df, _ = data.merge_duplicates(df)
    daily = data.build_daily(data.build_donor_day(df), df)
    assert len(daily) == 3                                             # 3-5 April (2 April held only automatic charges)
    assert not daily.set_index("Gregorian_Date").loc["2022-04-04", "has_data"]
    assert pd.isna(daily.set_index("Gregorian_Date").loc["2022-04-04", "Donors"])
    first = daily.iloc[0]                                              # 1 Ramadan 1443 = 2 April 2022, so 3 April = 2 Ramadan
    assert (first["Hijri_Month"], first["Hijri_Day"]) == (9, 2)
