"""Tests for the GET /health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Validate /health response contract and stability."""

    def test_returns_200(self, client: TestClient) -> None:
        """Health endpoint must return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_healthy(self, client: TestClient) -> None:
        """Response body must contain status=healthy."""
        data = client.get("/health").json()
        assert data["status"] == "healthy"

    def test_version_present(self, client: TestClient) -> None:
        """Response body must include a non-empty version string."""
        data = client.get("/health").json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_environment_present(self, client: TestClient) -> None:
        """Response body must include an environment string."""
        data = client.get("/health").json()
        assert "environment" in data
        assert isinstance(data["environment"], str)

    def test_response_shape_is_stable(self, client: TestClient) -> None:
        """Response must contain exactly status, version, environment."""
        data = client.get("/health").json()
        assert set(data.keys()) == {"status", "version", "environment"}

    def test_version_from_env(self, client: TestClient, monkeypatch: object) -> None:
        """APP_VERSION env var overrides default version."""
        import pytest

        mp = pytest.MonkeyPatch()
        mp.setenv("APP_VERSION", "2.3.4")
        try:
            # Need fresh import to pick up env change at module level
            from importlib import reload

            import app.routers.health as health_mod

            reload(health_mod)

            response = client.get("/health")
            data = response.json()
            assert data["version"] == "2.3.4"
        finally:
            mp.undo()

    def test_no_sensitive_data(self, client: TestClient) -> None:
        """Response must not expose secrets, tokens, or internal paths."""
        data = client.get("/health").json()
        text = str(data).lower()
        assert "password" not in text
        assert "secret" not in text
        assert "token" not in text
        assert "/home" not in text
