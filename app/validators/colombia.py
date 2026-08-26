"""Validators for Colombia-specific geographic and temporal constraints.

Canonical source for geographic bounding box constants and validation
functions.  The Pydantic ``WeatherDataRequest`` schema imports the
constants for ``Field`` constraints and delegates cross-field date
validation to ``validate_date_range``.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

# ---------------------------------------------------------------------------
# Colombia bounding box (approximate continental boundaries)
# ---------------------------------------------------------------------------
COLOMBIA_LAT_MIN: float = -4.23
COLOMBIA_LAT_MAX: float = 12.44
COLOMBIA_LON_MIN: float = -79.09
COLOMBIA_LON_MAX: float = -66.88


def validate_colombia_bbox(latitude: float, longitude: float) -> None:
    """Validate that coordinates fall within Colombia's bounding box.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.

    Raises:
        ValueError: If coordinates are outside Colombia's bounding box.
    """
    if not (COLOMBIA_LAT_MIN <= latitude <= COLOMBIA_LAT_MAX):
        raise ValueError(
            f"Latitude {latitude} is outside Colombia "
            f"(valid range: {COLOMBIA_LAT_MIN} to {COLOMBIA_LAT_MAX})"
        )
    if not (COLOMBIA_LON_MIN <= longitude <= COLOMBIA_LON_MAX):
        raise ValueError(
            f"Longitude {longitude} is outside Colombia "
            f"(valid range: {COLOMBIA_LON_MIN} to {COLOMBIA_LON_MAX})"
        )


def validate_date_range(start: date, end: date) -> None:
    """Validate that a date range is valid and not in the future.

    Args:
        start: Start date.
        end: End date.

    Raises:
        ValueError: If start >= end or either date is in the future.
    """
    today = datetime.now(tz=timezone.utc).date()
    if start > today:
        raise ValueError(f"Start date {start} is in the future")
    if end > today:
        raise ValueError(f"End date {end} is in the future")
    if start >= end:
        raise ValueError(
            f"Start date {start} must be before end date {end}"
        )
