"""Hand-audited independent golden network, deliberately separate from random generation."""

from datetime import UTC, datetime

from supplygraph.domain.models import Dataset, Edge, Inventory, Node


def truth_dataset():
    def meta(rid):
        return dict(id=rid, source_id="golden-v1", ingested_at=datetime(2026, 1, 1, tzinfo=UTC))

    nodes = [
        Node(**meta(nid), kind=kind, name=name, daily_demand=demand, unit_value=value)
        for nid, kind, name, demand, value in [
            ("SUP-A", "supplier", "Primary source", 0, 0),
            ("SUP-B", "supplier", "Backup source", 0, 0),
            ("PORT-A", "port", "Golden port", 0, 0),
            ("RTE-A", "route", "Golden lane", 0, 0),
            ("FAC-A", "facility", "Assembly facility", 0, 0),
            ("CMP-A", "component", "Single sourced part", 0, 0),
            ("CMP-B", "component", "Dual sourced part", 0, 0),
            ("PRD-A", "product", "At risk product", 10, 100),
            ("PRD-B", "product", "Resilient product", 5, 200),
            ("CUS-A", "customer", "Golden customer", 0, 0),
        ]
    ]
    edges = []

    def link(source, target, group, lead=0, capacity=1, approved=True):
        edges.append(
            Edge(
                **meta(f"E-{len(edges) + 1}"),
                source=source,
                target=target,
                kind="supply",
                group=group,
                lead_time_days=lead,
                capacity=capacity,
                approved=approved,
            )
        )

    link("SUP-A", "CMP-A", "part", 1)
    link("SUP-B", "CMP-A", "part", 1, 0.5)  # insufficient capacity; not a valid alternate
    link("SUP-A", "CMP-B", "part")
    link("SUP-B", "CMP-B", "part")
    link("CMP-A", "PRD-A", "bom-a")
    link("CMP-B", "PRD-A", "bom-b")
    link("FAC-A", "PRD-A", "assembly")
    link("CMP-B", "PRD-B", "bom")
    link("FAC-A", "PRD-B", "assembly")
    link("PRD-A", "CUS-A", "order-a")
    link("PRD-B", "CUS-A", "order-b")
    link("PORT-A", "RTE-A", "port", 1)
    link("RTE-A", "FAC-A", "transport", 1)
    return Dataset(
        snapshot_id="GOLDEN",
        source_id="golden-v1",
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        nodes=nodes,
        edges=edges,
        inventories=[
            Inventory(**meta("INV-A"), node_id="CMP-A", facility_id="FAC-A", on_hand=20, daily_usage=10)
        ],
    )


# Manually derived expectation: SUP-A stops at t0; CMP-A has one day in transit + 2 days stock;
# CMP-B survives via SUP-B. PRD-A and CUS-A stop at t3. PRD-A loses (7-3)*10=40 units.
IMPACT_CASES = [
    {"roots": ["SUP-A"], "days": 7, "affected": ["SUP-A", "CMP-A", "PRD-A", "CUS-A"], "units": 40},
    {"roots": ["SUP-A"], "days": 3, "affected": ["SUP-A"], "units": 0},
    {"roots": ["FAC-A"], "days": 7, "affected": ["FAC-A", "PRD-A", "PRD-B", "CUS-A"], "units": 105},
    {
        "roots": ["PORT-A"],
        "days": 7,
        "affected": ["PORT-A", "RTE-A", "FAC-A", "PRD-A", "PRD-B", "CUS-A"],
        "units": 75,
    },
    {"roots": ["RTE-A"], "days": 7, "affected": ["RTE-A", "FAC-A", "PRD-A", "PRD-B", "CUS-A"], "units": 90},
    {"roots": ["CMP-B"], "days": 7, "affected": ["CMP-B", "PRD-A", "PRD-B", "CUS-A"], "units": 105},
    {
        "roots": ["SUP-A", "SUP-B"],
        "days": 7,
        "affected": ["SUP-A", "SUP-B", "CMP-A", "CMP-B", "PRD-A", "PRD-B", "CUS-A"],
        "units": 105,
    },
]
QUERY_CASES = [
    ("Impact of SUP-A for 7 days", "impact", "SUP-A", None),
    ("What is the outage impact at Primary source for 7 days?", "impact", "SUP-A", None),
    ("Upstream suppliers of PRD-A", "upstream", "PRD-A", None),
    ("Downstream dependents of PORT-A", "downstream", "PORT-A", None),
    ("Path from SUP-A to PRD-A", "path", "SUP-A", "PRD-A"),
    ("Path from PRD-A to SUP-A", "path", "PRD-A", "SUP-A"),
    ("Which nodes have critical centrality?", "critical", None, None),
    ("Impact of missing SUP-Z", None, None, None),
    ("Who will win the election?", None, None, None),
    ("Impact of SUP-A-9999", None, None, None),
]
