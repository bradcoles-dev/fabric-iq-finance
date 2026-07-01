"""Sector-relative value screening.

A stock is "cheap" only relative to its peers — a low P/E in a structurally
low-P/E sector (e.g. utilities) isn't a value signal, and a mid-range P/E in
a structurally high-P/E sector (e.g. tech) might be. So every factor is
percentile-ranked within dim_security.sector before being combined, rather
than compared across the whole universe.
"""

from __future__ import annotations

import pandas as pd

VALUE_FACTORS = {
    "pe_ratio_ttm": False,  # lower is more attractive
    "price_to_book": False,  # lower is more attractive
    "return_on_equity": True,  # higher is more attractive
}


def compute_value_scores(securities: pd.DataFrame, min_peers: int = 3) -> pd.DataFrame:
    """Compute a 0-1 sector-relative value_score per ticker.

    `securities` must be the merge_security_snapshot() output (one row per
    ticker with `sector` plus the VALUE_FACTORS columns). Sectors with fewer
    than `min_peers` members get a null value_score — there aren't enough
    peers to rank against.
    """
    df = securities.copy()
    sector_sizes = df.groupby("sector")["ticker"].transform("size")
    eligible = sector_sizes >= min_peers

    rank_columns = []
    for factor, higher_is_better in VALUE_FACTORS.items():
        rank_col = f"_{factor}_rank"
        ranked = df.groupby("sector")[factor].rank(pct=True, na_option="keep")
        df[rank_col] = ranked if higher_is_better else 1.0 - ranked
        rank_columns.append(rank_col)

    df["value_score"] = df[rank_columns].mean(axis=1, skipna=True)
    df.loc[~eligible, "value_score"] = pd.NA
    df.loc[df[rank_columns].isna().all(axis=1), "value_score"] = pd.NA

    return df.drop(columns=rank_columns).sort_values("value_score", ascending=False)


def select_candidates(
    scored: pd.DataFrame, top_n: int = 40, min_score: float = 0.5
) -> pd.DataFrame:
    """Shortlist the top-scoring, sufficiently-attractive tickers for the optimizer."""
    eligible = scored.dropna(subset=["value_score"])
    eligible = eligible[eligible["value_score"] >= min_score]
    return eligible.nlargest(top_n, "value_score").reset_index(drop=True)
