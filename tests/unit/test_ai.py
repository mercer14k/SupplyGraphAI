import pytest

from supplygraph.ai.query import answer, parse_question
from supplygraph.ai.runtime import LocalPlanner
from supplygraph.data.validation import canonical_bytes
from supplygraph.domain.graph import SupplyGraph
from supplygraph.domain.models import QueryPlan, QueryRequest
from supplygraph.evaluation.fixtures import QUERY_CASES


@pytest.mark.parametrize("question,operation,node,target", QUERY_CASES)
def test_query_accuracy(dataset, question, operation, node, target):
    graph = SupplyGraph(dataset)
    if operation is None:
        with pytest.raises(ValueError):
            parse_question(graph, question)
    else:
        result = parse_question(graph, question)
        assert (result.operation, result.node_id, result.target_id) == (operation, node, target)


def test_missing_evidence_abstains(dataset):
    graph = SupplyGraph(dataset)
    graph.evidence.pop("INV-A")
    response = answer(graph, QueryRequest(snapshot_id="GOLDEN", question="Impact of SUP-A for 7 days"))
    assert response.status == "abstained" and not response.claims


class FailedPlanner:
    name, model = "test-local", "malformed"

    def plan(self, question, candidates):
        raise RuntimeError("unavailable")


class HallucinatingPlanner:
    name, model = "test-local", "invalid"

    def plan(self, question, candidates):
        return QueryPlan(operation="impact", node_id="SUP-B"), {}


@pytest.mark.parametrize("planner", [None, FailedPlanner(), HallucinatingPlanner()])
def test_llm_failure_cannot_mutate_graph(dataset, planner):
    before = canonical_bytes(dataset)
    response = answer(
        SupplyGraph(dataset),
        QueryRequest(snapshot_id="GOLDEN", question="Impact of SUP-A", use_llm=True),
        planner,
    )
    assert response.status == "abstained"
    assert not response.claims
    assert canonical_bytes(dataset) == before
    if planner:
        assert response.telemetry["validation_failures"] == 2


def test_grounded_claims(dataset):
    response = answer(
        SupplyGraph(dataset), QueryRequest(snapshot_id="GOLDEN", question="Impact of SUP-A for 7 days")
    )
    assert response.status == "answered"
    assert "40.00" in response.claims[0].text
    assert "INV-A" in response.claims[0].evidence_ids


@pytest.mark.parametrize(
    "url",
    ["https://api.example.com", "http://evil.com", "http://user:pass@localhost", "http://localhost.evil.com"],
)
def test_no_remote_runtime(url):
    with pytest.raises(ValueError):
        LocalPlanner(url, "anything")


def test_model_output_no_arbitrary_sql(dataset):
    class SQLPlanner:
        name, model = "test", "test"

        def plan(self, question, candidates):
            return {"operation": "execute_sql", "query": "DROP TABLE nodes"}, {}

    result = answer(
        SupplyGraph(dataset),
        QueryRequest(snapshot_id="GOLDEN", question="Impact of SUP-A", use_llm=True),
        SQLPlanner(),
    )
    assert result.status == "abstained"
