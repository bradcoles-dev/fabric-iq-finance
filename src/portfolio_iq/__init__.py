"""Quant intelligence layer for fabric-iq-finance.

Plain, Spark-free Python so it's unit-testable without a live Fabric session.
Fabric notebooks import this package for the actual computation and only
handle I/O (reading gold tables, writing iq_* output tables) themselves.
"""

__version__ = "0.1.0"
