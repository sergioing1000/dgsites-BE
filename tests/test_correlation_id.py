"""Tests for the correlation-ID middleware."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


class TestCorrelationID:
    """Validate X-Request-ID propagation and generation."""

    def test_generates_id_when_absent(self, client: TestClient) -> None:
        """Middleware must generate a UUID when no X-Request-ID is sent."""
        response = client.get("/health")
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None
        # Must be a valid UUID4
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    def test_propagates_provided_id(self, client: TestClient) -> None:
        """Middleware must echo back a client-supplied X-Request-ID."""
        provided = str(uuid.uuid4())
        response = client.get("/health", headers={"X-Request-ID": provided})
        assert response.headers.get("X-Request-ID") == provided

    def test_different_requests_get_different_ids(self, client: TestClient) -> None:
        """Two requests without X-Request-ID must produce distinct IDs."""
        id1 = client.get("/health").headers.get("X-Request-ID")
        id2 = client.get("/health").headers.get("X-Request-ID")
        assert id1 != id2

    def test_id_on_weather_endpoint(self, client: TestClient) -> None:
        """Correlation ID must be present on non-health endpoints too."""
        response = client.post(
            "/api/v1/weather-data",
            json={
                "station_name": "Test",
                "latitude": 4.6,
                "longitude": -74.0,
                "start": "2024-01-01",
                "end": "2024-01-05",
            },
        )
        # Even if the endpoint returns 422/502, middleware still sets the header.
        assert "X-Request-ID" in response.headers

    def test_id_is_valid_uuid_format(self, client: TestClient) -> None:
        """Generated ID must be a valid UUID string."""
        response = client.get("/health")
        request_id = response.headers["X-Request-ID"]
        parsed = uuid.UUID(request_id)
        assert str(parsed) == request_id

    def test_preserves_existing_id_on_error(self, client: TestClient) -> None:
        """Provided ID must be returned even when the route errors."""
        provided = "test-correlation-123"
        response = client.post(
            "/api/v1/weather-data",
            json={},  # Invalid payload → 422
            headers={"X-Request-ID": provided},
        )
        assert response.headers.get("X-Request-ID") == provided
