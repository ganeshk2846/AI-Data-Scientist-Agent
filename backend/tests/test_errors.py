"""
Tests for structured error responses and exception handlers.
"""

from backend.app.core.errors import AppException, ResourceNotFoundError, ValidationError


def test_custom_exception_serialization(client):
    # Route that triggers a domain error if added, or test via manual client request
    res = client.get("/non-existent-route-xyz")
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "request_id" in body

