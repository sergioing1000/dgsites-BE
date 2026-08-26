"""Excel report generation service.

Modularized from the original generate_excel.py to support in-memory
generation via io.BytesIO with streaming response delivery.
"""

from __future__ import annotations

import io
import os
import tempfile
from datetime import date, datetime, timezone
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import structlog
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment

logger = structlog.get_logger(__name__)


def _create_polar_chart(
    theta: Any,
    r: Any,
    title: str,
    cmap: str,
    filepath: str,
) -> None:
    """Create a polar scatter chart and save to file.

    Args:
        theta: Angular data in radians.
        r: Radial data (wind speed).
        title: Chart title.
        cmap: Matplotlib colormap name.
        filepath: Output file path for the chart image.
    """
    degree_ticks = np.arange(0, 360, 10)

    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, polar=True)
    scatter = ax.scatter(theta, r, c=r, cmap=cmap, alpha=0.75, edgecolors="black")
    plt.colorbar(scatter, ax=ax, label="Wind Speed (m/s)")
    ax.set_theta_zero_location("N")  # type: ignore[attr-defined]
    ax.set_theta_direction(-1)  # type: ignore[attr-defined]
    ax.set_xticks(np.deg2rad(degree_ticks))
    ax.set_xticklabels([f"{d}°" for d in degree_ticks])
    for label, degree in zip(["N", "E", "S", "W"], [0, 90, 180, 270]):
        ax.text(
            np.deg2rad(degree),
            ax.get_rmax() * 1.1,  # type: ignore[attr-defined]
            label,
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
        )
    ax.set_title(title, pad=20)
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close(fig)


