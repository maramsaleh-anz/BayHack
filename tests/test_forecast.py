"""The "which days to pick" test: top-share arithmetic and the claims made on the slide."""
import pandas as pd
import pytest

from bayyin.forecast import top_share

TABLE = "outputs/tables/forecast_capture.csv"


def test_top_share_counts_whole_days_and_splits_ties():
    donors = pd.Series([10, 20, 30, 40])
    assert top_share(donors, donors, 0.25) == pytest.approx(0.4)                      # best day only
    assert top_share(donors, pd.Series([0, 0, 0, 0]), 0.5) == pytest.approx(0.5)      # all tied = random
    assert top_share(donors, pd.Series([1, 0, 0, 0]), 0.5) == pytest.approx((10 + 90 / 3) / 100)


def test_model_beats_the_calendar_alone_on_ordinary_days():
    t = pd.read_csv(TABLE).set_index(["Days_group", "Top_days"])
    ordinary = t.loc[("Ordinary days", "10%")]
    assert ordinary["Model"] > ordinary["Seasons_only"] and ordinary["Model"] > ordinary["Same_weekday_last_week"]
    all_days = t.loc[("All test days", "10%")]
    assert all_days[["Model", "Perfect_hindsight"]].tolist() == [30.7, 31.3]           # the numbers on the slide
