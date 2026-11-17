"""Religious seasons are defined by Hijri month and day (bayyin/config.py)."""
import pandas as pd
import pytest

from bayyin.config import PAYDAY_MODEL_SEASONS, SEASONS
from bayyin.models import add_season_flags


def flags(month: int, day: int) -> set[str]:
    row = pd.DataFrame({"Hijri_Month": [month], "Hijri_Day": [day]})
    out = add_season_flags(row)
    return {c for c in SEASONS if out[c].iloc[0] == 1}


@pytest.mark.parametrize("month, day, expected", [
    (9, 1, {"s_ramadan_1_20"}), (9, 20, {"s_ramadan_1_20"}), (9, 21, {"s_ramadan_last10"}), (9, 30, {"s_ramadan_last10"}),
    (10, 1, {"s_eid_fitr"}), (10, 3, {"s_eid_fitr"}), (10, 4, set()),
    (12, 1, {"s_dhul_hijjah_1_9"}), (12, 9, {"s_dhul_hijjah_1_9"}), (12, 10, {"s_eid_adha"}), (12, 13, {"s_eid_adha"}), (12, 14, set()),
    (1, 15, {"s_muharram"}), (5, 5, set()),
])
def test_season_of_a_hijri_date(month, day, expected):
    assert flags(month, day) == expected


def test_seasons_never_overlap_and_any_season_is_their_union():
    days = pd.DataFrame([(m, d) for m in range(1, 13) for d in range(1, 31)], columns=["Hijri_Month", "Hijri_Day"])
    out = add_season_flags(days)
    assert (out[list(SEASONS)].sum(axis=1) <= 1).all()
    assert (out["any_season"] == out[list(SEASONS)].sum(axis=1)).all()


def test_the_payday_model_controls_for_every_season_except_muharram():
    assert set(SEASONS) - set(PAYDAY_MODEL_SEASONS) == {"s_muharram"}
