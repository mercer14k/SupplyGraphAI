"""One-command reproducible correctness + 1k/10k/100k graph microbenchmark."""

import argparse
import csv
import json
import logging
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from supplygraph.ai.query import answer, parse_question
from supplygraph.ai.runtime import LocalPlanner
from supplygraph.domain.graph import SupplyGraph
from supplygraph.domain.models import Dataset, Edge, Node, QueryRequest, ScenarioRequest
from supplygraph.evaluation.fixtures import IMPACT_CASES, QUERY_CASES, truth_dataset


def hardware():
    cpu = platform.processor() or platform.machine()
    if sys.platform == "darwin":
        try:
            cpu = subprocess.check_output(
                ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return {
        "os": platform.platform(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "networkx": version("networkx"),
        "application_version": version("supplygraph-ai"),
    }


def accuracy(planner=None):
    graph = SupplyGraph(truth_dataset())
    tp = fp = fn = 0
    impact_results = []
    for case in IMPACT_CASES:
        result = graph.simulate(
            ScenarioRequest(snapshot_id="GOLDEN", disrupted_ids=case["roots"], duration_days=case["days"])
        )
        predicted = {i.node_id for i in result.impacts}
        expected = set(case["affected"])
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        impact_results.append(
            {
                "roots": case["roots"],
                "days": case["days"],
                "correct": predicted == expected,
                "units_correct": result.lost_product_units == case["units"],
            }
        )
    query_results = []
    unsupported = total_claims = 0
    for question, operation, node, target in QUERY_CASES:
        request = QueryRequest(snapshot_id="GOLDEN", question=question, use_llm=planner is not None)
        response = answer(graph, request, planner)
        if planner:
            plan = response.plan
            actual = (
                (plan.operation, plan.node_id, plan.target_id)
                if plan and response.status == "answered"
                else (None, None, None)
            )
            # A reversed directed path must abstain, despite a valid intent.
            expected = (
                (None, None, None) if operation == "path" and node == "PRD-A" else (operation, node, target)
            )
        else:
            try:
                plan = parse_question(graph, question)
                actual = (plan.operation, plan.node_id, plan.target_id)
            except ValueError:
                actual = (None, None, None)
            expected = (operation, node, target)
        query_results.append(
            {
                "question": question,
                "correct": actual == expected,
                "status": response.status,
                "latency_ms": response.telemetry["latency_ms"],
                "validation_failures": response.telemetry["validation_failures"],
                "telemetry": response.telemetry,
            }
        )
        for claim in response.claims:
            total_claims += 1
            # Citation integrity plus deterministic rendering; this is not a semantic LLM judge.
            unsupported += int(
                not claim.evidence_ids or any(e not in graph.evidence for e in claim.evidence_ids)
            )
    protected = graph.simulate(
        ScenarioRequest(snapshot_id="GOLDEN", disrupted_ids=["SUP-A"], duration_days=7)
    ).alternates
    alternate_correct = {(a.source_id, a.target_id, a.group) for a in protected} == {
        ("SUP-B", "CMP-B", "part")
    }
    return {
        "impact_precision": tp / (tp + fp) if tp + fp else 1,
        "impact_recall": tp / (tp + fn) if tp + fn else 1,
        "query_accuracy": sum(r["correct"] for r in query_results) / len(query_results),
        "unsupported_claim_rate": unsupported / total_claims if total_claims else None,
        "claim_count": total_claims,
        "unsupported_claim_definition": "Missing/invalid citation IDs in deterministic templates; not general hallucination detection.",
        "alternate_path_correctness": int(alternate_correct),
        "impact_cases": impact_results,
        "query_cases": query_results,
    }


def performance_dataset(size):
    # Eight layers keep depth fixed. This microbenchmark deliberately separates graph scaling
    # from data ingestion and realistic industry topology; see docs/evaluation.md.
    stamp = datetime(2026, 1, 1, tzinfo=UTC)

    def meta(rid):
        return dict(id=rid, source_id="perf-layered-v1", ingested_at=stamp)

    width = max(1, size // 8)
    nodes = []
    edges = []
    for i in range(size):
        layer = min(i // width, 7)
        kind = "supplier" if layer < 3 else "component" if layer < 7 else "product"
        nodes.append(
            Node(
                **meta(f"N-{i:06d}"),
                kind=kind,
                name=f"Benchmark node {i}",
                daily_demand=10 if layer == 7 else 0,
            )
        )
        if width <= i < 2 * width:
            edges.append(
                Edge(
                    **meta(f"S-{i:06d}"),
                    source="N-000000",
                    target=f"N-{i:06d}",
                    kind="supply",
                    group="shared-risk",
                )
            )
        if i >= width:
            parent = i - width
            edges.append(
                Edge(
                    **meta(f"E-{i:06d}"),
                    source=f"N-{parent:06d}",
                    target=f"N-{i:06d}",
                    kind="supply",
                    group="required",
                )
            )
            if i % 7 == 0:
                alternate = max((layer - 1) * width, parent - 1)
                if alternate != parent:
                    edges.append(
                        Edge(
                            **meta(f"A-{i:06d}"),
                            source=f"N-{alternate:06d}",
                            target=f"N-{i:06d}",
                            kind="supply",
                            group="required",
                        )
                    )
    return Dataset(
        snapshot_id=f"PERF-{size}", source_id="perf-layered-v1", effective_at=stamp, nodes=nodes, edges=edges
    )


def performance(size, repeats):
    tracemalloc.start()
    t = time.perf_counter()
    dataset = performance_dataset(size)
    generate_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    graph = SupplyGraph(dataset)
    build_ms = (time.perf_counter() - t) * 1000
    roots = [f"N-{i:06d}" for i in range(min(20, size // 8))]
    request = ScenarioRequest(snapshot_id=dataset.snapshot_id, disrupted_ids=roots, duration_days=14)
    # Warm-up excluded; no network, disk, rendering, or model latency included.
    graph.simulate(request)
    timings = []
    for _ in range(repeats):
        t = time.perf_counter()
        result = graph.simulate(request)
        timings.append((time.perf_counter() - t) * 1000)
    t = time.perf_counter()
    graph.critical(10)
    centrality_ms = (time.perf_counter() - t) * 1000
    path_target = f"N-{7 * (size // 8):06d}"
    t = time.perf_counter()
    graph.path("N-000000", path_target)
    path_ms = (time.perf_counter() - t) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "nodes": size,
        "edges": len(dataset.edges),
        "affected": result.affected_count,
        "repeats": repeats,
        "generate_ms": round(generate_ms, 2),
        "graph_build_ms": round(build_ms, 2),
        "impact_p50_ms": round(statistics.median(timings), 2),
        "impact_p95_ms": round(sorted(timings)[min(len(timings) - 1, int(len(timings) * 0.95))], 2),
        "sampled_centrality_ms": round(centrality_ms, 2),
        "path_ms": round(path_ms, 2),
        "peak_traced_python_mib": round(peak / 1024 / 1024, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/benchmarks"))
    parser.add_argument("--sizes", type=int, nargs="+", default=[1000, 10000, 100000])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--model", default=None, help="Optional locally installed Ollama model")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    if any(s < 100 or s > 200000 for s in args.sizes) or not 1 <= args.repeats <= 100:
        parser.error("sizes must be 100..200000 and repeats 1..100")
    logging.getLogger("supplygraph").setLevel(logging.ERROR)
    metadata = {
        "timestamp": datetime.now(UTC).isoformat(),
        "hardware": hardware(),
        "seed": 42,
        "model": args.model or "none",
        "runtime": "ollama" if args.model else "none",
        "template": "query-plan-v1",
        "performance_topology": "eight-layer DAG with shared risk root; broad fan-out; distinct from synthetic electronics demo",
        "memory_method": "tracemalloc Python allocation peak, excludes native/GPU memory",
        "timing_note": "tracemalloc enabled; five warm-cache impact repetitions by default; microbenchmark, not end-to-end throughput",
    }
    result = {"metadata": metadata, "evaluation": accuracy()}
    if args.model:
        result["local_model_evaluation"] = accuracy(LocalPlanner(args.base_url, args.model))
    result["performance"] = []
    for size in args.sizes:
        row = performance(size, args.repeats)
        result["performance"].append(row)
        print(json.dumps(row), flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(json.dumps(result, indent=2))
    with (args.output / "performance.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["performance"][0]))
        writer.writeheader()
        writer.writerows(result["performance"])
    e = result["evaluation"]
    lines = [
        "# Measured benchmark example",
        "",
        f"Run: {metadata['timestamp']}",
        f"Hardware: {metadata['hardware']}",
        f"Model: {metadata['model']} / {metadata['runtime']}",
        "",
        f"Golden query accuracy: {e['query_accuracy']:.1%} ({len(e['query_cases'])} cases).",
        f"Impact precision / recall: {e['impact_precision']:.1%} / {e['impact_recall']:.1%} ({len(e['impact_cases'])} hand-audited cases).",
        f"Unsupported citation rate: {e['unsupported_claim_rate']:.1%} over {e['claim_count']} template claims.",
        f"Alternate-path correctness: {e['alternate_path_correctness']:.0%} (one hand-audited alternate fixture).",
        "",
        "| Nodes | Edges | Build ms | Impact p50 ms | Impact p95 ms | Centrality ms | Python peak MiB |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in result["performance"]:
        lines.append(
            f"| {r['nodes']:,} | {r['edges']:,} | {r['graph_build_ms']} | {r['impact_p50_ms']} | {r['impact_p95_ms']} | {r['sampled_centrality_ms']} | {r['peak_traced_python_mib']} |"
        )
    lines += [
        "",
        metadata["timing_note"] + ". " + metadata["memory_method"] + ".",
        "These are small synthetic correctness fixtures and bounded graph microbenchmarks, not proof of enterprise accuracy or scalability.",
        "A zero unsupported-citation rate is enforced by deterministic templates; it does not measure arbitrary natural-language truth.",
    ]
    if args.model:
        e = result["local_model_evaluation"]
        lines += [
            "",
            f"Local model query outcome accuracy: {e['query_accuracy']:.1%}; see results.json for per-case latency and abstentions.",
        ]
    (args.output / "summary.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
