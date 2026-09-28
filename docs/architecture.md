# Architecture

SupplyGraph separates facts, deterministic models, and model-assisted intent selection. The Python package is the business layer. FastAPI validates HTTP contracts and delegates; React renders results and does no supply-chain calculation.

- `domain/models.py`: strict Pydantic schemas, evidence identity, typed plans and results.
- `domain/graph.py`: qualified dependency graph, AND/OR propagation, shortest paths, sampled centrality.
- `data/generator.py`: fixed-seed synthetic electronics data with provenance and seeded anomalies.
- `data/validation.py`: structural and domain validation before any graph mutation.
- `data/repository.py`: SQLAlchemy graph tables, immutable snapshots, transactional ingestion receipts.
- `services/network.py`: bounded graph cache, overview, neighborhood extraction.
- `ai/runtime.py`: local-only Ollama/llama.cpp adapters; `ai/query.py`: intent validation, graph retrieval, deterministic statement templates.
- `evaluation/`: independent hand-audited fixtures and scalable graph benchmarks.
- `observability/`: JSON logs and request-scoped trace IDs.

## Deployment

Compose runs PostgreSQL, API, and nginx/React. Ollama is an optional profile. Host bindings are loopback only. PostgreSQL has no host port. The API uses a writer role for validated ingestion and a separate reader role for graph loads. On native development SQLite uses the same repository layer; PostgreSQL behavior is exercised in CI.

Snapshots are append-only through the API. A snapshot contains node, relationship, and inventory records, not a mutable pointer to another version. A content digest and idempotency receipt make retried imports safe; content changes require a new snapshot ID. Import transactions never partially commit.

Graphs are loaded into a per-process, three-snapshot LRU. Topological ordering is computed on load. UI neighborhoods are capped at 200 nodes by default (1,000 maximum); analytics use the entire snapshot. Read endpoints paginate nodes and validation reports. A large graph can consume substantial memory; run the supplied benchmark before increasing limits.

## Computation contract

For an outage set, a directly disrupted node fails at day zero. For every downstream node in topological order:

1. Exclude ownership edges, unapproved sources, and sources below the required dedicated capacity.
2. For each dependency group, take the maximum of `source shortage day + edge lead-time days`; a surviving source has infinite availability.
3. Take the minimum expiry across required groups (AND semantics).
4. Add receiving inventory coverage, `on_hand / daily_usage`, when usage is positive.
5. Report a node as affected only if shortage occurs strictly before the scenario ends.

For products, `lost_units = daily_demand × max(0, duration - shortage_day)` and modeled exposure is `lost_units × unit_value`. Products are counted once even if several BOM paths fail. Customers are affected endpoints, not additional product revenue.

Lead time models already committed pipeline stock. It is not a recovery lead time. Inventory is one aggregate pool per node; zero-usage stock gives no assumed buffer. The model is a screening calculation with no post-outage recovery simulation. Read all assumptions in `data-model.md` before operational use.

The critical-node ranking uses NetworkX normalized betweenness with up to 32 pivots and seed 42, then out-degree as a tie-break. It measures structural intermediation, not expected financial loss. Isolated nodes remain visible.

## API boundaries

`GET /api/v1/*` reads facts and computed graph views. `POST /api/v1/analysis/*` is read-only despite using POST for typed request bodies. `POST /api/v1/ingestions` is the sole graph mutation, protected by a bearer token and idempotency key. The model has no mutation tool.

Full interface: `/docs` (bundled Swagger assets), `/openapi.json`, `/health`, `/ready`. Errors use `{error: {code, message, trace_id, details}}`. Invalid imports include the validation report in `details` and persist it to the ledger.

## Extensibility

A new local planner implements `Planner.plan(question, candidates) -> (QueryPlan, metadata)`. It cannot change the algorithm layer. Add new operations to the typed allowlist, deterministic executor, tests, and evaluation fixtures together. Keep generated narrative templated until an independently evaluated entailment check exists.
