"""Deterministic AND/OR dependencies, with inventory and in-transit buffers."""

import math
from collections import defaultdict

import networkx as nx

from supplygraph.domain.models import Alternate, Dataset, Impact, ScenarioRequest, ScenarioResult

ASSUMPTIONS = [
    "Complete node outage; constant demand; no allocation, substitution consumption, or post-outage catch-up.",
    "All dependency groups are required; one approved, full-capacity source satisfies a group.",
    "Lead time represents already committed in-transit supply; inventory buffers are aggregate and non-overlapping.",
    "Exposure is product units at risk × synthetic unit value, not realized revenue loss.",
    "Alternates are already qualified, instantly available, and dedicated; shared capacity is not optimized.",
]


class SupplyGraph:
    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self.nodes = {n.id: n for n in dataset.nodes}
        self.evidence = {r.id: r for r in [*dataset.nodes, *dataset.edges, *dataset.inventories]}
        self.graph = nx.DiGraph()
        self.graph.add_nodes_from(self.nodes)
        self.groups = defaultdict(lambda: defaultdict(list))
        for edge in dataset.edges:
            if edge.kind != "ownership":
                self.groups[edge.target][edge.group].append(edge)
                if edge.approved and edge.capacity >= edge.required_capacity:
                    self.graph.add_edge(edge.source, edge.target)
        self.order = list(nx.topological_sort(self.graph))
        self.inventory = {i.node_id: i for i in dataset.inventories}

    def require_node(self, node_id: str):
        if node_id not in self.nodes:
            raise KeyError(node_id)

    def path_evidence(self, path: list[str]) -> list[str]:
        ids = list(path)
        for source, target in zip(path, path[1:], strict=False):
            ids.extend(
                e.id
                for group in self.groups[target].values()
                for e in group
                if e.source == source and e.approved and e.capacity >= e.required_capacity
            )
        return list(dict.fromkeys(ids))

    def path(self, source: str, target: str) -> list[str]:
        self.require_node(source)
        self.require_node(target)
        try:
            return nx.shortest_path(self.graph, source, target)
        except nx.NetworkXNoPath:
            return []

    def critical(self, limit: int = 20) -> list[dict]:
        # Sampled betweenness remains reproducible. This is topology, not probability of loss.
        scores = nx.betweenness_centrality(self.graph, k=min(32, len(self.nodes)), seed=42)
        degree = nx.out_degree_centrality(self.graph)
        rows = [
            {
                "node_id": n,
                "name": self.nodes[n].name,
                "kind": self.nodes[n].kind,
                "betweenness": round(scores[n], 8),
                "out_degree": self.graph.out_degree(n),
                "degree_centrality": round(degree[n], 8),
                "evidence_ids": [n],
            }
            for n in self.nodes
        ]
        return sorted(rows, key=lambda r: (-r["betweenness"], -r["out_degree"], r["node_id"]))[:limit]

    def simulate(self, request: ScenarioRequest) -> ScenarioResult:
        if request.snapshot_id != self.dataset.snapshot_id:
            raise ValueError("Scenario snapshot does not match graph.")
        roots = set(request.disrupted_ids)
        for node in roots:
            self.require_node(node)
        candidates = set(roots)
        for node in roots:
            candidates.update(nx.descendants(self.graph, node))
        failure = dict.fromkeys(self.nodes, math.inf)
        paths: dict[str, list[str]] = {}
        proofs: dict[str, list[str]] = {}
        alternates: list[Alternate] = []
        for node in self.order:
            if node in roots:
                failure[node], paths[node], proofs[node] = 0.0, [node], [node]
                continue
            if node not in candidates:
                continue
            controlling = None
            for group_id, edges in self.groups[node].items():
                eligible = [e for e in edges if e.approved and e.capacity >= e.required_capacity]
                # A group fails only after the last qualified source's buffer expires.
                chosen = max(eligible, key=lambda e: (failure[e.source] + e.lead_time_days, e.id))
                expires = failure[chosen.source] + chosen.lead_time_days
                if math.isinf(expires):
                    threatened = [e for e in eligible if math.isfinite(failure[e.source])]
                    if threatened:
                        alternates.append(
                            Alternate(
                                target_id=node,
                                source_id=chosen.source,
                                group=group_id,
                                evidence_ids=[node, chosen.source, chosen.id, *[e.id for e in threatened]],
                            )
                        )
                if controlling is None or expires < controlling[0]:
                    controlling = (expires, chosen, eligible)
            if controlling and math.isfinite(controlling[0]):
                expires, chosen, eligible = controlling
                inventory = self.inventory.get(node)
                coverage = (
                    inventory.on_hand / inventory.daily_usage if inventory and inventory.daily_usage else 0
                )
                failure[node] = expires + coverage
                paths[node] = paths[chosen.source] + [node]
                proof = [node]
                for edge in eligible:
                    proof += [edge.id, edge.source, *proofs.get(edge.source, [])]
                if inventory:
                    proof.append(inventory.id)
                proofs[node] = list(dict.fromkeys(proof))
        impacts = []
        for node_id in sorted(candidates, key=lambda n: (failure[n], n)):
            day = failure[node_id]
            if day >= request.duration_days:
                continue
            node = self.nodes[node_id]
            units = max(0, request.duration_days - day) * node.daily_demand if node.kind == "product" else 0
            impacts.append(
                Impact(
                    node_id=node_id,
                    name=node.name,
                    kind=node.kind,
                    shortage_day=round(day, 4),
                    lost_units=round(units, 2),
                    exposure_value=round(units * node.unit_value, 2),
                    path=paths[node_id],
                    evidence_ids=proofs[node_id],
                )
            )
        product_impacts = [i for i in impacts if i.kind == "product"]
        evidence = list(dict.fromkeys(e for i in impacts for e in i.evidence_ids))
        return ScenarioResult(
            snapshot_id=self.dataset.snapshot_id,
            disrupted_ids=sorted(roots),
            duration_days=request.duration_days,
            candidate_count=len(candidates),
            affected_count=len(impacts),
            affected_products=len(product_impacts),
            lost_product_units=round(sum(i.lost_units for i in product_impacts), 2),
            product_exposure_value=round(sum(i.exposure_value for i in product_impacts), 2),
            impacts=impacts,
            alternates=alternates,
            evidence_ids=evidence,
            assumptions=ASSUMPTIONS,
        )
