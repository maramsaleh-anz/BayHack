"""The model specification is part of the result: guard it."""
import numpy as np

from bayyin.config import CANDIDATE_TERMS, PAYDAY_MODEL_SEASONS, PAYDAY_WINDOWS, ROBUSTNESS_VARIANTS, SEASONS
from bayyin.models import base_formula, pct_change


def test_pct_change_turns_a_log_coefficient_into_a_percentage():
    assert pct_change(0) == 0
    assert round(pct_change(np.log(2)), 6) == 100
    assert round(pct_change(np.log(0.5)), 6) == -50


def test_main_model_formula():
    assert base_formula(windows=PAYDAY_WINDOWS) == (
        "Donors ~ C(Weekday, Treatment('Sunday')) + cr(t, df=4, constraints='center') + "
        + " + ".join(SEASONS) + " + salary_27_window + pension_25_window + citizen_10_window + day1_group_window")


def test_payday_model_has_no_muharram_term():
    formula = base_formula(seasons=PAYDAY_MODEL_SEASONS, windows=PAYDAY_WINDOWS)
    assert "s_muharram" not in formula and "s_eid_adha" in formula


def test_trend_flexibility_can_be_changed_for_the_robustness_runs():
    assert "cr(t, df=8, constraints='center')" in base_formula(outcome="y", trend_df=8)
    assert base_formula(outcome="y").startswith("y ~ ")


def test_robustness_design_is_nine_variants_of_five_periods():
    assert len(ROBUSTNESS_VARIANTS) == 9 and len(CANDIDATE_TERMS) == 5
