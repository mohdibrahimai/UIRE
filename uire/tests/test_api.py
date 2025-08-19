"""Basic API tests for UIRE.

These tests exercise the main endpoints of the UIRE API to ensure
that detection, clarification, resolution, answering, memory and
consent all operate as expected.  They also check that the bench
endpoint returns sensible values.
"""
from fastapi.testclient import TestClient
from uire.api.main import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"

def test_detect_clarify_resolve_answer_flow():
    q = "Find me the best bank account"
    # detect
    res = client.post("/v1/detect", json={"query": q}).json()
    assert "factors" in res
    assert res["ambiguous"] is True
    # clarify
    clar = client.post("/v1/clarify", json={"query": q, "factors": res["factors"]}).json()
    # ensure at most 2 questions
    assert len(clar["questions"]) <= 2
    # build answers using defaults
    answers = {}
    for i, qd in enumerate(clar["questions"], start=1):
        answers[f"q{i}"] = qd.get("default")
    # resolve
    resolved = client.post("/v1/resolve", json={"query": q, "answers": answers}).json()
    assert "final_prompt" in resolved
    # answer (same output shape)
    ans = client.post("/v1/answer", json={"query": q, "answers": answers}).json()
    assert "final_prompt" in ans

def test_memory_and_consent():
    # set a preference
    client.post("/v1/memory", json={"prefs": {"region": "US"}})
    mem = client.get("/v1/memory").json()
    assert mem["prefs"].get("region") == "US"
    # clear
    client.delete("/v1/memory")
    mem2 = client.get("/v1/memory").json()
    assert mem2["prefs"] == {}
    # consent
    client.post("/v1/consent", json={"accepted": True})
    cons = client.get("/v1/consent").json()
    assert cons["accepted"] is True

def test_bench():
    bench = client.get("/v1/bench").json()
    assert "total" in bench and "flagged" in bench and "flag_rate" in bench

def test_stats_and_metrics():
    stats = client.get("/v1/stats").json()
    assert "requests_total" in stats
    metrics_text = client.get("/metrics").text
    assert "uire_requests_total" in metrics_text