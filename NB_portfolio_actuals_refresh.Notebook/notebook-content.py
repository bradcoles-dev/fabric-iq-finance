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
RECOMMENDATION_TABLE = "iq_portfolio_recommendation"
ACTUALS_TABLE = "iq_portfolio_actuals"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from datetime import datetime, timezone

from portfolio_iq.gold import derive_latest_price

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

recommendation_path = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{DBO_SCHEMA}/{RECOMMENDATION_TABLE}"
gold_base = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{GOLD_SCHEMA}"

# Shares held and leftover cash are fixed at purchase time — this notebook
# only re-prices the position, it never re-runs the optimizer.
positions = spark.read.format("delta").load(recommendation_path).toPandas()
positions = positions[positions["source"] == "recommendation"]

current_snapshot = spark.read.format("delta").load(f"{gold_base}/fact_security_snapshot").toPandas()
current_snapshot = current_snapshot[current_snapshot["ticker"].isin(positions["ticker"])]

print(f"Re-pricing {len(positions)} held positions as of today.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

current_price = derive_latest_price(current_snapshot)

actuals = positions[["ticker", "shares", "price", "leftover_cash"]].rename(columns={"price": "purchase_price"})
actuals["latest_price"] = actuals["ticker"].map(current_price)
actuals["dollar_amount"] = actuals["shares"] * actuals["latest_price"]
actuals["unrealized_return"] = actuals["latest_price"] / actuals["purchase_price"] - 1

total_value = actuals["dollar_amount"].sum() + actuals["leftover_cash"].iloc[0]
actuals["weight"] = actuals["dollar_amount"] / total_value
actuals["source"] = "actual"
actuals["as_of_date"] = datetime.now(timezone.utc)

print(f"Total portfolio value: ${total_value:,.2f}")
actuals[["ticker", "shares", "latest_price", "dollar_amount", "unrealized_return", "weight"]]

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

output_path = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{DBO_SCHEMA}/{ACTUALS_TABLE}"

spark.createDataFrame(actuals).write.format("delta").mode("append").option("mergeSchema", "true").save(
    output_path
)

print(f"Appended {len(actuals):,} rows to {output_path}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
