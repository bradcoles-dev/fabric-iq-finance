import pandas as pd
import pytest

from conftest import ALL_TICKERS
from portfolio_iq.gold import pivot_covariance
from portfolio_iq.optimizer import OptimizationError, optimize_portfolio


@pytest.fixture
def candidates(securities) -> pd.DataFrame:
    return securities[["ticker", "sector", "annualised_return"]].copy()


@pytest.fixture
def cov_matrix(return_covariance) -> pd.DataFrame:
    return pivot_covariance(
        return_covariance, tickers=ALL_TICKERS, value_column="covariance_annual"
    )


def test_weights_sum_to_one_and_respect_position_cap(candidates, cov_matrix):
    weights = optimize_portfolio(
        candidates, cov_matrix, max_position_weight=0.10, max_sector_weight=0.40
    )

    assert weights.sum() == pytest.approx(1.0, abs=1e-4)
    assert (weights <= 0.10 + 1e-6).all()
    assert (weights > 0).all()


def test_weights_respect_sector_cap(candidates, cov_matrix):
    # 3 sectors, so the cap must allow at least 1/3 combined or "fully invested" is infeasible.
    weights = optimize_portfolio(
        candidates, cov_matrix, max_position_weight=0.20, max_sector_weight=0.40
    )

    ticker_sector = candidates.set_index("ticker")["sector"]
    sector_totals = weights.groupby(ticker_sector.reindex(weights.index)).sum()
    assert (sector_totals <= 0.40 + 1e-6).all()


def test_raises_on_too_few_candidates(cov_matrix):
    one_candidate = pd.DataFrame(
        {"ticker": ["AAPL"], "sector": ["Technology"], "annualised_return": [0.1]}
    )
    with pytest.raises(OptimizationError):
        optimize_portfolio(one_candidate, cov_matrix)


def test_raises_when_covariance_missing_a_candidate(candidates, cov_matrix):
    incomplete_cov = cov_matrix.drop(index="AAPL", columns="AAPL")
    with pytest.raises(OptimizationError):
        optimize_portfolio(candidates, incomplete_cov)
