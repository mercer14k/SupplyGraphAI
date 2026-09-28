"""Atomic validation: rejected datasets produce reports, never partial graphs."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import PurePath

import networkx as nx
from pydantic import ValidationError

from supplygraph.domain.models import Dataset, ValidationIssue, ValidationReport


def validate_bytes(raw: bytes, filename: str = "dataset.json") -> tuple[Dataset | None, ValidationReport]:
    report = ValidationReport(
        id="VAL-" + hashlib.sha256(raw).hexdigest()[:20],
        valid=False,
        filename=PurePath(filename.replace("\\", "/")).name[:160],
        created_at=datetime.now(UTC),
    )
    try:
        dataset = Dataset.model_validate_json(raw)
    except ValidationError as exc:
        report.errors = [
            ValidationIssue(code=e["type"], message=e["msg"], location=".".join(map(str, e["loc"])))
            for e in exc.errors(include_input=False)
        ]
        return None, report
    report.source_id = dataset.source_id
    report.snapshot_id = dataset.snapshot_id
    report.node_count, report.edge_count = len(dataset.nodes), len(dataset.edges)
    seen: set[str] = set()
    nodes = {n.id: n for n in dataset.nodes}
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)

    def error(code: str, message: str, rid: str):
        report.errors.append(ValidationIssue(code=code, message=message, record_id=rid))

    for record in [*dataset.nodes, *dataset.edges, *dataset.inventories]:
        if record.id in seen:
            error("duplicate_id", "IDs must be unique across all evidence records.", record.id)
        seen.add(record.id)
        if record.ingested_at.tzinfo is None:
            error("timezone_required", "Use an ingestion timestamp with timezone.", record.id)
    if dataset.effective_at.tzinfo is None:
        error("timezone_required", "Snapshot effective time must include timezone.", dataset.snapshot_id)
    groups: dict[tuple[str, str], list] = {}
    for edge in dataset.edges:
        if edge.source not in nodes or edge.target not in nodes:
            error("dangling_edge", "Both edge endpoints must exist in the snapshot.", edge.id)
        if edge.source == edge.target:
            error("self_dependency", "A node cannot depend on itself.", edge.id)
        if edge.kind != "ownership":
            graph.add_edge(edge.source, edge.target)
            groups.setdefault((edge.target, edge.group), []).append(edge)
    if not nx.is_directed_acyclic_graph(graph):
        error(
            "dependency_cycle",
            "Dependency cycles require an explicit flow model; snapshot rejected.",
            dataset.snapshot_id,
        )
    for (target, group), edges in groups.items():
        if not any(e.approved and e.capacity >= e.required_capacity for e in edges):
            error(
                "uncovered_group", f"Dependency group {group} has no qualified full-capacity source.", target
            )
        if len({e.required_capacity for e in edges}) > 1 or len({e.quantity for e in edges}) > 1:
            error(
                "inconsistent_group",
                "Interchangeable sources must share capacity and BOM requirements.",
                target,
            )
    inv_nodes: set[str] = set()
    for inv in dataset.inventories:
        if inv.node_id not in nodes or inv.facility_id not in nodes:
            error("orphan_inventory", "Inventory references a missing node or facility.", inv.id)
        elif nodes[inv.facility_id].kind != "facility":
            error("invalid_facility", "Inventory location must be a facility.", inv.id)
        if inv.node_id in inv_nodes:
            error("ambiguous_stock", "v1 requires one aggregate inventory record per node.", inv.id)
        inv_nodes.add(inv.node_id)
        if inv.daily_usage == 0:
            report.warnings.append(
                ValidationIssue(
                    code="zero_usage",
                    record_id=inv.id,
                    message="Zero-usage stock contributes no inventory buffer; demand is unknown.",
                )
            )
    isolated = list(nx.isolates(graph))
    if isolated:
        report.warnings.append(
            ValidationIssue(code="isolated_nodes", message=f"{len(isolated)} isolated nodes.")
        )
    report.valid = not report.errors
    return (dataset if report.valid else None), report


def canonical_bytes(dataset: Dataset) -> bytes:
    payload = dataset.model_dump(mode="json")
    for key in ("nodes", "edges", "inventories"):
        payload[key] = sorted(payload[key], key=lambda record: record["id"])
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
