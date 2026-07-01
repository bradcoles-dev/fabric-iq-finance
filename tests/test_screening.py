import pandas as pd

from portfolio_iq.screening import compute_value_scores, select_candidates


def test_value_score_ranks_within_sector_by_construction(securities):
    scored = compute_value_scores(securities)

    def score(ticker: str) -> float:
        return scored.loc[scored["ticker"] == ticker, "value_score"].iloc[0]

    # AAPL/JPM/JNJ were built as the best value name in their sector,
    # NFLX/GS/UNH the worst.
    assert score("AAPL") > score("MSFT") > score("GOOG") > score("NFLX")
    assert score("JPM") > score("BAC") > score("WFC") > score("GS")
    assert score("JNJ") > score("PFE") > score("MRK") > score("UNH")


def test_value_score_is_sector_relative_not_universe_wide(securities):
    scored = compute_value_scores(securities)
    # Financials sector has structurally low P/E; a Financials name shouldn't
    # automatically outrank a Tech name just because its raw P/E is lower.
    aapl = scored.loc[scored["ticker"] == "AAPL", "value_score"].iloc[0]
    gs = scored.loc[scored["ticker"] == "GS", "value_score"].iloc[0]
    assert aapl > gs  # AAPL is best-in-sector, GS is worst-in-sector

    financials_max = scored.loc[scored["sector"] == "Financials", "value_score"].max()
    assert 0.0 <= financials_max <= 1.0
    assert 0.0 <= aapl <= 1.0


def test_sectors_below_min_peers_get_null_score(dim_security, security_snapshot):
    # Drop three Technology tickers so it only has one member.
    thin_dim = dim_security[~dim_security["ticker"].isin(["MSFT", "GOOG", "NFLX"])]
    thin_snapshot = security_snapshot[~security_snapshot["ticker"].isin(["MSFT", "GOOG", "NFLX"])]

    from portfolio_iq.gold import merge_security_snapshot

    merged = merge_security_snapshot(thin_dim, thin_snapshot)
    scored = compute_value_scores(merged, min_peers=3)

    assert pd.isna(scored.loc[scored["ticker"] == "AAPL", "value_score"].iloc[0])
    assert not pd.isna(scored.loc[scored["ticker"] == "JPM", "value_score"].iloc[0])


def test_select_candidates_filters_and_ranks(securities):
    scored = compute_value_scores(securities)
    candidates = select_candidates(scored, top_n=3, min_score=0.0)

    assert len(candidates) == 3
    assert candidates["value_score"].is_monotonic_decreasing
    assert candidates.iloc[0]["ticker"] in {"AAPL", "JPM", "JNJ"}
