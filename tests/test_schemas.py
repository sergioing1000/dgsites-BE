"""Tests for Pydantic request/response schemas."""

from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.weather import (
    DailyData,
    Metadata,
    MonthlySummary,
    WeatherDataRequest,
    WeatherDataResponse,
)


class TestWeatherDataRequest:
    """Tests for WeatherDataRequest validation."""

    def test_valid_request(self):
        """Valid request with proper Colombia coordinates."""
        req = WeatherDataRequest(
            station_name="Test Station",
            latitude=4.6097,
            longitude=-74.0817,
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
        )
        assert req.station_name == "Test Station"
        assert req.latitude == 4.6097
        assert req.longitude == -74.0817

    def test_empty_station_name_rejected(self):
        """Station name must be non-empty."""
        with pytest.raises(ValidationError):
            WeatherDataRequest(
                station_name="",
                latitude=4.6097,
                longitude=-74.0817,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

    def test_latitude_out_of_range(self):
        """Latitude outside Colombia bbox is rejected."""
        with pytest.raises(ValidationError):
            WeatherDataRequest(
                station_name="Test",
                latitude=50.0,  # Outside Colombia
                longitude=-74.0817,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

    def test_longitude_out_of_range(self):
        """Longitude outside Colombia bbox is rejected."""
        with pytest.raises(ValidationError):
            WeatherDataRequest(
                station_name="Test",
                latitude=4.6097,
                longitude=-50.0,  # Outside Colombia
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )

    def test_start_after_end_rejected(self):
        """Start date must be before end date."""
        with pytest.raises(ValidationError):
            WeatherDataRequest(
                station_name="Test",
                latitude=4.6097,
                longitude=-74.0817,
                start=date(2024, 1, 31),
                end=date(2024, 1, 1),
            )

    def test_start_equals_end_rejected(self):
        """Start date must be strictly before end date."""
        with pytest.raises(ValidationError):
            WeatherDataRequest(
                station_name="Test",
                latitude=4.6097,
                longitude=-74.0817,
                start=date(2024, 1, 15),
                end=date(2024, 1, 15),
            )

    def test_future_start_date_rejected(self):
        """Start date in the future is rejected."""
        future = datetime.now(tz=timezone.utc).date() + timedelta(days=10)
        with pytest.raises(ValidationError):
            WeatherDataRequest(
                station_name="Test",
                latitude=4.6097,
                longitude=-74.0817,
                start=future,
                end=future + timedelta(days=5),
            )

    def test_future_end_date_rejected(self):
        """End date in the future is rejected."""
        today = datetime.now(tz=timezone.utc).date()
        with pytest.raises(ValidationError):
            WeatherDataRequest(
                station_name="Test",
                latitude=4.6097,
                longitude=-74.0817,
                start=today - timedelta(days=5),
                end=today + timedelta(days=5),
            )

    def test_colombia_bbox_boundaries(self):
        """Coordinates at Colombia bbox boundaries are accepted."""
        req = WeatherDataRequest(
            station_name="Border Station",
            latitude=-4.23,  # Southern boundary
            longitude=-79.09,  # Western boundary
            start=date(2024, 6, 1),
            end=date(2024, 6, 15),
        )
        assert req.latitude == -4.23
        assert req.longitude == -79.09


class TestWeatherDataResponse:
    """Tests for WeatherDataResponse construction."""

    def test_response_construction(self):
        """Response can be constructed with all fields."""
        response = WeatherDataResponse(
            daily_data=[
                DailyData(
                    date="20240101",
                    wind_speed_ms=2.5,
                    wind_direction_deg=180.0,
                    solar_radiation_kwh=4.5,
                )
            ],
            monthly_summary=[
                MonthlySummary(
                    year_month="202401",
                    avg_wind_speed_ms=2.5,
                    avg_wind_direction_deg=180.0,
                    avg_solar_radiation_kwh=4.5,
                )
            ],
            metadata=Metadata(
                station_name="Test",
                latitude=4.6097,
                longitude=-74.0817,
                start_date="2024-01-01",
                end_date="2024-01-31",
                total_days=1,
            ),
        )
        assert len(response.daily_data) == 1
        assert response.metadata.total_days == 1

    def test_response_with_none_values(self):
        """Response handles None values in daily data."""
        response = WeatherDataResponse(
            daily_data=[
                DailyData(
                    date="20240101",
                    wind_speed_ms=None,
                    wind_direction_deg=None,
                    solar_radiation_kwh=None,
                )
            ],
            monthly_summary=[],
            metadata=Metadata(
                station_name="Test",
                latitude=4.6097,
                longitude=-74.0817,
                start_date="2024-01-01",
                end_date="2024-01-01",
                total_days=1,
            ),
        )
        assert response.daily_data[0].wind_speed_ms is None
