"""Tests for NASA POWER API service."""

from datetime import date

import httpx
import pytest
import respx

from app.services.nasa import NASAPowerService


@pytest.fixture
def nasa_service():
    """Create a NASA POWER service instance."""
    return NASAPowerService(timeout=5.0)


class TestNASAPowerService:
    """Tests for NASAPowerService."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_weather_data_success(self, nasa_service, mock_nasa_wind_response, mock_nasa_solar_response):
        """Successful fetch returns combined data."""
        respx.get("https://power.larc.nasa.gov/api/temporal/daily/point").mock(
            side_effect=[
                httpx.Response(200, json=mock_nasa_wind_response),
                httpx.Response(200, json=mock_nasa_solar_response),
            ]
        )

        result = await nasa_service.fetch_weather_data(
            latitude=4.6097,
            longitude=-74.0817,
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
        )

        assert "properties" in result
        assert "WS2M" in result["properties"]["parameter"]
        assert "WD2M" in result["properties"]["parameter"]
        assert "ALLSKY_SFC_SW_DWN" in result["properties"]["parameter"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_weather_data_wind_error(self, nasa_service):
        """NASA wind API error returns 502."""
        respx.get("https://power.larc.nasa.gov/api/temporal/daily/point").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await nasa_service.fetch_weather_data(
                latitude=4.6097,
                longitude=-74.0817,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )
        assert exc_info.value.status_code == 502

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_weather_data_solar_error(self, nasa_service, mock_nasa_wind_response):
        """NASA solar API error returns 502."""
        respx.get("https://power.larc.nasa.gov/api/temporal/daily/point").mock(
            side_effect=[
                httpx.Response(200, json=mock_nasa_wind_response),
                httpx.Response(502, text="Bad Gateway"),
            ]
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await nasa_service.fetch_weather_data(
                latitude=4.6097,
                longitude=-74.0817,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )
        assert exc_info.value.status_code == 502

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_weather_data_timeout(self, nasa_service):
        """NASA API timeout returns 504."""
        respx.get("https://power.larc.nasa.gov/api/temporal/daily/point").mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await nasa_service.fetch_weather_data(
                latitude=4.6097,
                longitude=-74.0817,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )
        assert exc_info.value.status_code == 504

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_weather_data_connection_error(self, nasa_service):
        """NASA connection error returns 502."""
        respx.get("https://power.larc.nasa.gov/api/temporal/daily/point").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await nasa_service.fetch_weather_data(
                latitude=4.6097,
                longitude=-74.0817,
                start=date(2024, 1, 1),
                end=date(2024, 1, 31),
            )
        assert exc_info.value.status_code == 502

    @respx.mock
    @pytest.mark.asyncio
    async def test_url_construction(self, nasa_service, mock_nasa_wind_response, mock_nasa_solar_response):
        """URL is constructed with correct parameters."""
        route = respx.get("https://power.larc.nasa.gov/api/temporal/daily/point").mock(
            side_effect=[
                httpx.Response(200, json=mock_nasa_wind_response),
                httpx.Response(200, json=mock_nasa_solar_response),
            ]
        )

        await nasa_service.fetch_weather_data(
            latitude=4.6097,
            longitude=-74.0817,
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
        )

        # Verify both requests were made
        assert route.call_count == 2
        # Check wind request URL
        wind_request = route.calls[0].request
        assert "WS2M,WD2M" in str(wind_request.url)
        assert "latitude=4.6097" in str(wind_request.url)
        assert "longitude=-74.0817" in str(wind_request.url)
        assert "start=20240101" in str(wind_request.url)
        assert "end=20240131" in str(wind_request.url)
        # Check solar request URL
        solar_request = route.calls[1].request
        assert "ALLSKY_SFC_SW_DWN" in str(solar_request.url)