def generate_excel_bytes(
    station_name: str,
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    nasa_data: dict[str, Any],
) -> io.BytesIO:
    """Generate an Excel workbook in memory with wind/solar data and charts.

    Creates a multi-sheet Excel workbook containing:
    - Info sheet with station metadata
    - Wind Data sheet with daily observations
    - Monthly Summary sheet
    - Solar Radiation sheet
    - Monthly Solar Radiation sheet
    - Chart sheets (scatter, wind rose, monthly summary, solar monthly)

    Charts are generated as temporary files, inserted into the workbook,
    then cleaned up. The final workbook is returned as a BytesIO buffer.

    Args:
        station_name: Name of the weather station.
        latitude: Station latitude in decimal degrees.
        longitude: Station longitude in decimal degrees.
        start_date: Start date of the data range.
        end_date: End date of the data range.
        nasa_data: NASA POWER API JSON response (combined wind + solar).

    Returns:
        BytesIO buffer containing the Excel workbook.

    Raises:
        KeyError: If expected NASA data parameters are missing.
        ValueError: If NASA data is empty or malformed.
    """
    logger.info(
        "generating_excel",
        station_name=station_name,
        latitude=latitude,
        longitude=longitude,
    )

    params = nasa_data.get("properties", {}).get("parameter", {})
    ws2m = params.get("WS2M", {})
    wd2m = params.get("WD2M", {})
    solar = params.get("ALLSKY_SFC_SW_DWN", {})

    if not ws2m or not wd2m:
        raise ValueError("NASA data missing wind parameters (WS2M, WD2M)")

    # Build wind DataFrame
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(list(ws2m.keys()), format="%Y%m%d"),
            "Wind Speed (m/s)": list(ws2m.values()),
            "Wind Direction (degrees)": list(wd2m.values()),
        }
    )

    df["YearMonth"] = df["Date"].dt.to_period("M")
    monthly_avg = (
        df.groupby("YearMonth")
        .agg({"Wind Speed (m/s)": "mean", "Wind Direction (degrees)": "mean"})
        .reset_index()
    )
    monthly_avg["YearMonth"] = monthly_avg["YearMonth"].astype(str)

    # Build solar DataFrame
    df_solar: pd.DataFrame | None = None
    monthly_solar_avg: pd.DataFrame | None = None
    if solar:
        df_solar = pd.DataFrame(
            {
                "Date": pd.to_datetime(list(solar.keys()), format="%Y%m%d"),
                "Solar Radiation (kWh/m²/day)": list(solar.values()),
            }
        )
        df_solar["YearMonth"] = df_solar["Date"].dt.to_period("M")
        monthly_solar_avg = (
            df_solar.groupby("YearMonth")
            .agg({"Solar Radiation (kWh/m²/day)": "mean"})
            .reset_index()
        )
        monthly_solar_avg["YearMonth"] = monthly_solar_avg["YearMonth"].astype(str)

    # Generate chart images as temp files (cleaned up by TemporaryDirectory)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Daily polar scatter
            theta_daily = df["Wind Direction (degrees)"] * np.pi / 180.0
            r_daily = df["Wind Speed (m/s)"]
            scatter_path = os.path.join(tmpdir, "scatter.jpg")
            _create_polar_chart(
                theta_daily,
                r_daily,
                f"Polar Wind Chart - {station_name}",
                "viridis",
                scatter_path,
            )

            # Wind rose bar chart
            fig2 = plt.figure(figsize=(6, 6))
            ax2 = fig2.add_subplot(111, polar=True)
            sort_idx = np.argsort(theta_daily.values)
            ax2.bar(
                theta_daily.iloc[sort_idx],
                r_daily.iloc[sort_idx],
                width=np.deg2rad(8),
                bottom=0.0,
                color=plt.cm.viridis(r_daily.iloc[sort_idx] / r_daily.max()),
                alpha=0.75,
                edgecolor="black",
            )
            ax2.set_theta_zero_location("N")  # type: ignore[attr-defined]
            ax2.set_theta_direction(-1)  # type: ignore[attr-defined]
            degree_ticks = np.arange(0, 360, 10)
            ax2.set_xticks(np.deg2rad(degree_ticks))
            ax2.set_xticklabels([f"{d}°" for d in degree_ticks])
            for label, degree in zip(["N", "E", "S", "W"], [0, 90, 180, 270]):
                ax2.text(
                    np.deg2rad(degree),
                    ax2.get_rmax() * 1.1,  # type: ignore[attr-defined]
                    label,
                    ha="center",
                    va="center",
                    fontsize=12,
                    fontweight="bold",
                )
            ax2.set_title(f"Polar Wind Rose - {station_name}", pad=20)
            plt.colorbar(
                plt.cm.ScalarMappable(
                    cmap="viridis", norm=plt.Normalize(0, r_daily.max())
                ),
                ax=ax2,
            )
            bar_path = os.path.join(tmpdir, "bar.jpg")
            plt.savefig(bar_path, dpi=300, bbox_inches="tight")
            plt.close(fig2)

            # Monthly summary polar
            theta_monthly = monthly_avg["Wind Direction (degrees)"] * np.pi / 180.0
            r_monthly = monthly_avg["Wind Speed (m/s)"]
            summary_path = os.path.join(tmpdir, "summary.jpg")
            _create_polar_chart(
                theta_monthly,
                r_monthly,
                f"Monthly Summary Polar Chart - {station_name}",
                "plasma",
                summary_path,
            )

            # Monthly solar bar chart
            solar_chart_path: str | None = None
            if monthly_solar_avg is not None and not monthly_solar_avg.empty:
                fig_solar = plt.figure(figsize=(8, 6))
                ax_solar = fig_solar.add_subplot(111)
                ax_solar.barh(
                    monthly_solar_avg["YearMonth"],
                    monthly_solar_avg["Solar Radiation (kWh/m²/day)"],
                    color="goldenrod",
                    edgecolor="black",
                )
                ax_solar.set_xlabel("Solar Radiation (kWh/m²/day)")
                ax_solar.set_title(f"Monthly Solar Radiation - {station_name}")
                plt.tight_layout()
                solar_chart_path = os.path.join(tmpdir, "solar_monthly.jpg")
                plt.savefig(solar_chart_path, dpi=300)
                plt.close(fig_solar)

            # Write Excel to temp file (openpyxl needs a real file path)
            excel_path = os.path.join(tmpdir, "report.xlsx")
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                df[["Date", "Wind Speed (m/s)", "Wind Direction (degrees)"]].to_excel(
                    writer, sheet_name="Wind Data", index=False
                )
                monthly_avg.to_excel(writer, sheet_name="Monthly Summary", index=False)

                if df_solar is not None:
                    df_solar.to_excel(
                        writer, sheet_name="Solar Radiation", index=False
                    )
                if monthly_solar_avg is not None:
                    monthly_solar_avg.to_excel(
                        writer, sheet_name="Monthly Solar Radiation", index=False
                    )

                # Info sheet
                now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                info_df = pd.DataFrame(
                    {
                        "Parameter": [
                            "Station Name",
                            "Latitude",
                            "Longitude",
                            "Start Date",
                            "End Date",
                            "Generated At",
                            "Google Maps Link",
                        ],
                        "Value": [
                            station_name,
                            latitude,
                            longitude,
                            start_date.strftime("%Y-%m-%d"),
                            end_date.strftime("%Y-%m-%d"),
                            now_str,
                            f"https://www.google.com/maps?q={latitude},{longitude}",
                        ],
                    }
                )
                info_df.to_excel(writer, sheet_name="Info", index=False)

            # Load workbook and apply formatting
            wb = load_workbook(excel_path)

            def auto_width(sheet_name: str) -> None:
                """Auto-fit column widths for a sheet.

                Iterates every column in the sheet, measures the maximum
                string length of cell values, and sets the column width
                to that length plus a two-character padding.

                Args:
                    sheet_name: Title of the workbook sheet to resize.
                """
                ws = wb[sheet_name]
                for col in ws.columns:
                    max_len = max(
                        len(str(cell.value)) if cell.value else 0 for cell in col
                    )
                    ws.column_dimensions[col[0].column_letter].width = max_len + 2  # type: ignore[union-attr]

            def format_cells(
                sheet_name: str,
                column_letter: str,
                number_format: str | None = None,
                align: str = "center",
            ) -> None:
                """Apply number format and alignment to a column.

                Skips the header row (row 1) and applies formatting only
                to data rows.

                Args:
                    sheet_name: Title of the workbook sheet to format.
                    column_letter: Excel column letter (e.g. ``"A"``,
                        ``"B"``).
                    number_format: Optional openpyxl number format string
                        (e.g. ``"DD-MMM-YY"``, ``"0.00"``). ``None``
                        leaves the format unchanged.
                    align: Horizontal alignment — ``"center"`` (default)
                        or ``"right"``.
                """
                ws = wb[sheet_name]
                for cell in ws[column_letter][1:]:
                    if number_format:
                        cell.number_format = number_format
                    cell.alignment = Alignment(horizontal=align)

            for sheet_name in [
                "Wind Data",
                "Monthly Summary",
                "Solar Radiation",
                "Monthly Solar Radiation",
                "Info",
            ]:
                if sheet_name in wb.sheetnames:
                    auto_width(sheet_name)

            if "Wind Data" in wb.sheetnames:
                format_cells("Wind Data", "A", "DD-MMM-YY")
                format_cells("Wind Data", "B", "0.00", "right")
                format_cells("Wind Data", "C", "0")

            if "Monthly Summary" in wb.sheetnames:
                format_cells("Monthly Summary", "B", "0.00", "right")
                format_cells("Monthly Summary", "C", "0")

            if "Solar Radiation" in wb.sheetnames:
                format_cells("Solar Radiation", "A", "DD-MMM-YY")
                format_cells("Solar Radiation", "B", "0.00", "right")

            if "Monthly Solar Radiation" in wb.sheetnames:
                format_cells("Monthly Solar Radiation", "B", "0.00", "right")

            # Insert chart sheets
            chart_specs = [
                ("Scatter Chart", scatter_path),
                ("Wind Rose Chart", bar_path),
                ("Monthly Summary Polar", summary_path),
            ]
            if solar_chart_path:
                chart_specs.append(("Monthly Solar Radiation Chart", solar_chart_path))

            for title, img_file in chart_specs:
                sheet = wb.create_sheet(title=title)
                img = ExcelImage(img_file)
                img.anchor = "A1"
                sheet.add_image(img)

            # Reorder sheets
            desired_order = [
                "Info",
                "Solar Radiation",
                "Monthly Solar Radiation",
                "Wind Data",
                "Monthly Summary",
                "Scatter Chart",
                "Wind Rose Chart",
                "Monthly Summary Polar",
                "Monthly Solar Radiation Chart",
            ]
            wb._sheets = [wb[s] for s in desired_order if s in wb.sheetnames]  # type: ignore[attr-defined]

            # Save to BytesIO
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)

            logger.info("excel_generated_successfully", sheets=len(wb.sheetnames))
            return buf

    except (KeyError, ValueError, OSError) as exc:
        logger.exception("excel_generation_failed", error=str(exc))
        raise
