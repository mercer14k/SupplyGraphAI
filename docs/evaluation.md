# Evaluation methodology

Run all deterministic correctness fixtures plus scale benchmarks with one command:

```sh
python -m supplygraph.evaluation.benchmark --output output/benchmarks
```

Optional local planner comparison:

```sh
python -m supplygraph.evaluation.benchmark --sizes 1000 --model qwen3:8b --output output/qwen3
```

Each run writes `results.json`, `performance.csv`, and `summary.md`, including hardware, Python/NetworkX/application versions, seed, topology, model configuration and timestamp. Committed examples in `docs/benchmarks/` came from actual execution, not target numbers.

## Correctness

The golden network is hand-authored separately from the random generator. SUP-A feeds CMP-A and CMP-B. CMP-A has a one-day inbound buffer and two days of stock. CMP-B survives through a full-capacity SUP-B alternate. An insufficient SUP-B → CMP-A candidate cannot protect it. For a seven-day SUP-A outage, PRD-A loses exactly `(7−3) × 10 = 40` units while PRD-B remains supplied.

Seven cases cover supplier, port, route, facility, component, horizon boundary and simultaneous source outages. Impact precision and recall are micro-averages over expected affected-node sets. Product units are checked independently against fixed expectations. Alternate correctness compares the exact protected source/target/group set. Negative tests independently remove approval, evidence, or schema fields.

Ten natural-language cases measure the operation and grounded entity selection, including unknown IDs and unsupported questions. Deterministic parser accuracy and local-model outcome accuracy are distinct: an invalid directed path is a correctly parsed intent but must abstain when executed. These are tiny smoke evaluation sets, not representative benchmarks of language understanding.

Unsupported-claim rate measures missing/unknown citation IDs in deterministic rendered statements. All business text is templated; zero unsupported citations does not prove arbitrary narrative entailment, causal completeness, factual input accuracy, or safety under every prompt injection.

## Scale and timing

The 1k/10k/100k benchmarks generate eight-layer dependency DAGs with a shared risk root. An outage reaches most downstream nodes; the 100k example affects 87,520 nodes. It exercises broad fan-out, not just a tiny neighborhood.

Measurements: dataset construction, graph initialization, five warm-cache impact runs (median and nearest-rank p95), one sampled-centrality run, one path lookup, and peak Python allocations with `tracemalloc`. Tracing is enabled during timings and adds overhead. Peak values exclude native allocations, browser, database and GPU memory. Only the impact timing has repeated samples; five repeats cannot characterize stable tail latency.

This is an in-process microbenchmark. It excludes HTTP serialization, database reads, validation, UI rendering and local inference. It is not an end-to-end SLA or proof of 100k-node API capacity. Increasing graph depth or alternate fan-in increases evidence-materialization costs; JSON response size can become the bottleneck. The realistic demo generator is separately configurable by seed and scale.

The fixed seed specifies graph sampling and data generation. Results still depend on software versions, thermals, background processes and hardware. Do not compare numbers obtained from different topologies or disabled tracing without labeling the differences.
