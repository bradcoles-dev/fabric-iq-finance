# fabric-iq-finance

A public reference implementation applying **Microsoft Fabric IQ** — Ontology, Semantic Model integration, Plan, Graph, Data agent, and Operations agent — to real-money portfolio construction over the S&P 100 + ASX 200 universe.

> **Note:** This is the intelligence layer. The underlying bronze/silver/gold data platform lives in a separate repository, [`dbt-fabric-finance`](https://github.com/bradcoles-dev/dbt-fabric-finance), which this project consumes read-only via a OneLake shortcut — no data is duplicated.

This repository is **code only**. The Fabric IQ items themselves (Ontology, Data agent, Operations agent, Plan) are built by hand in the Fabric portal rather than generated from code, and the accompanying 8-part article series, e-book, and YouTube walkthrough are written independently — neither is part of this repo.

---

## Architecture

```
dbt-fabric-finance (gold layer, cross-workspace)
        │  OneLake shortcut, DirectLake semantic model
        ▼
Lakehouse.Lakehouse ── NB_value_screen ──────────┐
                    ── NB_diversification_graph ──┼──► iq_* Delta tables
                    ── NB_portfolio_optimizer ─────┤
                    ── NB_portfolio_actuals_refresh┘
        │
        ▼
(built manually in the Fabric portal, not in this repo)
Ontology → Data agent / Operations agent / Plan
```

Fabric data agents are read-only NL2SQL/DAX/KQL query generators — they cannot execute custom code. So the actual quant work (sector-relative value scoring, correlation-graph diversification metrics, mean-variance optimization, discrete share allocation) runs ahead of time in the notebooks below and lands in output Delta tables. Those tables are what the hand-built Ontology, Data agent, Operations agent, and Plan items point at and reason over.

---

## Repository layout

```
fabric-iq-finance/
├── src/portfolio_iq/       # the intelligence logic — plain, unit-tested Python
│   ├── gold.py                #   typed readers for Project 1's gold tables
│   ├── screening.py           #   sector-relative value score
│   ├── diversification.py     #   correlation graph, communities, centrality
│   ├── optimizer.py           #   mean-variance optimization (PyPortfolioOpt)
│   └── allocation.py          #   discrete share allocation for a fixed budget
├── tests/                  # pytest — runs standalone against synthetic fixtures
├── Lakehouse.Lakehouse/    # Fabric-managed (git-synced) — do not hand-edit
└── NB_*.Notebook/          # Fabric-managed notebooks (native git percent-cell format)
```

---

## Quickstart

### Prerequisites

- Python 3.11+
- A Microsoft Fabric workspace with an F-SKU capacity attached, git-integrated with this repo

### 1. Clone and install

```bash
git clone https://github.com/bradcoles-dev/fabric-iq-finance.git
cd fabric-iq-finance
pip install -r requirements.txt
```

### 2. Run the test suite

```bash
pytest
ruff check src/ tests/
```

The screening, diversification, optimization, and allocation logic is fully testable offline against synthetic fixtures shaped like the real gold schema — no live Fabric connection required.

### 3. Run the notebooks in Fabric

Upload/sync `NB_value_screen`, `NB_diversification_graph`, and `NB_portfolio_optimizer` (in that order) into the Fabric workspace and run them to produce `iq_value_screen`, `iq_diversification_metrics`, `iq_correlation_edges`, and `iq_portfolio_recommendation`. Schedule `NB_portfolio_actuals_refresh` to run daily once a position is actually purchased, to build up `iq_portfolio_actuals` for the 6-month retrospective.

Each notebook expects a workspace-level **Variable Library** named `Variables` with `WORKSPACE_ID` and `LAKEHOUSE_ID` keys (same pattern `dbt-fabric-finance` uses), and imports `portfolio_iq` from an attached custom Environment built from this package.

### 4. Build the Fabric IQ layer

Ontology, Data agent, Operations agent, and Plan are built directly in the Fabric portal against the `iq_*` tables above and Project 1's `SM_dbt-fabric-finance` semantic model — intentionally not automated here.

---

## Contributing

- Python is linted with Ruff (`ruff check src/ tests/`).
- All logic in `src/portfolio_iq/` must have unit test coverage using synthetic fixtures — no test should require a live Fabric connection.
- Notebooks are thin orchestration only: read data, call `portfolio_iq`, write output. No business logic lives in notebook cells.
- Fabric item folders follow `dbt-fabric-finance`'s `<PREFIX>_<name>.<ItemType>` convention (`NB_`, ...).

---

## License

MIT
