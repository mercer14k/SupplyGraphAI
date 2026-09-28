import os

import pytest
from fastapi.testclient import TestClient

from supplygraph.api import create_app
from supplygraph.data.validation import canonical_bytes


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(f"sqlite:///{tmp_path}/test.db", bootstrap=False, write_token="test-token")
    ) as c:
        yield c


def upload(client, dataset, key="test", token="test-token", filename="demo.json", mime="application/json"):
    return client.post(
        "/api/v1/ingestions",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": key},
        files={"file": (filename, canonical_bytes(dataset), mime)},
    )


def test_end_to_end_import_scenario_evidence_query_export(client, dataset):
    response = upload(client, dataset)
    assert response.status_code == 200 and response.json()["created"]
    assert client.get("/ready").status_code == 200
    assert client.get("/api/v1/snapshots").json()[0]["id"] == "GOLDEN"
    scenario = client.post(
        "/api/v1/analysis/scenarios",
        json={"snapshot_id": "GOLDEN", "disrupted_ids": ["SUP-A"], "duration_days": 7},
    )
    assert scenario.json()["lost_product_units"] == 40
    for eid in scenario.json()["evidence_ids"]:
        assert client.get(f"/api/v1/evidence/{eid}", params={"snapshot_id": "GOLDEN"}).status_code == 200
    result = client.post(
        "/api/v1/analysis/query", json={"snapshot_id": "GOLDEN", "question": "Impact of SUP-A for 7 days"}
    ).json()
    assert result["status"] == "answered"
    assert client.get("/api/v1/snapshots/GOLDEN/export").content == canonical_bytes(dataset)
    assert (
        client.get("/api/v1/nodes", params={"snapshot_id": "GOLDEN", "limit": 2, "offset": 2}).json()["total"]
        == 10
    )
    assert scenario.headers["X-Trace-ID"]
    assert "/api/v1/ingestions" in client.get("/openapi.json").json()["paths"]


def test_idempotency_and_snapshot_immutability(client, dataset):
    assert upload(client, dataset).json()["created"]
    assert not upload(client, dataset).json()["created"]
    dataset.nodes[0].name = "Changed"
    assert upload(client, dataset).status_code == 409
    assert upload(client, dataset, key="new").status_code == 409
    assert (
        client.get("/api/v1/evidence/SUP-A", params={"snapshot_id": "GOLDEN"}).json()["name"]
        == "Primary source"
    )
    dataset.snapshot_id = "GOLDEN-2"
    assert upload(client, dataset, key="new2").status_code == 200
    assert len(client.get("/api/v1/snapshots").json()) == 2


def test_invalid_is_atomic_and_visible(client, dataset):
    dataset.edges[0].source = "MISSING"
    result = upload(client, dataset)
    assert result.status_code == 422
    assert result.json()["error"]["details"]["errors"][0]["code"] == "dangling_edge"
    assert client.get("/api/v1/snapshots").json() == []
    assert not client.get("/api/v1/validation-reports").json()[0]["valid"]


def test_authorization_mime_and_schema(client, dataset):
    assert upload(client, dataset, token="wrong").status_code == 401
    assert upload(client, dataset, mime="text/html").status_code == 415
    assert upload(client, dataset, filename="payload.exe").status_code == 415
    assert (
        client.post(
            "/api/v1/analysis/scenarios", json={"snapshot_id": "GOLDEN", "disrupted_ids": []}
        ).status_code
        == 422
    )
    assert client.get("/api/v1/nodes", params={"snapshot_id": "MISSING"}).status_code == 404
    response = client.get("/api/v1/nodes", params={"snapshot_id": "GOLDEN", "limit": 10000})
    assert response.status_code == 422 and "error" in response.json()
    assert client.get("/not-found").json()["error"]["code"] == "http_404"


def test_upload_size_limit(client):
    response = client.post(
        "/api/v1/ingestions",
        headers={"Authorization": "Bearer test-token", "Idempotency-Key": "large"},
        files={"file": ("large.json", b" " * (25 * 1024 * 1024 + 1), "application/json")},
    )
    assert response.status_code == 413


def test_llm_disabled_does_not_affect_state(client, dataset):
    upload(client, dataset)
    before = client.get("/api/v1/snapshots/GOLDEN/export").content
    response = client.post(
        "/api/v1/analysis/query",
        json={"snapshot_id": "GOLDEN", "question": "Impact of SUP-A", "use_llm": True},
    )
    assert response.json()["status"] == "abstained"
    assert client.get("/api/v1/snapshots/GOLDEN/export").content == before


@pytest.mark.postgres
@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="PostgreSQL integration requires TEST_DATABASE_URL"
)
def test_postgres_roundtrip(dataset):
    with TestClient(
        create_app(os.environ["TEST_DATABASE_URL"], bootstrap=False, write_token="test-token")
    ) as client:
        dataset.snapshot_id = "POSTGRES-TEST"
        assert upload(client, dataset, key="pg-test").status_code == 200
        assert (
            client.get("/api/v1/overview", params={"snapshot_id": dataset.snapshot_id}).json()["nodes"] == 10
        )


def test_offline_documentation_and_trace(client):
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "/docs-assets/swagger-ui-bundle.js" in docs.text
    assert "cdn.jsdelivr" not in docs.text
    assert client.get("/docs-assets/swagger-ui-bundle.js").status_code == 200
    assert client.get("/health").headers.get("X-Trace-ID")


def test_default_write_boundary(tmp_path, dataset):
    with TestClient(create_app(f"sqlite:///{tmp_path}/readonly.db", bootstrap=False, write_token="")) as c:
        assert upload(c, dataset).status_code == 403


def test_snapshot_export_round_trip_is_idempotent(client, dataset):
    upload(client, dataset)
    exported = client.get("/api/v1/snapshots/GOLDEN/export").content
    response = client.post(
        "/api/v1/ingestions",
        headers={"Authorization": "Bearer test-token", "Idempotency-Key": "export-roundtrip"},
        files={"file": ("export.json", exported, "application/json")},
    )
    assert response.status_code == 200 and not response.json()["created"]
