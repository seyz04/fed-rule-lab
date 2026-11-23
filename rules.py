"""Rule math and quarterly alignment. All rates, inflation and gaps are in percent."""
import pandas as pd

R_STAR = 2.0   # neutral real rate in Taylor (1993)
PI_STAR = 2.0  # inflation target


def policy_rule(inflation, gap, gap_weight, r_star=R_STAR, pi_star=PI_STAR):
    """Taylor (1993) uses gap_weight 0.5; the balanced approach uses 1.0."""
    return r_star + inflation + 0.5 * (inflation - pi_star) + gap_weight * gap


def output_gap(real_gdp, potential_gdp):
    return 100 * (real_gdp / potential_gdp - 1)


def monthly_to_quarterly(monthly):
    """Average the three months, dropping any quarter with a month missing."""
    groups = monthly.dropna().groupby(monthly.dropna().index.to_period("Q"))
    return groups.mean()[groups.count() == 3]


def year_over_year(quarterly_index):
    """Percent change from the same quarter a year earlier."""
    # Compare by date, not by row position, so a missing quarter cannot shift the base.
    base = quarterly_index.copy()
    base.index = base.index + 4
    return (100 * (quarterly_index / base - 1)).reindex(quarterly_index.index)


def build_panel(fed_funds, core_pce, real_gdp, potential_gdp):
    """Put all four series on one quarterly index and keep only complete quarters."""
    gdp = real_gdp.copy()
    gdp.index = gdp.index.to_period("Q")
    potential = potential_gdp.copy()
    potential.index = potential.index.to_period("Q")
    panel = pd.DataFrame({
        "fed_funds": monthly_to_quarterly(fed_funds),
        "inflation": year_over_year(monthly_to_quarterly(core_pce)),
        "gap": output_gap(gdp, potential),
    })
    return panel.dropna()
