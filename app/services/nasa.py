"""Centralized NASA POWER API client with timeout and error handling.

Provides a single service for fetching wind and solar radiation data
from NASA's POWER API, with proper timeout management and HTTP error
code mapping.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx
import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)

NASA_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_TIMEOUT_SECONDS = 30

# Parameters to fetch from NASA POWER API
WIND_PARAMS = "WS2M,WD2M"
SOLAR_PARAMS = "ALLSKY_SFC_SW_DWN"
COMMUNITY = "RE"


class NASAPowerService:
    """Service for interacting with NASA POWER API.

    Handles HTTP communication, timeout management, and error mapping
    for the NASA POWER daily point data endpoint.
    """

    def __init__(self, timeout: float = NASA_TIMEOUT_SECONDS) -> None:
        """Initialize the NASA POWER service.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self._timeout = timeout

    async def fetch_weather_data(
        self,
        latitude: float,
        longitude: float,
        start: date,
        end: date,
    ) -> dict[str, Any]:
        """Fetch wind and solar data from NASA POWER API.

        Makes two parallel requests (wind + solar) and returns combined
        JSON response from the NASA POWER API.

        Args:
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.
            start: Start date for data retrieval.
            end: End date for data retrieval.

        Returns:
            Combined NASA POWER API JSON response dict.

        Raises:
            HTTPException: 502 if NASA returns non-200, 504 on timeout,
                500 on unexpected errors.
        """
        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")

        wind_url = (
            f"{NASA_BASE_URL}"
            f"?parameters={WIND_PARAMS}"
            f"&community={COMMUNITY}"
            f"&latitude={latitude}"
            f"&longitude={longitude}"
            f"&start={start_str}"
            f"&end={end_str}"
            "&format=JSON"
        )

        solar_url = (
            f"{NASA_BASE_URL}"
            f"?parameters={SOLAR_PARAMS}"
            f"&community={COMMUNITY}"
            f"&latitude={latitude}"
            f"&longitude={longitude}"
            f"&start={start_str}"
            f"&end={end_str}"
            "&format=JSON"
        )

        logger.info(
            "fetching_nasa_data",
            latitude=latitude,
            longitude=longitude,
            start=start_str,
            end=end_str,
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                wind_response = await client.get(wind_url)
                solar_response = await client.get(solar_url)
        except httpx.TimeoutException:
            logger.error("nasa_api_timeout", url=wind_url)
            raise HTTPException(
                status_code=504,
                detail="NASA POWER API request timed out",
            )
        except httpx.RequestError as exc:
            logger.error("nasa_api_request_error", error=str(exc))
            raise HTTPException(
                status_code=502,
                detail=f"Failed to connect to NASA POWER API: {exc}",
            )

        if wind_response.status_code != 200:
            logger.error(
                "nasa_wind_api_error",
                status_code=wind_response.status_code,
                response=wind_response.text[:500],
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    f"NASA POWER API returned {wind_response.status_code} "
                    "for wind data"
                ),
            )

        if solar_response.status_code != 200:
            logger.error(
                "nasa_solar_api_error",
                status_code=solar_response.status_code,
                response=solar_response.text[:500],
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    f"NASA POWER API returned {solar_response.status_code} "
                    "for solar data"
                ),
            )

        wind_json: dict[str, Any] = wind_response.json()
        solar_json: dict[str, Any] = solar_response.json()

        # Merge solar parameters into wind response structure
        solar_params = solar_json.get("properties", {}).get("parameter", {})
        wind_json.setdefault("properties", {}).setdefault("parameter", {}).update(
            solar_params
        )

        logger.info("nasa_data_fetched_successfully")
        return wind_json
