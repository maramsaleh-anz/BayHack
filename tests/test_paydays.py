"""STEP 6: the payday calendar and the payday windows."""
import pandas as pd

from bayyin.config import PAYDAY_WINDOW_DAYS, WEEKEND_SHIFT
from bayyin.paydays import add_payday_flags, build_payday_calendar

calendar = build_payday_calendar("2021-03-01", "2023-07-01")


def pay_date(program: str, month: str) -> pd.Timestamp:
    row = calendar[(calendar["Program"] == program) & (calendar["Month"] == month)]
    return row["Pay_Date"].iloc[0]


def test_salary_is_paid_on_the_27th_unless_it_is_a_weekend():
    assert pay_date("salary_27", "2022-06") == pd.Timestamp("2022-06-27")   # a Monday
    assert pay_date("salary_27", "2022-05") == pd.Timestamp("2022-05-26")   # 27th is a Friday -> Thursday
    assert pay_date("salary_27", "2022-08") == pd.Timestamp("2022-08-28")   # 27th is a Saturday -> Sunday


def test_every_rule_based_payday_avoids_friday_and_saturday():
    rule_based = calendar[calendar["Status"] != "announced"]
    assert not rule_based["Pay_Date"].dt.dayofweek.isin([4, 5]).any()


def test_an_official_announcement_overrides_the_rule():
    row = calendar[(calendar["Program"] == "citizen_10") & (calendar["Month"] == "2022-07")].iloc[0]
    assert row["Pay_Date"] == pd.Timestamp("2022-07-06") and row["Status"] == "announced"


def test_one_payday_per_program_and_month():
    assert not calendar.duplicated(["Program", "Month"]).any()
    assert calendar["Program"].nunique() == len(WEEKEND_SHIFT)


def test_window_is_the_payday_and_the_three_days_after():
    days = pd.DataFrame({"Gregorian_Date": pd.date_range("2022-06-24", "2022-07-03")})
    flagged = add_payday_flags(days, calendar).set_index("Gregorian_Date")
    window = flagged["salary_27_window"]
    assert window["2022-06-26"] == 0
    assert list(window["2022-06-27":"2022-06-30"]) == [1] * (PAYDAY_WINDOW_DAYS + 1)
    assert window["2022-07-01"] == 0
    assert flagged.loc["2022-06-29", "salary_27_days_since"] == 2


def test_flags_do_not_change_the_input_table():
    days = pd.DataFrame({"Gregorian_Date": pd.date_range("2022-06-24", "2022-07-03")})
    add_payday_flags(days, calendar)
    assert list(days.columns) == ["Gregorian_Date"]
