# Data dictionary and provenance

All data is synthetic. No real company dependencies or current risk claims are included. Port labels and country coordinates provide geographic context only.

## Snapshot envelope

| Field | Meaning |
|---|---|
| `schema_version` | `1.0` only |
| `snapshot_id` | Stable immutable dataset version; 1–96 safe identifier characters |
| `source_id` | Dataset provenance identifier |
| `effective_at` | Timezone-aware business snapshot time |
| `seed` | Reproducibility metadata |
| `nodes`, `edges`, `inventories` | Typed record collections |

Every record has a globally unique `id` within its snapshot, `source_id`, timezone-aware `ingested_at`, `validation_status=valid`, and optional `lineage`. Rejected records are retained as identified issues in a validation report, not silently omitted from a partial import. Uploaded raw files are not retained by the service.

## Nodes

| Kind | ID example | Operational meaning |
|---|---|---|
| supplier | SUP-0001 | Legal/entity-level supplier with tier 1–3 in demo |
| site | SITE-0001 | Supplier manufacturing site |
| component | CMP-0001 | Purchased material/component SKU |
| product | PRD-0001 | Finished-good SKU, daily demand and unit value |
| facility | FAC-0001 | Assembly or distribution facility |
| port | PORT-0001 | Port dependency |
| route | RTE-0001 | Transport lane represented as a disruptable node |
| customer | CUS-0001 | Demand endpoint |

`name`, `country`, `latitude`, `longitude` support identification and geography. `daily_demand` is base units/day; `unit_value` is synthetic USD/unit. The v1 dataset uses consistent base units and one currency; no implicit currency or unit conversion occurs.

## Edges and BOM

Edges point upstream → downstream. Kinds: `supply`, `tier`, `transport`, `bom`, `manufacture`, `demand`, `ownership`. Ownership edges are informational and excluded from propagation. Every operational edge has a target-local `group`.

All incoming groups must be supplied. Sources within one group are interchangeable. `approved=true` and `capacity >= required_capacity` qualify an edge. Capacities are dedicated normalized ratios in the demo (requirement 1); the model does not pool partial sources. Group alternatives must have consistent `quantity` and `required_capacity`.

BOM `quantity` is component base units per product unit. Generator inventory usage reconciles the represented BOM (`sum(product demand × quantity)`) plus explicitly recorded synthetic service/spares demand. The propagation engine uses that supplied `daily_usage`; it does not run an MRP explosion or allocate common stock across competing products. Reconcile usage upstream when importing your own network.

`lead_time_days` is a deterministic supply pipeline buffer; a complete disruption reaches the receiver after that buffer is exhausted. Do not also include this quantity in on-hand stock. Actual calendars, sailing schedules, lead-time distributions, and emergency qualification are out of scope.

## Inventory

`node_id`, `facility_id`, `on_hand`, `daily_usage` identify aggregate usable inventory. A node can have only one record in v1. `facility_id` must reference a facility. Coverage is `on_hand / daily_usage`; zero usage triggers a warning and contributes zero buffer. A direct outage of the inventory's own node bypasses its stock; stock location outages do not themselves destroy inventory. Facility-to-product dependencies model assembly availability separately.

## Demo cases

Seed 42 creates 200 suppliers, 40 sites, 800 components, 80 products, 25 facilities, 8 ports, 24 routes and 30 customers: 1,207 nodes and 1,754 relationships. Eight isolated supplier nodes are deliberately retained. Other seeded conditions include zero stock, unapproved alternates, capacity-inadequate alternates, and a zero-usage spare inventory record.

Bootstrap loads September 1, 2026, plus a September 15 snapshot with inventory reduced to 65% of the initial quantity. This is an explicit hypothetical inventory change, not historical observation. Node IDs persist across both snapshots.

`tests/unit/test_validation.py` creates rejected examples: duplicate IDs, self-links, cycles, orphan inventory, invalid facilities, non-finite values, negative inventory, timezone omissions, inconsistent alternative requirements, and uncovered groups. The independent `evaluation/fixtures.py` golden graph defines exact expected outcomes.

## Data creation

```sh
python -m supplygraph.data.generator --seed 42 --output data/sample/demo.json
python -m supplygraph.data.generator --seed 73 --scale 10 --output data/generated/large.json
```

The committed JSON is compact (about 1 MB); the JSON Schema is in `data/schemas/dataset.schema.json`. Ingestion accepts JSON only, maximum 25 MiB. Larger graph microbenchmarks are generated directly in memory; they do not imply that a 100k-node JSON import fits that upload limit.
