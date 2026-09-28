"""Reproducible synthetic electronics network. No external or real company data."""

import argparse
import json
import random
from datetime import UTC, datetime
from pathlib import Path

from supplygraph.domain.models import Dataset, Edge, Inventory, Node

STAMP = datetime(2026, 9, 1, tzinfo=UTC)
REGIONS = [
    ("Taiwan", 25.03, 121.56),
    ("Japan", 35.68, 139.69),
    ("South Korea", 37.57, 126.98),
    ("Germany", 50.11, 8.68),
    ("United States", 37.77, -122.42),
    ("Mexico", 25.69, -100.32),
    ("Vietnam", 10.82, 106.63),
    ("Singapore", 1.35, 103.82),
    ("China", 31.23, 121.47),
    ("Netherlands", 51.92, 4.48),
    ("India", 19.08, 72.88),
    ("Malaysia", 5.41, 100.33),
]
PREFIXES = ["Aster", "Koyo", "Helix", "Nord", "Vector", "Meridian", "Atlas", "Vela", "Nexus", "Orion"]
PARTS = [
    "Power management IC",
    "Precision bearing",
    "Control module",
    "Copper winding",
    "Optical sensor",
    "Ceramic capacitor",
    "Thermal assembly",
    "Signal processor",
]
PRODUCTS = ["Drive controller", "Industrial gateway", "Motion platform", "Sensor array", "Power inverter"]


