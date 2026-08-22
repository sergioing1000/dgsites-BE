import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_wind_request():
    """Return a valid wind data request payload."""
    return {
        "station_name": "Test Station",
        "latitude": 4.6097,
        "longitude": -74.0817,
        "start": "2024-01-01",
        "end": "2024-01-31"
    }


@pytest.fixture
def invalid_wind_request():
    """Return an invalid wind data request payload (missing required fields)."""
    return {
        "station_name": "Test Station"
    }
