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
METRICS_TABLE = "iq_diversification_metrics"
EDGES_TABLE = "iq_correlation_edges"
CORRELATION_THRESHOLD = 0.5

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import networkx as nx

from portfolio_iq.diversification import build_correlation_graph, compute_diversification_metrics

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

candidate_tickers = candidates["ticker"].tolist()
print(f"Building the correlation graph over {len(candidate_tickers)} value candidates.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

graph = build_correlation_graph(
    return_covariance, tickers=candidate_tickers, correlation_threshold=CORRELATION_THRESHOLD
)
metrics = compute_diversification_metrics(graph)

edges = nx.to_pandas_edgelist(graph, source="ticker_a", target="ticker_b")

print(f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges, {metrics['community_id'].nunique()} communities")
metrics.head(10)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

metrics_path = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{DBO_SCHEMA}/{METRICS_TABLE}"
edges_path = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Tables/{DBO_SCHEMA}/{EDGES_TABLE}"

spark.createDataFrame(metrics).write.format("delta").mode("overwrite").option("mergeSchema", "true").save(
    metrics_path
)
spark.createDataFrame(edges).write.format("delta").mode("overwrite").option("mergeSchema", "true").save(
    edges_path
)

print(f"Written {len(metrics):,} rows to {metrics_path}")
print(f"Written {len(edges):,} rows to {edges_path}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