def generate(seed: int = 42, scale: int = 1, snapshot_id: str = "DEMO-2026-09-01") -> Dataset:
    rng = random.Random(seed)
    source = f"synthetic-v1-seed-{seed}"

    def meta(rid):
        return dict(id=rid, source_id=source, ingested_at=STAMP, lineage={"generator": "1.0", "seed": seed})

    nodes, edges, inventories = [], [], []
    counts = {
        "supplier": 200 * scale,
        "component": 800 * scale,
        "product": 80 * scale,
        "facility": 25 * scale,
        "site": 40 * scale,
        "port": 8,
        "route": 24 * scale,
        "customer": 30 * scale,
    }
    prefixes = {
        "supplier": "SUP",
        "component": "CMP",
        "product": "PRD",
        "facility": "FAC",
        "site": "SITE",
        "port": "PORT",
        "route": "RTE",
        "customer": "CUS",
    }
    for kind, count in counts.items():
        for i in range(count):
            country, lat, lon = REGIONS[i % len(REGIONS)]
            rid = f"{prefixes[kind]}-{i + 1:04d}"
            tier = (3 if i < count // 4 else 2 if i < count * 3 // 5 else 1) if kind == "supplier" else 0
            name = f"{PREFIXES[i % 10]} {['Materials', 'Electronics', 'Precision'][i % 3]} {i + 1:03d}"
            if kind == "component":
                name = f"{PARTS[i % 8]} · {i + 1:04d}"
            elif kind == "product":
                name = f"{PRODUCTS[i % 5]} {chr(65 + i % 10)}{100 + i}"
            elif kind not in {"supplier"}:
                name = f"{country} {kind.title()} {i + 1:02d}"
            if kind == "port":
                country, lat, lon, name = [
                    ("Taiwan", 22.61, 120.30, "Port of Kaohsiung"),
                    ("Japan", 35.44, 139.64, "Port of Yokohama"),
                    ("South Korea", 35.10, 129.04, "Port of Busan"),
                    ("Netherlands", 51.92, 4.48, "Port of Rotterdam"),
                    ("United States", 33.73, -118.27, "Port of Los Angeles"),
                    ("Mexico", 19.05, -104.32, "Port of Manzanillo"),
                    ("Vietnam", 10.78, 106.72, "Port of Ho Chi Minh City"),
                    ("Singapore", 1.26, 103.84, "Port of Singapore"),
                ][i]
            nodes.append(
                Node(
                    **meta(rid),
                    kind=kind,
                    name=name,
                    country=country,
                    tier=tier,
                    latitude=lat + rng.uniform(-0.5, 0.5),
                    longitude=lon + rng.uniform(-0.5, 0.5),
                    daily_demand=rng.randint(20, 120) if kind == "product" else 0,
                    unit_value=rng.randint(100, 900) if kind == "product" else 0,
                )
            )

    def edge(source_id, target, kind, group, lead=0.0, approved=True, capacity=1.0, quantity=1.0):
        edges.append(
            Edge(
                **meta(f"EDG-{len(edges) + 1:06d}"),
                source=source_id,
                target=target,
                kind=kind,
                group=group,
                lead_time_days=lead,
                approved=approved,
                capacity=capacity,
                quantity=quantity,
            )
        )

    ns = counts["supplier"]
    for i in range(ns // 4, ns):
        upstream = rng.randrange(ns // 4) if i < ns * 3 // 5 else rng.randrange(ns // 4, ns * 3 // 5)
        edge(f"SUP-{upstream + 1:04d}", f"SUP-{i + 1:04d}", "tier", "raw-input", 0.5)
        if i % 9 == 0:
            edge(f"SUP-{(upstream + 1) % (ns // 4) + 1:04d}", f"SUP-{i + 1:04d}", "tier", "raw-input", 0.5)
    for i in range(counts["route"]):
        edge(f"PORT-{i % 8 + 1:04d}", f"RTE-{i + 1:04d}", "transport", "port", 0.5)
    for i in range(counts["site"]):
        edge(
            f"SUP-{ns * 3 // 5 + i % (ns - ns * 3 // 5) + 1:04d}",
            f"SITE-{i + 1:04d}",
            "supply",
            "supplier",
            0.5,
        )
        edge(f"RTE-{i % counts['route'] + 1:04d}", f"SITE-{i + 1:04d}", "transport", "inbound", 0.5)
        if i % 5 == 0:
            edge(f"RTE-{(i + 1) % counts['route'] + 1:04d}", f"SITE-{i + 1:04d}", "transport", "inbound", 0.5)
    for i in range(counts["component"]):
        cid = f"CMP-{i + 1:04d}"
        edge(f"SITE-{i % counts['site'] + 1:04d}", cid, "supply", "source", 0.5)
        if i % 7 == 0:
            # Capacity-inadequate and unapproved alternatives deliberately remain visible in raw graph.
            edge(
                f"SITE-{(i + 1) % counts['site'] + 1:04d}",
                cid,
                "supply",
                "source",
                0.5,
                approved=i % 21 != 0,
                capacity=0.4 if i % 14 == 0 else 1,
            )
        usage = rng.randint(15, 90)
        inventories.append(
            Inventory(
                **meta(f"INV-{i + 1:05d}"),
                node_id=cid,
                facility_id=f"FAC-{i % counts['facility'] + 1:04d}",
                daily_usage=usage,
                on_hand=usage * rng.choice([0, 1, 2, 3, 5, 8]),
            )
        )
    for i in range(counts["product"]):
        pid = f"PRD-{i + 1:04d}"
        for j in range(5):
            component = (i * 7 + j * 13) % counts["component"] + 1
            edge(f"CMP-{component:04d}", pid, "bom", f"part-{j}", quantity=j % 3 + 1)
        edge(f"FAC-{i % counts['facility'] + 1:04d}", pid, "manufacture", "assembly")
        edge(pid, f"CUS-{i % counts['customer'] + 1:04d}", "demand", f"order-{pid}")
    # Reconcile represented BOM requirements plus explicit synthetic service/spares demand.
    by_id = {node.id: node for node in nodes}
    gross = {}
    for relation in edges:
        if relation.kind == "bom":
            gross[relation.source] = (
                gross.get(relation.source, 0) + by_id[relation.target].daily_demand * relation.quantity
            )
    for inv in inventories:
        coverage = inv.on_hand / inv.daily_usage
        service_usage = inv.daily_usage
        inv.daily_usage += gross.get(inv.node_id, 0)
        inv.on_hand = inv.daily_usage * coverage
        inv.lineage["service_daily_usage"] = service_usage
        inv.lineage["bom_daily_usage"] = gross.get(inv.node_id, 0)
    inventories[-1].daily_usage = 0  # Deliberate unknown-use stock warning on a non-BOM spare part.
    inventories[-1].lineage["anomaly"] = "unknown usage; buffer excluded"
    return Dataset(
        snapshot_id=snapshot_id,
        source_id=source,
        effective_at=STAMP,
        seed=seed,
        nodes=nodes,
        edges=edges,
        inventories=inventories,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("data/sample/demo.json"))
    args = parser.parse_args()
    if not 1 <= args.scale <= 150:
        parser.error("scale must be 1..150")
    data = generate(args.seed, args.scale)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data.model_dump(mode="json"), separators=(",", ":")))
    print(
        json.dumps(
            {"file": str(args.output), "nodes": len(data.nodes), "edges": len(data.edges), "seed": args.seed}
        )
    )


if __name__ == "__main__":
    main()
