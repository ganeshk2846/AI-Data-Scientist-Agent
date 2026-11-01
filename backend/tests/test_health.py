"""
Tests for health, ready, and system status endpoints.
"""

def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert "version" in body["data"]
    assert "request_id" in body
    assert res.headers.get("X-Request-ID") == body["request_id"]
    assert "X-Process-Time-Ms" in res.headers


def test_api_v1_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_ready_endpoint(client):
    res = client.get("/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["ready"] is True
    assert data["database"]["connected"] is True
    assert data["database"]["read_only_verified"] is True
    assert data["database"]["table_count"] == 30
    assert data["database"]["total_rows"] == 334503


def test_system_status_endpoint(client):
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["app"]["version"] == "0.1.0"
    assert data["database"]["connected"] is True
    assert data["limits"]["sql_query_timeout_seconds"] == 30

