"""Tests for Colombia-specific validators."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.validators.colombia import (
    validate_colombia_bbox,
    validate_date_range,
)


class TestValidateColombiaBbox:
    """Tests for geographic bounding box validation."""

    def test_bogota_valid(self):
        """Bogota coordinates are within Colombia bbox."""
        validate_colombia_bbox(4.6097, -74.0817)  # Should not raise

    def test_southern_boundary(self):
        """Southernmost Colombia coordinate is valid."""
        validate_colombia_bbox(-4.23, -74.0)

    def test_northern_boundary(self):
        """Northernmost Colombia coordinate is valid."""
        validate_colombia_bbox(12.44, -72.0)

    def test_western_boundary(self):
        """Westernmost Colombia coordinate is valid."""
        validate_colombia_bbox(2.0, -79.09)

    def test_eastern_boundary(self):
        """Easternmost Colombia coordinate is valid."""
        validate_colombia_bbox(2.0, -66.88)

    def test_latitude_too_north(self):
        """Latitude above Colombia is rejected."""
        with pytest.raises(ValueError, match="outside Colombia"):
            validate_colombia_bbox(13.0, -74.0)

    def test_latitude_too_south(self):
        """Latitude below Colombia is rejected."""
        with pytest.raises(ValueError, match="outside Colombia"):
            validate_colombia_bbox(-5.0, -74.0)

    def test_longitude_too_east(self):
        """Longitude east of Colombia is rejected."""
        with pytest.raises(ValueError, match="outside Colombia"):
            validate_colombia_bbox(4.0, -60.0)

    def test_longitude_too_west(self):
        """Longitude west of Colombia is rejected."""
        with pytest.raises(ValueError, match="outside Colombia"):
            validate_colombia_bbox(4.0, -80.0)


class TestValidateDateRange:
    """Tests for date range validation."""

    def test_valid_past_range(self):
        """Past date range with start < end is valid."""
        validate_date_range(date(2024, 1, 1), date(2024, 1, 31))

    def test_start_after_end_rejected(self):
        """Start date after end date is rejected."""
        with pytest.raises(ValueError, match="must be before"):
            validate_date_range(date(2024, 1, 31), date(2024, 1, 1))

    def test_start_equals_end_rejected(self):
        """Start date equal to end date is rejected."""
        with pytest.raises(ValueError, match="must be before"):
            validate_date_range(date(2024, 1, 15), date(2024, 1, 15))

    def test_future_start_rejected(self):
        """Start date in the future is rejected."""
        future = datetime.now(tz=timezone.utc).date() + timedelta(days=10)
        with pytest.raises(ValueError, match="in the future"):
            validate_date_range(future, future + timedelta(days=5))

    def test_future_end_rejected(self):
        """End date in the future is rejected."""
        today = datetime.now(tz=timezone.utc).date()
        with pytest.raises(ValueError, match="in the future"):
            validate_date_range(today - timedelta(days=5), today + timedelta(days=5))
