from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import matplotlib.pyplot as plt
import pandas as pd
import os
import uuid
import numpy as np

app = FastAPI()

# Data model
class WindDataPoint(BaseModel):
    avg_wind_speed: float
    avg_wind_direction: float

class WindDataRequest(BaseModel):
    station_name: str
    data: List[WindDataPoint]

# API Endpoint to generate Excel + JPG
@app.post("/generate-files")
async def generate_files(request: WindDataRequest):

    file_id = str(uuid.uuid4())

    # Build DataFrame
    df = pd.DataFrame([{
        "Avg Wind Speed (m/s)": point.avg_wind_speed,
        "Avg Wind Direction (degrees)": point.avg_wind_direction
    } for point in request.data])

    # Generate Excel file
    excel_filename = f"{file_id}_wind_data.xlsx"
    df.to_excel(excel_filename, index=False)

    #### --- 1st Chart: Scatter Polar Chart --- ####
    fig1 = plt.figure(figsize=(6, 6))
    ax1 = fig1.add_subplot(111, polar=True)

    theta = df["Avg Wind Direction (degrees)"] * (np.pi / 180.0)
    r = df["Avg Wind Speed (m/s)"]

    # Scatter plot
    scatter = ax1.scatter(theta, r, c=r, cmap='viridis', alpha=0.75)
    plt.colorbar(scatter, ax=ax1, label='Wind Speed (m/s)')

    ax1.set_theta_zero_location('N')
    ax1.set_theta_direction(-1)

    # Degree labels every 10°
    degree_ticks = np.arange(0, 360, 10)
    ax1.set_xticks(np.deg2rad(degree_ticks))
    ax1.set_xticklabels([f"{d}°" for d in degree_ticks])

    # Cardinal points
    cardinal_degrees = [0, 90, 180, 270]
    for label, degree in zip(['N', 'E', 'S', 'W'], cardinal_degrees):
        angle_rad = np.deg2rad(degree)
        ax1.text(angle_rad, ax1.get_rmax() + 0.1 * ax1.get_rmax(), label,
                 horizontalalignment='center', verticalalignment='center',
                 fontsize=12, fontweight='bold', color='black')

    ax1.set_title(f"Polar Wind Chart (Scatter) - {request.station_name}", pad=20)

    # Save scatter chart
    scatter_jpg_filename = f"{file_id}_wind_scatter_chart.jpg"
    plt.savefig(scatter_jpg_filename, dpi=300, bbox_inches='tight')
    plt.close()

    #### --- 2nd Chart: Wind Rose (Bar Chart) --- ####
    fig2 = plt.figure(figsize=(6, 6))
    ax2 = fig2.add_subplot(111, polar=True)

    # Sort bars for better display
    sort_idx = np.argsort(theta)
    theta_sorted = theta.iloc[sort_idx]
    r_sorted = r.iloc[sort_idx]

    bars = ax2.bar(theta_sorted, r_sorted,
                   width=np.deg2rad(8),  # 8 degree width
                   bottom=0.0,
                   color=plt.cm.viridis(r_sorted / r_sorted.max()),
                   alpha=0.75,
                   edgecolor='black')

    ax2.set_theta_zero_location('N')
    ax2.set_theta_direction(-1)

    # Degree labels every 10°
    ax2.set_xticks(np.deg2rad(degree_ticks))
    ax2.set_xticklabels([f"{d}°" for d in degree_ticks])

    # Cardinal points
    for label, degree in zip(['N', 'E', 'S', 'W'], cardinal_degrees):
        angle_rad = np.deg2rad(degree)
        ax2.text(angle_rad, ax2.get_rmax() + 0.1 * ax2.get_rmax(), label,
                 horizontalalignment='center', verticalalignment='center',
                 fontsize=12, fontweight='bold', color='black')

    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(0, r_sorted.max()))
    sm.set_array([])
    plt.colorbar(sm, ax=ax2, pad=0.1, label='Wind Speed (m/s)')

    ax2.set_title(f"Polar Wind Rose (Bar Chart) - {request.station_name}", pad=20)

    # Save bar chart
    bar_jpg_filename = f"{file_id}_wind_bar_chart.jpg"
    plt.savefig(bar_jpg_filename, dpi=300, bbox_inches='tight')
    plt.close()

    #### --- Return URLs --- ####
    return {
        "excel_file_url": f"/download/{excel_filename}",
        "scatter_chart_file_url": f"/download/{scatter_jpg_filename}",
        "bar_chart_file_url": f"/download/{bar_jpg_filename}"
    }





# Download Endpoint
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(".", filename)
    if os.path.isfile(file_path):
        return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
    return {"error": "File not found"}
