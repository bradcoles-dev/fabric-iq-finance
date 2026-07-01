"""Typed readers and reshapers for Project 1's (dbt-fabric-finance) gold-layer tables.

These functions operate on pandas DataFrames already read out of Spark
(`spark.read.table("gold.dim_security").toPandas()`), not on Spark DataFrames
directly, so the rest of this package — and its tests — never need a Spark
session.
"""

from __future__ import annotations

import pandas as pd

DIM_SECURITY_KEY = "ticker"
SNAPSHOT_KEY = "ticker"
ANNUAL_FINANCIALS_KEY = ["ticker", "fiscal_year"]
COVARIANCE_KEY = ["ticker_a", "ticker_b"]

DIM_SECURITY_COLUMNS = [
    "ticker",
    "company_name",
    "sector",
    "industry",
    "country",
    "currency",
    "exchange",
    "market_index",
]

SNAPSHOT_COLUMNS = [
    "ticker",
    "annualised_return",
    "annualised_volatility",
    "sharpe_ratio",
    "max_drawdown",
    "market_cap",
    "beta",
    "pe_ratio_ttm",
    "pe_ratio_forward",
    "price_to_book",
    "dividend_yield",
    "eps_ttm",
    "return_on_equity",
    "debt_to_equity",
    "ev_ebitda",
]

COVARIANCE_COLUMNS = [
    "ticker_a",
    "ticker_b",
    "correlation",
    "covariance_daily",
    "covariance_annual",
    "common_trading_days",
    "sector_a",
    "sector_b",
]


class GoldSchemaError(ValueError):
    """Raised when a gold-layer DataFrame is missing required columns or keys."""


def _require_columns(df: pd.DataFrame, required: list[str], table_name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise GoldSchemaError(f"{table_name} is missing required columns: {missing}")


def validate_dim_security(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, DIM_SECURITY_COLUMNS, "dim_security")
    if df[DIM_SECURITY_KEY].duplicated().any():
        dupes = df.loc[df[DIM_SECURITY_KEY].duplicated(), DIM_SECURITY_KEY].tolist()
        raise GoldSchemaError(f"dim_security.ticker is not unique: {dupes}")
    return df


def validate_security_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, SNAPSHOT_COLUMNS, "fact_security_snapshot")
    if df[SNAPSHOT_KEY].duplicated().any():
        dupes = df.loc[df[SNAPSHOT_KEY].duplicated(), SNAPSHOT_KEY].tolist()
        raise GoldSchemaError(f"fact_security_snapshot.ticker is not unique: {dupes}")
    return df


def validate_return_covariance(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, COVARIANCE_COLUMNS, "fact_return_covariance")
    return df


def merge_security_snapshot(dim_security: pd.DataFrame, snapshot: pd.DataFrame) -> pd.DataFrame:
    """Join dim_security and fact_security_snapshot into one row-per-ticker frame."""
    validate_dim_security(dim_security)
    validate_security_snapshot(snapshot)
    merged = dim_security.merge(snapshot, on=DIM_SECURITY_KEY, how="inner", validate="one_to_one")
    if merged.empty:
        raise GoldSchemaError("dim_security and fact_security_snapshot share no tickers")
    return merged


def pivot_covariance(
    covariance: pd.DataFrame,
    tickers: list[str] | None = None,
    value_column: str = "covariance_annual",
) -> pd.DataFrame:
    """Reshape the long ticker_a/ticker_b covariance table into a square matrix.

    fact_return_covariance stores one row per unordered pair (including the
    diagonal), so the pivot is mirrored across ticker_a/ticker_b to guarantee
    a symmetric matrix even if the source only has one direction per pair.
    """
    validate_return_covariance(covariance)
    df = covariance
    if tickers is not None:
        wanted = set(tickers)
        df = df[df["ticker_a"].isin(wanted) & df["ticker_b"].isin(wanted)]

    mirrored = pd.concat(
        [
            df[["ticker_a", "ticker_b", value_column]],
            df.rename(columns={"ticker_a": "ticker_b", "ticker_b": "ticker_a"})[
                ["ticker_a", "ticker_b", value_column]
            ],
        ],
        ignore_index=True,
    ).drop_duplicates(subset=["ticker_a", "ticker_b"])

    matrix = mirrored.pivot(index="ticker_a", columns="ticker_b", values=value_column)
    matrix = matrix.sort_index().sort_index(axis=1)
    if tickers is not None:
        matrix = matrix.reindex(index=tickers, columns=tickers)
    return matrix


def derive_latest_price(securities: pd.DataFrame) -> pd.Series:
    """fact_security_snapshot has no direct last-price column, so price is
    recovered from the P/E identity (price = pe_ratio_ttm * eps_ttm) that
    Project 1 used to compute pe_ratio_ttm in the first place. Undefined for
    unprofitable companies (eps_ttm <= 0), where P/E-implied price has no
    meaning — those tickers get NaN rather than a negative price.
    """
    _require_columns(securities, ["ticker", "pe_ratio_ttm", "eps_ttm"], "securities")
    price = securities["pe_ratio_ttm"] * securities["eps_ttm"]
    price = price.where(securities["eps_ttm"] > 0)
    return pd.Series(price.values, index=securities["ticker"], name="latest_price")
