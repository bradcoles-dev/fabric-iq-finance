"""Convert continuous optimizer weights into whole-share quantities for a
fixed real-money budget — the exact problem of turning a recommendation into
an actual brokerage order.
"""

from __future__ import annotations

import pandas as pd
from pypfopt.discrete_allocation import DiscreteAllocation


def filter_affordable_candidates(
    candidates: pd.DataFrame, latest_prices: pd.Series, budget: float, max_position_weight: float
) -> pd.DataFrame:
    """Drop candidates priced above max_position_weight * budget.

    A single share of these can never be sized accurately: it either has to
    be skipped (0%) or bought anyway and blow past its own position cap, so
    they're excluded from the optimizer's universe up front rather than
    discovered as a rounding problem after the fact. Most brokers don't
    support fractional shares, so this is the only way to guarantee the cap
    actually holds for a fixed-dollar budget.
    """
    position_cap = max_position_weight * budget
    price_by_ticker = candidates["ticker"].map(latest_prices)
    return candidates[price_by_ticker <= position_cap].reset_index(drop=True)


def allocate_shares(
    weights: pd.Series, latest_prices: pd.Series, budget: float = 1000.0
) -> tuple[pd.DataFrame, float]:
    """Greedy discrete allocation (no external LP solver required) of `budget`
    across `weights`, priced at `latest_prices`.

    Returns (allocation_df, leftover_cash). allocation_df columns: ticker,
    target_weight, weight, shares, price, dollar_amount. `target_weight` is
    the optimizer's pre-rounding weight; `weight` is what was actually
    achieved after rounding to whole shares. These can diverge significantly
    for tickers whose share price is large relative to the position's dollar
    cap (target_weight * budget) — e.g. a $373 share against a $100 cap can
    only round to 0% or 37%, never the intended 10%.
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
    allocation["target_weight"] = allocation["ticker"].map(weights)
    allocation["price"] = allocation["ticker"].map(prices)
    allocation["dollar_amount"] = allocation["shares"] * allocation["price"]

    total_portfolio_value = allocation["dollar_amount"].sum() + leftover_cash
    allocation["weight"] = allocation["dollar_amount"] / total_portfolio_value

    allocation = allocation.sort_values("dollar_amount", ascending=False).reset_index(drop=True)

    return allocation, leftover_cash
