from conftest import ALL_TICKERS, SECTORS
from portfolio_iq.diversification import build_correlation_graph, compute_diversification_metrics


def test_build_correlation_graph_connects_within_sector_only(return_covariance):
    graph = build_correlation_graph(
        return_covariance, tickers=ALL_TICKERS, correlation_threshold=0.5
    )

    assert set(graph.nodes) == set(ALL_TICKERS)
    # Within-sector correlation was set to 0.75 (above threshold), cross-sector to 0.10 (below).
    assert graph.has_edge("AAPL", "MSFT")
    assert not graph.has_edge("AAPL", "JPM")


def test_isolated_ticker_still_appears_as_a_node(return_covariance):
    graph = build_correlation_graph(
        return_covariance, tickers=ALL_TICKERS, correlation_threshold=0.99
    )
    assert "AAPL" in graph.nodes
    assert graph.degree["AAPL"] == 0


def test_communities_align_with_sectors(return_covariance):
    graph = build_correlation_graph(
        return_covariance, tickers=ALL_TICKERS, correlation_threshold=0.5
    )
    metrics = compute_diversification_metrics(graph)

    assert set(metrics["ticker"]) == set(ALL_TICKERS)
    for tickers in SECTORS.values():
        community_ids = metrics.loc[metrics["ticker"].isin(tickers), "community_id"]
        assert community_ids.nunique() == 1  # every sector forms its own tight community

    tech_community = metrics.loc[metrics["ticker"] == "AAPL", "community_id"].iloc[0]
    financials_community = metrics.loc[metrics["ticker"] == "JPM", "community_id"].iloc[0]
    assert tech_community != financials_community

    assert (metrics["degree_centrality"] >= 0).all()
    assert (metrics["eigenvector_centrality"] >= 0).all()
