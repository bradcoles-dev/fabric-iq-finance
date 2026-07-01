import pandas as pd
import pytest

from portfolio_iq.allocation import allocate_shares, filter_affordable_candidates


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


def test_weight_reflects_realized_allocation_not_target(weights, prices):
    allocation, leftover_cash = allocate_shares(weights, prices, budget=1000.0)
    total_value = allocation["dollar_amount"].sum() + leftover_cash

    expected_weight = allocation["dollar_amount"] / total_value
    pd.testing.assert_series_equal(allocation["weight"], expected_weight, check_names=False)
    # target_weight is preserved separately for comparison against the realized weight.
    assert (allocation["target_weight"] == allocation["ticker"].map(weights)).all()


def test_missing_price_raises(weights):
    incomplete_prices = pd.Series({"AAPL": 190.0, "JPM": 210.0})
    with pytest.raises(ValueError):
        allocate_shares(weights, incomplete_prices, budget=1000.0)


@pytest.fixture
def candidates() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "JPM", "NVDA"],
            "sector": ["Technology", "Financials", "Technology"],
        }
    )


def test_filter_affordable_candidates_drops_tickers_above_position_cap(candidates):
    # 10% of a $1,000 budget is a $100 cap. NVDA at $6,813/share can never
    # fit; AAPL and JPM are both comfortably under it.
    latest_prices = pd.Series({"AAPL": 19.0, "JPM": 21.0, "NVDA": 6813.0})

    affordable = filter_affordable_candidates(
        candidates, latest_prices, budget=1000.0, max_position_weight=0.10
    )

    assert set(affordable["ticker"]) == {"AAPL", "JPM"}


def test_filter_affordable_candidates_keeps_ticker_priced_exactly_at_cap(candidates):
    latest_prices = pd.Series({"AAPL": 100.0, "JPM": 21.0, "NVDA": 6813.0})

    affordable = filter_affordable_candidates(
        candidates, latest_prices, budget=1000.0, max_position_weight=0.10
    )

    assert "AAPL" in set(affordable["ticker"])
