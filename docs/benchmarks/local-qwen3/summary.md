# Measured benchmark example

Run: 2026-09-27T21:24:32.235119+00:00
Hardware: {'os': 'macOS-26.6.2-arm64-arm-64bit', 'cpu': 'Apple M5', 'logical_cpus': 10, 'python': '3.12.14', 'networkx': '3.7', 'application_version': '0.1.0'}
Model: qwen3:8b / ollama

Golden query accuracy: 100.0% (10 cases).
Impact precision / recall: 100.0% / 100.0% (7 hand-audited cases).
Unsupported citation rate: 0.0% over 22 template claims.
Alternate-path correctness: 100% (one hand-audited alternate fixture).

| Nodes | Edges | Build ms | Impact p50 ms | Impact p95 ms | Centrality ms | Python peak MiB |
|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 1,124 | 4.16 | 28.28 | 29.44 | 10.56 | 6.82 |

tracemalloc enabled; five warm-cache impact repetitions by default; microbenchmark, not end-to-end throughput. tracemalloc Python allocation peak, excludes native/GPU memory.
These are small synthetic correctness fixtures and bounded graph microbenchmarks, not proof of enterprise accuracy or scalability.
A zero unsupported-citation rate is enforced by deterministic templates; it does not measure arbitrary natural-language truth.

Local model query outcome accuracy: 100.0%; see results.json for per-case latency and abstentions.
