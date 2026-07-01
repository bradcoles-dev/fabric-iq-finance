# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# PARAMETERS CELL ********************

vl = notebookutils.variableLibrary.getLibrary("Variables")
WORKSPACE_ID = vl.WORKSPACE_ID
LAKEHOUSE_ID = vl.LAKEHOUSE_ID

GOLD_SCHEMA = "gold"
DBO_SCHEMA = "dbo"
CANDIDATES_TABLE = "iq_value_screen"
OUTPUT_TABLE = "iq_portfolio_recommendation"

BUDGET = 1000.0
MAX_POSITION_WEIGHT = 0.10
MAX_SECTOR_WEIGHT = 0.25
RISK_FREE_RATE = 0.02

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from datetime import datetime, timezone

from portfolio_iq.allocation import allocate_shares
from portfolio_iq.gold import derive_latest_price, pivot_covariance
from portfolio_iq.optimizer import optimize_portfolio

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

candidates_path = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{DBO_SCHEMA}/{CANDIDATES_TABLE}"
gold_base = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{GOLD_SCHEMA}"

candidates = spark.read.format("delta").load(candidates_path).toPandas()
return_covariance = spark.read.format("delta").load(f"{gold_base}/fact_return_covariance").toPandas()

# Unprofitable candidates (eps_ttm <= 0) have no P/E-implied price, so they
# can't be discretely allocated a share count — drop before optimizing
# rather than after, so the optimizer never recommends an unsizeable name.
candidates["latest_price"] = derive_latest_price(candidates).values
candidates = candidates.dropna(subset=["latest_price"]).reset_index(drop=True)

print(f"{len(candidates)} candidates have a derivable price and proceed to optimization.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

cov_matrix = pivot_covariance(
    return_covariance, tickers=candidates["ticker"].tolist(), value_column="covariance_annual"
)

weights = optimize_portfolio(
    candidates[["ticker", "sector", "annualised_return"]],
    cov_matrix,
    max_position_weight=MAX_POSITION_WEIGHT,
    max_sector_weight=MAX_SECTOR_WEIGHT,
    risk_free_rate=RISK_FREE_RATE,
)

print(f"Optimizer selected {len(weights)} positions out of {len(candidates)} candidates.")
weights.head(10)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

latest_prices = candidates.set_index("ticker")["latest_price"]
allocation, leftover_cash = allocate_shares(weights, latest_prices, budget=BUDGET)

allocation["source"] = "recommendation"
allocation["as_of_date"] = datetime.now(timezone.utc)
# Carried on every row (rather than a separate table) so
# NB_portfolio_actuals_refresh can reconstruct total portfolio value —
# shares/prices move, but the uninvested cash from the original $1,000 doesn't.
allocation["leftover_cash"] = leftover_cash

print(f"Allocated ${allocation['dollar_amount'].sum():,.2f} of ${BUDGET:,.2f}, ${leftover_cash:,.2f} left as cash.")
allocation

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

output_path = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{DBO_SCHEMA}/{OUTPUT_TABLE}"

spark.createDataFrame(allocation).write.format("delta").mode("overwrite").option(
    "mergeSchema", "true"
).save(output_path)

print(f"Written {len(allocation):,} rows to {output_path}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
