"""Graph-grounded retrieval: optional model planning; deterministic, cited statements only."""

import logging
import re
import time

import networkx as nx

from supplygraph.ai.runtime import Planner
from supplygraph.domain.graph import SupplyGraph
from supplygraph.domain.models import Claim, QueryPlan, QueryRequest, QueryResponse, ScenarioRequest

logger = logging.getLogger("supplygraph")


def resolve_candidates(graph: SupplyGraph, question: str) -> list[dict]:
    q = question.casefold()
    matches = []
    for node in graph.nodes.values():
        id_match = re.search(r"(?<![\w-])" + re.escape(node.id.casefold()) + r"(?![\w-])", q)
        position = id_match.start() if id_match else q.find(node.name.casefold())
        if position >= 0:
            matches.append((position, {"id": node.id, "name": node.name, "kind": node.kind}))
    return [node for _, node in sorted(matches, key=lambda pair: pair[0])][:20]


def parse_question(graph: SupplyGraph, question: str) -> QueryPlan:
    candidates = resolve_candidates(graph, question)
    q = question.casefold()
    duration = re.search(r"(\d+(?:\.\d+)?)\s*days?", q)
    days = float(duration.group(1)) if duration else 14
    if re.search(r"\b(critical|centrality|bottlenecks)\b", q):
        return QueryPlan(operation="critical")
    if not candidates:
        raise ValueError("Name a graph node or its exact evidence ID, such as PORT-0001.")
    node = candidates[0]["id"]
    if re.search(r"\b(path|connects|connection)\b", q) and len(candidates) == 2:
        return QueryPlan(operation="path", node_id=node, target_id=candidates[1]["id"])
    if len(candidates) != 1:
        raise ValueError("Use one node per impact/dependency query, or two nodes for a path query.")
    if re.search(r"\b(upstream|suppliers|ancestors)\b", q):
        return QueryPlan(operation="upstream", node_id=node)
    if re.search(r"\b(downstream|dependents|descendants)\b", q):
        return QueryPlan(operation="downstream", node_id=node)
    if re.search(r"\b(impact|disrupt|disrupted|disruption|outage|fails|closure|closes|shortage|blast)\b", q):
        return QueryPlan(operation="impact", node_id=node, duration_days=days)
    raise ValueError("Supported queries: impact, upstream, downstream, path, or critical nodes.")


def execute_plan(graph: SupplyGraph, plan: QueryPlan) -> list[Claim]:
    if plan.operation == "critical":
        rows = graph.critical(5)
        return [
            Claim(
                text=f"{r['name']} has sampled betweenness {r['betweenness']:.6f} and "
                f"{r['out_degree']} direct dependents (seed 42, up to 32 pivots).",
                evidence_ids=[
                    r.id for r in [*graph.dataset.nodes, *graph.dataset.edges, *graph.dataset.inventories]
                ],
            )
            for r in rows
        ]
    if not plan.node_id:
        raise ValueError("This operation requires a source node.")
    graph.require_node(plan.node_id)
    if plan.operation == "impact":
        result = graph.simulate(
            ScenarioRequest(
                snapshot_id=graph.dataset.snapshot_id,
                disrupted_ids=[plan.node_id],
                duration_days=plan.duration_days,
            )
        )
        return [
            Claim(
                text=f"A {plan.duration_days:g}-day outage at {graph.nodes[plan.node_id].name} "
                f"affects {result.affected_products} products and places {result.lost_product_units:,.2f} "
                f"product units at risk under time-to-shortage-v1.",
                evidence_ids=list(
                    dict.fromkeys(
                        [
                            plan.node_id,
                            *result.evidence_ids,
                            *[
                                r.id
                                for r in [
                                    *graph.dataset.nodes,
                                    *graph.dataset.edges,
                                    *graph.dataset.inventories,
                                ]
                            ],
                        ]
                    )
                ),
            )
        ]
    if plan.operation == "path":
        if not plan.target_id:
            raise ValueError("Path queries require two nodes.")
        path = graph.path(plan.node_id, plan.target_id)
        if not path:
            raise ValueError("No qualified directed dependency path exists in this snapshot.")
        return [
            Claim(text="Dependency path: " + " → ".join(path) + ".", evidence_ids=graph.path_evidence(path))
        ]
    related = sorted(
        nx.ancestors(graph.graph, plan.node_id)
        if plan.operation == "upstream"
        else nx.descendants(graph.graph, plan.node_id)
    )
    related_ids = {plan.node_id, *related}
    claims = [
        Claim(
            text=f"{graph.nodes[plan.node_id].name} has {len(related)} {plan.operation} "
            "dependencies in the qualified graph.",
            evidence_ids=[
                plan.node_id,
                *related,
                *[e.id for e in graph.dataset.edges if e.source in related_ids and e.target in related_ids],
            ],
        )
    ]
    for node in related[:10]:
        source, target = (node, plan.node_id) if plan.operation == "upstream" else (plan.node_id, node)
        path = graph.path(source, target)
        claims.append(Claim(text=" → ".join(path), evidence_ids=graph.path_evidence(path)))
    return claims


def answer(graph: SupplyGraph, request: QueryRequest, planner: Planner | None = None) -> QueryResponse:
    start = time.perf_counter()
    mode = "local-model" if request.use_llm else "deterministic"
    telemetry = {
        "template_version": "query-plan-v1",
        "data_version": graph.dataset.snapshot_id,
        "runtime": planner.name if planner and request.use_llm else "none",
        "model": planner.model if planner and request.use_llm else "none",
        "seed": 42,
        "temperature": 0,
        "retries": 0,
        "validation_failures": 0,
        "tool_calls": [],
    }
    plan = None
    try:
        if request.snapshot_id != graph.dataset.snapshot_id:
            raise ValueError("Query snapshot does not match graph.")
        if request.use_llm:
            if planner is None:
                raise ValueError("Local AI is disabled. Use deterministic mode or configure a local runtime.")
            candidates = resolve_candidates(graph, request.question)
            for attempt in range(2):
                try:
                    raw_plan, metadata = planner.plan(request.question, candidates)
                    plan = QueryPlan.model_validate(raw_plan)
                    allowed = {c["id"] for c in candidates}
                    if any(n and n not in allowed for n in [plan.node_id, plan.target_id]):
                        raise ValueError("Model selected a node not grounded in the question.")
                    telemetry.update(metadata)
                    break
                except Exception:
                    telemetry["validation_failures"] += 1
                    if attempt == 1:
                        raise ValueError(
                            "Local model failed structured output or evidence validation."
                        ) from None
                    telemetry["retries"] += 1
        else:
            plan = parse_question(graph, request.question)
        telemetry["tool_calls"] = [plan.model_dump()]
        claims = execute_plan(graph, plan)
        ids = list(dict.fromkeys(e for c in claims for e in c.evidence_ids))
        if any(e not in graph.evidence for e in ids):
            raise ValueError("Required supporting evidence is missing.")
        telemetry["input_source_ids"] = sorted({graph.evidence[e].source_id for e in ids})
        response = QueryResponse(
            status="answered", mode=mode, plan=plan, claims=claims, evidence_ids=ids, telemetry=telemetry
        )
    except (ValueError, KeyError, nx.NetworkXException) as exc:
        response = QueryResponse(
            status="abstained", mode=mode, plan=plan, reason=str(exc), telemetry=telemetry
        )
    telemetry["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
    response.telemetry = telemetry
    logger.info("graph_query", extra={"event_data": telemetry | {"status": response.status}})
    return response
