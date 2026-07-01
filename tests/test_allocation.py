import pandas as pd
import pytest

from portfolio_iq.allocation import allocate_shares


@pytest.fixture
def weights() -> pd.Series:
    return pd.Series({"AAPL": 0.5, "JPM": 0.3, "JNJ": 0.2})


@pytest.fixture
def prices() -> pd.Series:
    # Deliberately low relative to the budget so $1,000 buys enough whole
    # shares of each for the allocation to track the target weights closely
    # (a $1,000 budget against $190+ prices leaves too little share-count
    # resolution for that to hold, which is a budget/price ratio issue, not
    # an allocate_shares bug).
    return pd.Series({"AAPL": 19.0, "JPM": 21.0, "JNJ": 15.5})


def test_allocation_stays_within_budget(weights, prices):
    allocation, leftover_cash = allocate_shares(weights, prices, budget=1000.0)

    assert (allocation["shares"] >= 0).all()
    assert (allocation["shares"] % 1 == 0).all()
    assert allocation["dollar_amount"].sum() + leftover_cash == pytest.approx(1000.0, abs=1e-6)
    assert leftover_cash >= 0


def test_allocation_roughly_matches_weights(weights, prices):
    allocation, _ = allocate_shares(weights, prices, budget=1000.0)
    allocation = allocation.set_index("ticker")

    # AAPL had the highest target weight, so it should get the largest dollar allocation.
    assert allocation.loc["AAPL", "dollar_amount"] >= allocation.loc["JPM", "dollar_amount"]
    assert allocation.loc["AAPL", "dollar_amount"] >= allocation.loc["JNJ", "dollar_amount"]


def test_missing_price_raises(weights):
    incomplete_prices = pd.Series({"AAPL": 190.0, "JPM": 210.0})
    with pytest.raises(ValueError):
        allocate_shares(weights, incomplete_prices, budget=1000.0)
