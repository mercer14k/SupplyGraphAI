"""Verify a real Compose stack; caller owns teardown and its persistent volumes."""

import json
import urllib.request

base = "http://127.0.0.1:8041"
with urllib.request.urlopen(base + "/ready") as response:
    assert response.status == 200
with urllib.request.urlopen(base + "/api/v1/snapshots") as response:
    snapshots = json.load(response)
payload = {"snapshot_id": snapshots[0]["id"], "disrupted_ids": ["PORT-0001"], "duration_days": 14}
request = urllib.request.Request(
    base + "/api/v1/analysis/scenarios",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request) as response:
    scenario = json.load(response)
assert scenario["affected_products"] > 0 and scenario["evidence_ids"]
with urllib.request.urlopen("http://127.0.0.1:8080") as response:
    assert "SupplyGraph" in response.read().decode()
print(
    json.dumps(
        {
            "ready": True,
            "affected_products": scenario["affected_products"],
            "evidence_count": len(scenario["evidence_ids"]),
        }
    )
)
