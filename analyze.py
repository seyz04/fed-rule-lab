"""Run `python analyze.py` (add --refresh to download new data from FRED)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from rules import build_panel, policy_rule

ROOT = Path(__file__).parent
DATA, OUT = ROOT / "data", ROOT / "output"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
START = "1987Q3"  # Greenspan became chair in August 1987
WEIGHTS = {"taylor_1993": 0.5, "balanced": 1.0}
ERAS = [("1987Q3", "1999Q4"), ("2000Q1", "2007Q4"), ("2008Q1", "2015Q4"),
        ("2016Q1", "2019Q4"), ("2020Q1", "2021Q4"), ("2022Q1", None), (START, None)]
R_STARS, PI_STARS = [0.5, 1.0, 2.0], [2.0, 2.5, 3.0]
COLORS = {"fed_funds": "#0b0b0b", "taylor_1993": "#2a78d6", "balanced": "#eb6834"}


def load(series_id):
    path = DATA / f"{series_id}.csv"
    if "--refresh" in sys.argv or not path.exists():
        # Parse first, so a failed download never overwrites the good cache.
        fresh = pd.read_csv(URL + series_id)
        fresh[["observation_date", series_id]].to_csv(path, index=False)
    return pd.read_csv(path, index_col="observation_date", parse_dates=True,
                       na_values=".")[series_id]


def summarize(panel, rule, r_star, pi_star):
    rate = policy_rule(panel.inflation, panel.gap, WEIGHTS[rule], r_star, pi_star)
    deviation = panel.fed_funds - rate
    return {"rule": rule, "r_star": r_star, "pi_star": pi_star,
            "start": str(panel.index[0]), "end": str(panel.index[-1]),
            "quarters": len(panel), "mean_deviation": deviation.mean(),
            "mean_abs_deviation": deviation.abs().mean(),
            "lowest": deviation.min(), "lowest_quarter": str(deviation.idxmin()),
            "highest": deviation.max(), "highest_quarter": str(deviation.idxmax()),
            "latest_deviation": deviation.iloc[-1],
            "quarters_rule_below_zero": (rate < 0).sum()}


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e5e3", linewidth=0.7)
    ax.axhline(0, color="#77776f", linewidth=0.8)
    ax.set_axisbelow(True)


def chart_rates(panel):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    labels = {"fed_funds": "Actual fed funds", "taylor_1993": "Taylor 1993", "balanced": "Balanced approach"}
    for column, label in labels.items():
        ax.plot(panel.index.to_timestamp(), panel[column], color=COLORS[column], linewidth=2, label=label)
    style(ax)
    ax.set_ylabel("Percent")
    ax.set_title("Actual fed funds rate and two policy rules", loc="left", weight="bold")
    ax.legend(frameon=False, loc="lower left")
    fig.text(0.01, 0.01, "Rules use r* = 2, inflation target = 2, year-over-year core PCE. Current-vintage FRED data, quarterly.", fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "rates_vs_rules.png", dpi=150)


def chart_sensitivity(panel):
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True, sharey=True)
    cases = [("r*", R_STARS, "r_star", "Changing r* (inflation target = 2)"),
             ("target", PI_STARS, "pi_star", "Changing the inflation target (r* = 2)")]
    for ax, (label, values, argument, title) in zip(axes, cases):
        for value, color in zip(values, ["#86b6ef", "#2a78d6", "#104281"]):
            rate = policy_rule(panel.inflation, panel.gap, 0.5, **{argument: value})
            ax.plot(panel.index.to_timestamp(), panel.fed_funds - rate, color=color, linewidth=2, label=f"{label} = {value}")
        style(ax)
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_ylabel("Percentage points")
        ax.legend(frameon=False, ncol=3, loc="lower left")
    fig.suptitle("Actual rate minus Taylor 1993 (below zero = easier than the rule)", x=0.01, ha="left", weight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "sensitivity.png", dpi=150)


def main():
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    panel = build_panel(*[load(s) for s in ["FEDFUNDS", "PCEPILFE", "GDPC1", "GDPPOT"]]).loc[START:]
    for rule, weight in WEIGHTS.items():
        panel[rule] = policy_rule(panel.inflation, panel.gap, weight)
    panel.round(3).to_csv(OUT / "quarterly_panel.csv", index_label="quarter")

    summary = pd.DataFrame([summarize(panel.loc[a:b], rule, 2.0, 2.0) for a, b in ERAS for rule in WEIGHTS])
    sensitivity = pd.DataFrame([summarize(panel, rule, r, p) for rule in WEIGHTS for r in R_STARS for p in PI_STARS])
    summary.round(2).to_csv(OUT / "summary.csv", index=False)
    sensitivity.round(2).to_csv(OUT / "sensitivity.csv", index=False)
    chart_rates(panel)
    chart_sensitivity(panel)
    print(summary.round(2).to_string(index=False))
    print(panel.tail(1).round(2).to_string())


if __name__ == "__main__":
    main()
