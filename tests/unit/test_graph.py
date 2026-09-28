import pytest

from supplygraph.domain.graph import SupplyGraph
from supplygraph.domain.models import ScenarioRequest
from supplygraph.evaluation.fixtures import IMPACT_CASES


@pytest.mark.parametrize("case", IMPACT_CASES)
def test_hand_audited_impact(dataset, case):
    graph = SupplyGraph(dataset)
    result = graph.simulate(
        ScenarioRequest(snapshot_id="GOLDEN", disrupted_ids=case["roots"], duration_days=case["days"])
    )
    assert {i.node_id for i in result.impacts} == set(case["affected"])
    assert result.lost_product_units == case["units"]
    assert set(result.evidence_ids) <= graph.evidence.keys()


def test_inventory_and_alternate_proof(dataset):
    graph = SupplyGraph(dataset)
    result = graph.simulate(ScenarioRequest(snapshot_id="GOLDEN", disrupted_ids=["SUP-A"], duration_days=7))
    product = next(i for i in result.impacts if i.node_id == "PRD-A")
    assert product.shortage_day == 3
    assert product.exposure_value == 4000
    assert product.path == ["SUP-A", "CMP-A", "PRD-A"]
    assert "INV-A" in product.evidence_ids
    assert [(a.source_id, a.target_id) for a in result.alternates] == [("SUP-B", "CMP-B")]


def test_unapproved_alternate_is_not_usable(dataset):
    dataset.edges[3].approved = False
    result = SupplyGraph(dataset).simulate(
        ScenarioRequest(snapshot_id="GOLDEN", disrupted_ids=["SUP-A"], duration_days=7)
    )
    assert result.affected_products == 2
    assert result.lost_product_units == 105


def test_direct_outage_bypasses_own_stock(dataset):
    result = SupplyGraph(dataset).simulate(
        ScenarioRequest(snapshot_id="GOLDEN", disrupted_ids=["CMP-A"], duration_days=7)
    )
    assert next(i for i in result.impacts if i.node_id == "CMP-A").shortage_day == 0


def test_wrong_snapshot_and_missing_nodes(dataset):
    graph = SupplyGraph(dataset)
    with pytest.raises(ValueError):
        graph.simulate(ScenarioRequest(snapshot_id="OTHER", disrupted_ids=["SUP-A"]))
    with pytest.raises(KeyError):
        graph.simulate(ScenarioRequest(snapshot_id="GOLDEN", disrupted_ids=["UNKNOWN"]))
    assert graph.path("PRD-A", "SUP-A") == []


def test_critical_fixed_seed(dataset):
    assert SupplyGraph(dataset).critical() == SupplyGraph(dataset).critical()


def test_zero_usage_not_infinite_stock(dataset):
    dataset.inventories[0].daily_usage = 0
    result = SupplyGraph(dataset).simulate(
        ScenarioRequest(snapshot_id="GOLDEN", disrupted_ids=["SUP-A"], duration_days=7)
    )
    assert next(i for i in result.impacts if i.node_id == "CMP-A").shortage_day == 1
