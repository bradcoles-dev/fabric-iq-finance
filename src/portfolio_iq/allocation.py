"""Convert continuous optimizer weights into whole-share quantities for a
fixed real-money budget — the exact problem of turning a recommendation into
an actual brokerage order.
"""

from __future__ import annotations

import pandas as pd
from pypfopt.discrete_allocation import DiscreteAllocation


def allocate_shares(
    weights: pd.Series, latest_prices: pd.Series, budget: float = 1000.0
) -> tuple[pd.DataFrame, float]:
    """Greedy discrete allocation (no external LP solver required) of `budget`
    across `weights`, priced at `latest_prices`.

    Returns (allocation_df, leftover_cash). allocation_df columns:
    ticker, weight, shares, price, dollar_amount.
    """
    tickers = weights.index.tolist()
    prices = latest_prices.reindex(tickers)
    if prices.isna().any():
        missing = prices[prices.isna()].index.tolist()
        raise ValueError(f"latest_prices is missing candidates: {missing}")

    da = DiscreteAllocation(weights.to_dict(), prices, total_portfolio_value=budget)
    shares, leftover_cash = da.greedy_portfolio()

    allocation = pd.DataFrame(
        {
            "ticker": list(shares.keys()),
            "shares": list(shares.values()),
        }
    )
    allocation["weight"] = allocation["ticker"].map(weights)
    allocation["price"] = allocation["ticker"].map(prices)
    allocation["dollar_amount"] = allocation["shares"] * allocation["price"]
    allocation = allocation.sort_values("dollar_amount", ascending=False).reset_index(drop=True)

    return allocation, leftover_cash
