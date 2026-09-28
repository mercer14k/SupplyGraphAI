import httpx
import pytest

from supplygraph.ai.runtime import LocalPlanner


@pytest.mark.parametrize("runtime", ["ollama", "llamacpp"])
def test_local_runtime_structured_contract(monkeypatch, runtime):
    client_type = httpx.Client
    calls = []

    def handle(request):
        calls.append(request)
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "test-local-v1"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "test-model", "digest": "sha256:test"}]})
        content = '{"operation":"impact","node_id":"SUP-A","duration_days":7}'
        if runtime == "ollama":
            return httpx.Response(
                200, json={"message": {"content": content}, "model": "test-model", "eval_count": 20}
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}}],
                "model": "test-model",
                "usage": {"completion_tokens": 20},
            },
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: client_type(transport=httpx.MockTransport(handle), **kwargs)
    )
    planner = LocalPlanner("http://127.0.0.1:11434", "test-model", runtime)
    plan, telemetry = planner.plan("Impact of SUP-A for 7 days", [{"id": "SUP-A", "name": "Primary"}])
    assert plan.operation == "impact" and plan.node_id == "SUP-A"
    assert telemetry["runtime_model"] == "test-model"
    assert all(request.url.host == "127.0.0.1" for request in calls)
    assert b"format" in calls[-1].content if runtime == "ollama" else b"response_format" in calls[-1].content
