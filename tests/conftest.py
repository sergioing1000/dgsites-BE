"""Shared test fixtures for dgsites-BE test suite."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_request() -> dict:
    """Return a valid weather data request payload."""
    return {
        "station_name": "Bogota Station",
        "latitude": 4.6097,
        "longitude": -74.0817,
        "start": "2024-01-01",
        "end": "2024-01-31",
    }


@pytest.fixture
def mock_nasa_wind_response() -> dict:
    """Return a mock NASA POWER API wind response."""
    dates = [f"202401{d:02d}" for d in range(1, 32)]
    return {
        "type": "Feature",
        "properties": {
            "parameter": {
                "WS2M": {d: 2.5 + (i * 0.1) for i, d in enumerate(dates)},
                "WD2M": {d: 180.0 + (i * 5) for i, d in enumerate(dates)},
            }
        },
    }


@pytest.fixture
def mock_nasa_solar_response() -> dict:
    """Return a mock NASA POWER API solar response."""
    dates = [f"202401{d:02d}" for d in range(1, 32)]
    return {
        "type": "Feature",
        "properties": {
            "parameter": {
                "ALLSKY_SFC_SW_DWN": {d: 4.5 + (i * 0.05) for i, d in enumerate(dates)},
            }
        },
    }


@pytest.fixture
def mock_nasa_combined_response() -> dict:
    """Return a mock combined NASA response (wind + solar merged)."""
    dates = [f"202401{d:02d}" for d in range(1, 32)]
    return {
        "type": "Feature",
        "properties": {
            "parameter": {
                "WS2M": {d: 2.5 + (i * 0.1) for i, d in enumerate(dates)},
                "WD2M": {d: 180.0 + (i * 5) for i, d in enumerate(dates)},
                "ALLSKY_SFC_SW_DWN": {d: 4.5 + (i * 0.05) for i, d in enumerate(dates)},
            }
        },
    }
