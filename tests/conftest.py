"""Shared synthetic fixtures shaped like Project 1's real gold-layer schema.

Deliberately hand-crafted (not randomly generated) so tests can assert on
known relative orderings (e.g. "AAPL should out-rank NFLX on value") without
being fragile to floating point noise.
"""

from __future__ import annotations

import pandas as pd
import pytest

SECTORS = {
    "Technology": ["AAPL", "MSFT", "GOOG", "NFLX"],
    "Financials": ["JPM", "BAC", "WFC", "GS"],
    "Healthcare": ["JNJ", "PFE", "MRK", "UNH"],
}

# ticker -> (pe_ratio_ttm, price_to_book, return_on_equity), ordered best-to-worst per sector
VALUE_FACTORS = {
    "AAPL": (15.0, 3.0, 0.30),
    "MSFT": (25.0, 8.0, 0.20),
    "GOOG": (30.0, 6.0, 0.15),
    "NFLX": (40.0, 10.0, 0.10),
    "JPM": (9.0, 1.1, 0.15),
    "BAC": (10.0, 1.2, 0.14),
    "WFC": (12.0, 1.3, 0.12),
    "GS": (14.0, 1.4, 0.10),
    "JNJ": (18.0, 5.0, 0.25),
    "PFE": (20.0, 5.5, 0.20),
    "MRK": (22.0, 6.0, 0.18),
    "UNH": (25.0, 6.5, 0.15),
}

ALL_TICKERS = [t for tickers in SECTORS.values() for t in tickers]


@pytest.fixture
def dim_security() -> pd.DataFrame:
    rows = []
    for sector, tickers in SECTORS.items():
        for ticker in tickers:
            rows.append(
                {
                    "ticker": ticker,
                    "company_name": f"{ticker} Inc.",
                    "sector": sector,
                    "industry": f"{sector} Sub-industry",
                    "country": "United States",
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "market_index": "S&P 100",
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def security_snapshot() -> pd.DataFrame:
    rows = []
    for ticker, (pe, pb, roe) in VALUE_FACTORS.items():
        rows.append(
            {
                "ticker": ticker,
                "annualised_return": 0.08 + 0.01 * ALL_TICKERS.index(ticker),
                "annualised_volatility": 0.20,
                "sharpe_ratio": 0.4,
                "max_drawdown": -0.25,
                "market_cap": 5.0e10,
                "beta": 1.0,
                "pe_ratio_ttm": pe,
                "pe_ratio_forward": pe * 0.9,
                "price_to_book": pb,
                "dividend_yield": 0.015,
                "eps_ttm": -2.0
                if ticker == "NFLX"
                else 5.0,  # NFLX: unprofitable, for price-derivation tests
                "return_on_equity": roe,
                "debt_to_equity": 0.5,
                "ev_ebitda": 12.0,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def securities(dim_security, security_snapshot) -> pd.DataFrame:
    from portfolio_iq.gold import merge_security_snapshot

    return merge_security_snapshot(dim_security, security_snapshot)


@pytest.fixture
def annual_financials() -> pd.DataFrame:
    rows = []
    for ticker in ALL_TICKERS:
        for fiscal_year in (2023, 2024):
            rows.append(
                {
                    "ticker": ticker,
                    "fiscal_year": fiscal_year,
                    "period_end": f"{fiscal_year}-12-31",
                    "revenue": 1.0e10,
                    "gross_profit": 4.0e9,
                    "operating_income": 2.0e9,
                    "ebit": 2.0e9,
                    "ebitda": 2.5e9,
                    "net_income": 1.5e9,
                    "eps_basic": 5.0,
                    "eps_diluted": 4.9,
                    "total_assets": 5.0e10,
                    "book_equity": 2.0e10,
                    "total_debt": 1.0e10,
                    "cash": 5.0e9,
                    "current_assets": 1.5e10,
                    "current_liabilities": 8.0e9,
                    "operating_cash_flow": 2.2e9,
                    "capex": 5.0e8,
                    "free_cash_flow": 1.7e9,
                    "net_debt": 5.0e9,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def return_covariance() -> pd.DataFrame:
    """All unordered pairs (including the diagonal) among ALL_TICKERS.
    Within-sector pairs get high correlation, cross-sector pairs get low
    correlation, so diversification tests have a predictable community
    structure.
    """
    ticker_sector = {t: s for s, tickers in SECTORS.items() for t in tickers}
    rows = []
    for i, a in enumerate(ALL_TICKERS):
        for b in ALL_TICKERS[i:]:
            if a == b:
                correlation = 1.0
            elif ticker_sector[a] == ticker_sector[b]:
                correlation = 0.75
            else:
                correlation = 0.10
            rows.append(
                {
                    "ticker_a": a,
                    "ticker_b": b,
                    "correlation": correlation,
                    "covariance_daily": correlation * 0.0001,
                    "covariance_annual": correlation * 0.04,
                    "common_trading_days": 252,
                    "sector_a": ticker_sector[a],
                    "sector_b": ticker_sector[b],
                }
            )
    return pd.DataFrame(rows)
