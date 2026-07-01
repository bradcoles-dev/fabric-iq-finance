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
OUTPUT_SCHEMA = "dbo"
OUTPUT_TABLE = "iq_value_screen"
MIN_PEERS = 3
TOP_N = 40
MIN_SCORE = 0.5

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# portfolio_iq comes from an attached custom Environment (build a wheel from
# this package and attach it to the workspace), not from %pip install here.
from datetime import datetime, timezone

from portfolio_iq.gold import merge_security_snapshot
from portfolio_iq.screening import compute_value_scores, select_candidates

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

gold_base = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{GOLD_SCHEMA}"

dim_security = spark.read.format("delta").load(f"{gold_base}/dim_security").toPandas()
security_snapshot = spark.read.format("delta").load(f"{gold_base}/fact_security_snapshot").toPandas()

print(f"dim_security: {len(dim_security):,} rows, fact_security_snapshot: {len(security_snapshot):,} rows")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

securities = merge_security_snapshot(dim_security, security_snapshot)
scored = compute_value_scores(securities, min_peers=MIN_PEERS)
candidates = select_candidates(scored, top_n=TOP_N, min_score=MIN_SCORE)

candidates["as_of_date"] = datetime.now(timezone.utc)

print(f"Scored {len(scored):,} securities, shortlisted {len(candidates):,} value candidates.")
candidates[["ticker", "sector", "value_score"]].head(10)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

output_path = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{OUTPUT_SCHEMA}/{OUTPUT_TABLE}"

spark.createDataFrame(candidates).write.format("delta").mode("overwrite").option(
    "mergeSchema", "true"
).save(output_path)

print(f"Written {len(candidates):,} rows to {output_path}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
