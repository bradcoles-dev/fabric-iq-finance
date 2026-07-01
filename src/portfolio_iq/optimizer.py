"""Mean-variance (Modern Portfolio Theory) optimization over the value-screened
candidate set, using Project 1's precomputed 252-day covariance matrix rather
than recomputing it — this project never touches raw price history.
"""

from __future__ import annotations

import pandas as pd
from pypfopt import EfficientFrontier


class OptimizationError(ValueError):
    """Raised when the candidate set can't support a constrained optimization."""


def optimize_portfolio(
    candidates: pd.DataFrame,
    cov_matrix: pd.DataFrame,
    max_position_weight: float = 0.10,
    max_sector_weight: float = 0.25,
    risk_free_rate: float = 0.02,
) -> pd.Series:
    """Return max-Sharpe weights for `candidates` (columns: ticker, sector,
    annualised_return) subject to per-position and per-sector caps.

    `cov_matrix` must be a square, ticker-indexed/columned frame covering at
    least every ticker in `candidates` (see gold.pivot_covariance).
    """
    tickers = candidates["ticker"].tolist()
    if len(tickers) < 2:
        raise OptimizationError("Need at least 2 candidates to optimize a portfolio")

    missing_cov = [t for t in tickers if t not in cov_matrix.index or t not in cov_matrix.columns]
    if missing_cov:
        raise OptimizationError(f"cov_matrix is missing candidates: {missing_cov}")

    mu = candidates.set_index("ticker")["annualised_return"].reindex(tickers)
    sigma = cov_matrix.loc[tickers, tickers]

    ef = EfficientFrontier(mu, sigma, weight_bounds=(0, max_position_weight))

    sector_mapper = candidates.set_index("ticker")["sector"].to_dict()
    sectors = set(sector_mapper.values())
    ef.add_sector_constraints(
        sector_mapper,
        dict.fromkeys(sectors, 0.0),
        dict.fromkeys(sectors, max_sector_weight),
    )

    ef.max_sharpe(risk_free_rate=risk_free_rate)
    weights = ef.clean_weights()

    return pd.Series(weights, name="weight").loc[lambda s: s > 0].sort_values(ascending=False)
