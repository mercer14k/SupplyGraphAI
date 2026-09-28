import json
from collections import Counter

import pytest

from supplygraph.data.generator import generate
from supplygraph.data.validation import canonical_bytes, validate_bytes


def test_generator_reproducible():
    first, second = generate(42), generate(42)
    assert canonical_bytes(first) == canonical_bytes(second)
    assert canonical_bytes(first) != canonical_bytes(generate(43))
    counts = Counter(n.kind for n in first.nodes)
    assert counts["supplier"] == 200 and counts["component"] == 800
    assert counts["product"] == 80 and counts["facility"] == 25
    assert validate_bytes(canonical_bytes(first))[1].valid


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda d: d["nodes"].append(d["nodes"][0]), "duplicate_id"),
        (lambda d: d["edges"][0].update(source="MISSING"), "dangling_edge"),
        (lambda d: d["edges"][0].update(source="CMP-A"), "self_dependency"),
        (lambda d: d["edges"][0].update(source="PRD-A"), "dependency_cycle"),
        (lambda d: d["inventories"][0].update(on_hand=-1), "greater_than_equal"),
        (lambda d: d["inventories"][0].update(facility_id="SUP-A"), "invalid_facility"),
        (lambda d: d["inventories"][0].update(node_id="MISSING"), "orphan_inventory"),
        (lambda d: d["edges"][0].update(approved=False), "uncovered_group"),
        (lambda d: d["nodes"][0].update(unit_value=float("nan")), "finite_number"),
        (lambda d: d["nodes"][0].update(ingested_at="2026-01-01T00:00:00"), "timezone_required"),
        (lambda d: d["edges"][1].update(quantity=2), "inconsistent_group"),
        (lambda d: d["inventories"].append(d["inventories"][0] | {"id": "INV-B"}), "ambiguous_stock"),
    ],
)
def test_rejected_with_visible_error(dataset, mutation, code):
    payload = dataset.model_dump(mode="json")
    mutation(payload)
    result, report = validate_bytes(json.dumps(payload).encode(), "../../private.json")
    assert result is None
    assert code in {e.code for e in report.errors}
    assert report.filename == "private.json"


def test_malformed_json_and_extra_fields(dataset):
    assert not validate_bytes(b"{broken")[1].valid
    payload = dataset.model_dump(mode="json") | {"execute": "rm -rf /"}
    assert not validate_bytes(json.dumps(payload).encode())[1].valid


def test_zero_usage_warning(dataset):
    dataset.inventories[0].daily_usage = 0
    report = validate_bytes(canonical_bytes(dataset))[1]
    assert report.valid and report.warnings[0].code == "zero_usage"
