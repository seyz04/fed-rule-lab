import pandas as pd
import pytest

from rules import build_panel, monthly_to_quarterly, output_gap, policy_rule, year_over_year


@pytest.mark.parametrize("inflation, gap, weight, r_star, pi_star, expected", [
    (2, 0, 0.5, 2, 2, 4.0),      # on target, no gap: 2 + 2
    (4, 2, 0.5, 2, 2, 8.0),      # 2 + 4 + 0.5*2 + 0.5*2
    (4, 2, 1.0, 2, 2, 9.0),      # 2 + 4 + 0.5*2 + 1.0*2
    (1, -6, 0.5, 2, 2, -0.5),    # 2 + 1 - 0.5 - 3
    (4, 2, 0.5, 0.5, 3, 6.0),    # 0.5 + 4 + 0.5*1 + 0.5*2
])
def test_rule(inflation, gap, weight, r_star, pi_star, expected):
    assert policy_rule(inflation, gap, weight, r_star, pi_star) == expected


def test_output_gap_is_percent():
    assert output_gap(98, 100) == pytest.approx(-2)


def test_incomplete_quarters_are_dropped():
    monthly = pd.Series([1, 2, 6, 10], index=pd.date_range("2020-01-01", periods=4, freq="MS"))
    quarterly = monthly_to_quarterly(monthly)
    assert list(quarterly.index.astype(str)) == ["2020Q1"]
    assert quarterly.iloc[0] == 3


def test_year_over_year_survives_a_missing_quarter():
    quarters = pd.PeriodIndex(["2020Q1", "2020Q2", "2020Q4", "2021Q1", "2021Q3"], freq="Q")
    result = year_over_year(pd.Series([100, 200, 300, 110, 400], index=quarters))
    assert result["2021Q1"] == pytest.approx(10)
    assert pd.isna(result["2021Q3"])  # 2020Q3 is missing
    assert len(result) == 5


def test_panel_aligns_calendar_quarters():
    months = pd.date_range("2020-01-01", periods=16, freq="MS")
    quarters = pd.date_range("2020-01-01", periods=8, freq="QS")
    funds = pd.Series([float(i) for i in range(16)], index=months)
    prices = pd.Series([100.0] * 12 + [103.0] * 4, index=months)
    panel = build_panel(funds, prices, pd.Series(101.0, index=quarters), pd.Series(100.0, index=quarters))
    assert list(panel.index.astype(str)) == ["2021Q1"]  # 2021Q2 has only one month
    assert panel.iloc[0].tolist() == pytest.approx([13, 3, 1])
