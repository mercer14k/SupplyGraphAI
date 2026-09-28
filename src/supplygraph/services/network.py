"""Application services separate persistence and algorithms from HTTP and presentation."""

from collections import Counter
from functools import lru_cache

from supplygraph.data.repository import Repository
from supplygraph.domain.graph import SupplyGraph


class NetworkService:
    def __init__(self, repository: Repository):
        self.repository = repository
        self.graph = lru_cache(maxsize=3)(self._load_graph)

    def _load_graph(self, snapshot_id: str):
        return SupplyGraph(self.repository.load(snapshot_id))

    def overview(self, snapshot_id: str):
        graph = self.graph(snapshot_id)
        counts = Counter(n.kind for n in graph.nodes.values())
        single = sum(
            1
            for groups in graph.groups.values()
            for edges in groups.values()
            if sum(e.approved and e.capacity >= e.required_capacity for e in edges) == 1
        )
        return {
            "snapshot_id": snapshot_id,
            "source_id": graph.dataset.source_id,
            "effective_at": graph.dataset.effective_at,
            "nodes": len(graph.nodes),
            "edges": len(graph.dataset.edges),
            "counts": dict(counts),
            "single_source_groups": single,
            "inventory_records": len(graph.inventory),
            "supplier_tiers": len({n.tier for n in graph.nodes.values() if n.kind == "supplier"}),
            "countries": len({n.country for n in graph.nodes.values()}),
            "critical": graph.critical(8),
            "origin": "computed",
        }

    def graph_view(self, snapshot_id: str, focus: str | None = None, limit: int = 200):
        graph = self.graph(snapshot_id)
        if focus:
            graph.require_node(focus)
            # Breadth-first neighborhood limits render cost but never truncates analytics.
            selected = {focus}
            frontier = [focus]
            undirected = graph.graph.to_undirected(as_view=True)
            for node in frontier:
                for neighbor in sorted(undirected.neighbors(node)):
                    if neighbor not in selected and len(selected) < limit:
                        selected.add(neighbor)
                        frontier.append(neighbor)
                if len(selected) >= limit:
                    break
        else:
            ordered = sorted(
                graph.nodes,
                key=lambda n: (graph.nodes[n].kind not in {"port", "route", "site", "supplier"}, n),
            )
            selected = set(ordered[:limit])
        return {
            "snapshot_id": snapshot_id,
            "nodes": [graph.nodes[n] for n in sorted(selected)],
            "edges": [e for e in graph.dataset.edges if e.source in selected and e.target in selected],
            "total_nodes": len(graph.nodes),
            "truncated": len(selected) < len(graph.nodes),
        }
