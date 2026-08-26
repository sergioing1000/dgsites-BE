"""Weather data request and response schemas for NASA POWER API integration."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.validators.colombia import (
    COLOMBIA_LAT_MAX,
    COLOMBIA_LAT_MIN,
    COLOMBIA_LON_MAX,
    COLOMBIA_LON_MIN,
    validate_date_range,
)


class WeatherDataRequest(BaseModel):
    """Request schema for weather data queries.

    Validates station metadata, geographic coordinates within Colombia's
    bounding box, and temporal range constraints.

    Attributes:
        station_name: Human-readable station identifier (1–200 chars).
        latitude: Decimal degrees latitude; must fall within
            ``COLOMBIA_LAT_MIN`` (−4.23) to ``COLOMBIA_LAT_MAX`` (12.44).
        longitude: Decimal degrees longitude; must fall within
            ``COLOMBIA_LON_MIN`` (−79.09) to ``COLOMBIA_LON_MAX`` (−66.88).
        start: Inclusive start date for data retrieval (YYYY-MM-DD).
        end: Inclusive end date for data retrieval (YYYY-MM-DD).
    """

    station_name: str = Field(
        ..., min_length=1, max_length=200, description="Name of the weather station"
    )
    latitude: float = Field(
        ...,
        ge=COLOMBIA_LAT_MIN,
        le=COLOMBIA_LAT_MAX,
        description="Latitude in decimal degrees (Colombia)",
    )
    longitude: float = Field(
        ...,
        ge=COLOMBIA_LON_MIN,
        le=COLOMBIA_LON_MAX,
        description="Longitude in decimal degrees (Colombia)",
    )
    start: date = Field(..., description="Start date for data retrieval (YYYY-MM-DD)")
    end: date = Field(..., description="End date for data retrieval (YYYY-MM-DD)")

    @model_validator(mode="after")
    def validate_dates(self) -> WeatherDataRequest:
        """Delegate cross-field date validation to shared validator.

        Ensures neither date is in the future and that ``start`` is
        strictly before ``end``.

        Returns:
            self: The validated request instance.

        Raises:
            ValueError: If dates are future or ``start >= end``.
        """
        validate_date_range(self.start, self.end)
        return self


class DailyData(BaseModel):
    """Daily weather observation from NASA POWER API.

    Attributes:
        date: Observation date in ``YYYYMMDD`` format.
        wind_speed_ms: Wind speed at 2 m above ground (m/s).
            ``None`` when NASA reports the missing-data sentinel −999.0.
        wind_direction_deg: Wind direction at 2 m (degrees from north).
            ``None`` when NASA reports the missing-data sentinel −999.0.
        solar_radiation_kwh: All-sky surface shortwave downward
            irradiance (kWh/m²/day). ``None`` when NASA reports −999.0.
    """

    date: str = Field(..., description="Date in YYYYMMDD format")
    wind_speed_ms: float | None = Field(
        None, description="Wind speed at 2m (m/s)"
    )
    wind_direction_deg: float | None = Field(
        None, description="Wind direction at 2m (degrees)"
    )
    solar_radiation_kwh: float | None = Field(
        None,
        description="All-sky surface shortwave downward irradiance (kWh/m2/day)",
    )


class MonthlySummary(BaseModel):
    """Monthly aggregated weather statistics.

    Attributes:
        year_month: Year-month identifier in ``YYYY-MM`` format.
        avg_wind_speed_ms: Mean wind speed for the month (m/s).
            ``None`` when no valid daily readings exist.
        avg_wind_direction_deg: Mean wind direction for the month
            (degrees). ``None`` when no valid daily readings exist.
        avg_solar_radiation_kwh: Mean solar radiation for the month
            (kWh/m²/day). ``None`` when no valid daily readings exist.
    """

    year_month: str = Field(..., description="Year-month in YYYY-MM format")
    avg_wind_speed_ms: float | None = Field(
        None, description="Average wind speed (m/s)"
    )
    avg_wind_direction_deg: float | None = Field(
        None, description="Average wind direction (degrees)"
    )
    avg_solar_radiation_kwh: float | None = Field(
        None, description="Average solar radiation (kWh/m2/day)"
    )


class Metadata(BaseModel):
    """Response metadata including station info and data coverage.

    Attributes:
        station_name: Station name echoed from the request.
        latitude: Station latitude echoed from the request.
        longitude: Station longitude echoed from the request.
        start_date: Start date in ``YYYY-MM-DD`` format.
        end_date: End date in ``YYYY-MM-DD`` format.
        total_days: Count of daily records included in ``daily_data``.
    """

    station_name: str
    latitude: float
    longitude: float
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    total_days: int = Field(..., ge=0, description="Number of daily records returned")


class WeatherDataResponse(BaseModel):
    """Response schema for weather data queries.

    Contains daily observations, monthly summaries, and request metadata.

    Attributes:
        daily_data: Observations returned for each date in the requested range.
        monthly_summary: Aggregated wind and solar values grouped by month.
        metadata: Station, coordinate, date-range, and record-count metadata.
    """

    daily_data: list[DailyData] = Field(
        ..., description="Daily weather observations"
    )
    monthly_summary: list[MonthlySummary] = Field(
        ..., description="Monthly aggregated statistics"
    )
    metadata: Metadata = Field(..., description="Query metadata")
