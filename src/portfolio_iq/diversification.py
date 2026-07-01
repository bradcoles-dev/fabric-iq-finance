"""Correlation-graph diversification analytics over fact_return_covariance.

This doesn't feed the optimizer directly — the optimizer already penalizes
correlation implicitly through the covariance matrix. It exists to explain
*why* the optimizer avoided or grouped certain names, for the ontology graph
and the data agent's narrative answers.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd


def build_correlation_graph(
    covariance: pd.DataFrame,
    tickers: list[str] | None = None,
    correlation_threshold: float = 0.5,
) -> nx.Graph:
    """Build an undirected graph with an edge between tickers whose |correlation|
    exceeds `correlation_threshold`. Tickers with no such edge are still added
    as isolated nodes so every candidate appears in the diversification output.
    """
    df = covariance[covariance["ticker_a"] != covariance["ticker_b"]]
    if tickers is not None:
        wanted = set(tickers)
        df = df[df["ticker_a"].isin(wanted) & df["ticker_b"].isin(wanted)]

    graph = nx.Graph()
    graph.add_nodes_from(
        tickers if tickers is not None else set(df["ticker_a"]) | set(df["ticker_b"])
    )

    strong = df[df["correlation"].abs() > correlation_threshold]
    for row in strong.itertuples(index=False):
        graph.add_edge(
            row.ticker_a, row.ticker_b, weight=abs(row.correlation), correlation=row.correlation
        )

    return graph


def compute_diversification_metrics(graph: nx.Graph) -> pd.DataFrame:
    """Per-ticker community membership and centrality, for flagging redundant
    or concentrated names in a candidate set.
    """
    communities = nx.community.greedy_modularity_communities(graph, weight="weight")
    community_id = {ticker: i for i, group in enumerate(communities) for ticker in group}

    degree_centrality = nx.degree_centrality(graph)
    try:
        eigen_centrality = nx.eigenvector_centrality(graph, weight="weight", max_iter=1000)
    except (nx.PowerIterationFailedConvergence, nx.NetworkXError):
        eigen_centrality = dict.fromkeys(graph.nodes, 0.0)

    return (
        pd.DataFrame(
            {
                "ticker": list(graph.nodes),
                "community_id": [community_id[t] for t in graph.nodes],
                "degree_centrality": [degree_centrality[t] for t in graph.nodes],
                "eigenvector_centrality": [eigen_centrality[t] for t in graph.nodes],
            }
        )
        .sort_values(["community_id", "eigenvector_centrality"], ascending=[True, False])
        .reset_index(drop=True)
    )
