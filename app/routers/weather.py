"""Weather data API endpoints.

Provides JSON and Excel report endpoints for NASA POWER weather data
queries over Colombia.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.weather import (
    DailyData,
    Metadata,
    MonthlySummary,
    WeatherDataRequest,
    WeatherDataResponse,
)
from app.services.excel import generate_excel_bytes
from app.services.nasa import NASAPowerService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["weather"])

nasa_service = NASAPowerService()


def _parse_nasa_response(
    nasa_data: dict[str, Any],
    station_name: str,
    latitude: float,
    longitude: float,
    start: date,
    end: date,
) -> WeatherDataResponse:
    """Parse NASA POWER API response into WeatherDataResponse.

    Args:
        nasa_data: NASA POWER API JSON response.
        station_name: Station name from the request.
        latitude: Station latitude.
        longitude: Station longitude.
        start: Request start date.
        end: Request end date.

    Returns:
        Parsed WeatherDataResponse with daily data, monthly summary, and metadata.
    """
    params = nasa_data.get("properties", {}).get("parameter", {})
    ws2m = params.get("WS2M", {})
    wd2m = params.get("WD2M", {})
    solar = params.get("ALLSKY_SFC_SW_DWN", {})

    daily_data: list[DailyData] = []
    # Collect all unique dates from all parameters
    all_dates = sorted(set(list(ws2m.keys()) + list(wd2m.keys()) + list(solar.keys())))

    for date_str in all_dates:
        wind_speed = ws2m.get(date_str)
        wind_dir = wd2m.get(date_str)
        solar_val = solar.get(date_str)

        # NASA returns -999.0 for missing data
        daily_data.append(
            DailyData(
                date=date_str,
                wind_speed_ms=wind_speed if wind_speed is not None and wind_speed != -999.0 else None,
                wind_direction_deg=wind_dir if wind_dir is not None and wind_dir != -999.0 else None,
                solar_radiation_kwh=solar_val if solar_val is not None and solar_val != -999.0 else None,
            )
        )

    # Compute monthly summaries
    monthly_map: dict[str, dict[str, list[float]]] = {}
    for d in daily_data:
        ym = d.date[:6]  # YYYYMM
        if ym not in monthly_map:
            monthly_map[ym] = {"ws": [], "wd": [], "sr": []}
        if d.wind_speed_ms is not None:
            monthly_map[ym]["ws"].append(d.wind_speed_ms)
        if d.wind_direction_deg is not None:
            monthly_map[ym]["wd"].append(d.wind_direction_deg)
        if d.solar_radiation_kwh is not None:
            monthly_map[ym]["sr"].append(d.solar_radiation_kwh)

    monthly_summary: list[MonthlySummary] = []
    for ym in sorted(monthly_map.keys()):
        data = monthly_map[ym]
        monthly_summary.append(
            MonthlySummary(
                year_month=ym,
                avg_wind_speed_ms=(
                    round(sum(data["ws"]) / len(data["ws"]), 2)
                    if data["ws"]
                    else None
                ),
                avg_wind_direction_deg=(
                    round(sum(data["wd"]) / len(data["wd"]), 2)
                    if data["wd"]
                    else None
                ),
                avg_solar_radiation_kwh=(
                    round(sum(data["sr"]) / len(data["sr"]), 2)
                    if data["sr"]
                    else None
                ),
            )
        )

    return WeatherDataResponse(
        daily_data=daily_data,
        monthly_summary=monthly_summary,
        metadata=Metadata(
            station_name=station_name,
            latitude=latitude,
            longitude=longitude,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            total_days=len(daily_data),
        ),
    )


@router.post(
    "/weather-data",
    response_model=WeatherDataResponse,
    summary="Get weather data as JSON",
    description=(
        "Fetch daily wind speed, wind direction, and solar radiation data "
        "from the NASA POWER API for a station within Colombia. Returns "
        "daily observations, monthly aggregated summaries, and request "
        "metadata as JSON."
    ),
    responses={
        200: {
            "description": "Weather data retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "daily_data": [
                            {
                                "date": "20240101",
                                "wind_speed_ms": 3.26,
                                "wind_direction_deg": 152.07,
                                "solar_radiation_kwh": 5.42,
                            }
                        ],
                        "monthly_summary": [
                            {
                                "year_month": "2024-01",
                                "avg_wind_speed_ms": 3.15,
                                "avg_wind_direction_deg": 148.32,
                                "avg_solar_radiation_kwh": 5.38,
                            }
                        ],
                        "metadata": {
                            "station_name": "Bogotá",
                            "latitude": 4.6097,
                            "longitude": -74.0817,
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                            "total_days": 31,
                        },
                    }
                }
            },
        },
        422: {
            "description": (
                "Validation error — missing fields, coordinates outside "
                "Colombia bounding box, or invalid date range."
            )
        },
        502: {"description": "NASA POWER API returned an error or is unreachable."},
        504: {"description": "NASA POWER API request timed out (>30 s)."},
    },
    response_description="Weather data with daily observations, monthly summaries, and metadata.",
)
async def get_weather_data(request: WeatherDataRequest) -> WeatherDataResponse:
    """Fetch wind and solar data from NASA POWER API.

    Queries the NASA POWER daily point endpoint for wind (WS2M, WD2M)
    and solar (ALLSKY_SFC_SW_DWN) parameters, then aggregates the raw
    data into daily observations and monthly summaries.

    Args:
        request: Validated request body containing station name,
            Colombia-bounded coordinates, and a valid date range.

    Returns:
        WeatherDataResponse with daily_data, monthly_summary, and
        metadata describing the query coverage.

    Raises:
        HTTPException(422): Request validation failed (Pydantic or
            cross-field date validation).
        HTTPException(502): NASA POWER API returned a non-200 status
            or the connection failed.
        HTTPException(504): NASA POWER API request timed out.
    """
    logger.info(
        "weather_data_request",
        station_name=request.station_name,
        latitude=request.latitude,
        longitude=request.longitude,
    )

    nasa_data = await nasa_service.fetch_weather_data(
        latitude=request.latitude,
        longitude=request.longitude,
        start=request.start,
        end=request.end,
    )

    return _parse_nasa_response(
        nasa_data=nasa_data,
        station_name=request.station_name,
        latitude=request.latitude,
        longitude=request.longitude,
        start=request.start,
        end=request.end,
    )


@router.post(
    "/excel-report",
    summary="Generate Excel report with charts (streaming)",
    description=(
        "Generate a multi-sheet Excel workbook containing wind data, "
        "monthly summaries, solar radiation tables, and polar/bar chart "
        "images. The workbook is streamed back as an XLSX attachment."
    ),
    responses={
        200: {
            "description": "Excel workbook generated and streamed successfully.",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
        },
        422: {
            "description": (
                "Validation error — missing fields, coordinates outside "
                "Colombia bounding box, or invalid date range."
            )
        },
        502: {"description": "NASA POWER API returned an error or is unreachable."},
        504: {"description": "NASA POWER API request timed out (>30 s)."},
    },
    response_description="Streaming XLSX file attachment with weather data and charts.",
)
async def get_excel_report(request: WeatherDataRequest) -> StreamingResponse:
    """Generate and stream an Excel workbook with wind/solar data and charts.

    Fetches raw NASA POWER data, then delegates to the Excel service to
    build a multi-sheet workbook (Info, Wind Data, Monthly Summary, Solar
    Radiation, charts) and stream it as an XLSX attachment.

    Args:
        request: Validated request body containing station name,
            Colombia-bounded coordinates, and a valid date range.

    Returns:
        StreamingResponse with ``Content-Disposition: attachment``
        header; the body is an XLSX workbook.

    Raises:
        HTTPException(422): Request validation failed (Pydantic or
            cross-field date validation).
        HTTPException(502): NASA POWER API returned a non-200 status
            or the connection failed.
        HTTPException(504): NASA POWER API request timed out.
    """
    logger.info(
        "excel_report_request",
        station_name=request.station_name,
        latitude=request.latitude,
        longitude=request.longitude,
    )

    nasa_data = await nasa_service.fetch_weather_data(
        latitude=request.latitude,
        longitude=request.longitude,
        start=request.start,
        end=request.end,
    )

    excel_buffer = generate_excel_bytes(
        station_name=request.station_name,
        latitude=request.latitude,
        longitude=request.longitude,
        start_date=request.start,
        end_date=request.end,
        nasa_data=nasa_data,
    )

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{request.station_name}_weather_report.xlsx"'
            )
        },
    )
