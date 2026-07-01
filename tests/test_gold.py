import pandas as pd
import pytest

from conftest import ALL_TICKERS
from portfolio_iq.gold import (
    GoldSchemaError,
    derive_latest_price,
    merge_security_snapshot,
    pivot_covariance,
    validate_dim_security,
)


def test_validate_dim_security_rejects_missing_columns(dim_security):
    with pytest.raises(GoldSchemaError):
        validate_dim_security(dim_security.drop(columns=["sector"]))


def test_validate_dim_security_rejects_duplicate_tickers(dim_security):
    dupe = pd.concat([dim_security, dim_security.iloc[[0]]], ignore_index=True)
    with pytest.raises(GoldSchemaError):
        validate_dim_security(dupe)


def test_merge_security_snapshot_joins_on_ticker(dim_security, security_snapshot):
    merged = merge_security_snapshot(dim_security, security_snapshot)
    assert len(merged) == len(dim_security)
    assert {"sector", "pe_ratio_ttm", "return_on_equity"}.issubset(merged.columns)


def test_merge_security_snapshot_raises_on_no_overlap(dim_security, security_snapshot):
    disjoint = security_snapshot.copy()
    disjoint["ticker"] = disjoint["ticker"] + "_X"
    with pytest.raises(GoldSchemaError):
        merge_security_snapshot(dim_security, disjoint)


def test_pivot_covariance_is_symmetric(return_covariance):
    matrix = pivot_covariance(return_covariance, tickers=ALL_TICKERS, value_column="correlation")
    assert matrix.shape == (len(ALL_TICKERS), len(ALL_TICKERS))
    pd.testing.assert_frame_equal(matrix, matrix.T, check_exact=False, check_names=False)
    assert (pd.Series(matrix.values.diagonal(), index=matrix.index) == 1.0).all()


def test_derive_latest_price_uses_pe_times_eps(securities):
    prices = derive_latest_price(securities)
    aapl_pe = securities.loc[securities["ticker"] == "AAPL", "pe_ratio_ttm"].iloc[0]
    aapl_eps = securities.loc[securities["ticker"] == "AAPL", "eps_ttm"].iloc[0]
    assert prices["AAPL"] == pytest.approx(aapl_pe * aapl_eps)


def test_derive_latest_price_is_nan_for_unprofitable_tickers(securities):
    prices = derive_latest_price(securities)
    assert pd.isna(prices["NFLX"])  # eps_ttm <= 0 in the fixture
