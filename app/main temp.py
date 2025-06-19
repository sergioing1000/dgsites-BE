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

    # Create Polar Chart
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, polar=True)

    # Data for plot
    theta = df["Avg Wind Direction (degrees)"] * (3.14159265 / 180.0)
    r = df["Avg Wind Speed (m/s)"]

    # Scatter plot
    c = ax.scatter(theta, r, c=r, cmap='viridis', alpha=0.75)
    plt.colorbar(c, ax=ax, label='Wind Speed (m/s)')

    # Set 0° at top (North) and clockwise rotation
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)


    # Add degree labels every 10 degrees
    degree_ticks = np.arange(0, 360, 10)
    ax.set_xticks(np.deg2rad(degree_ticks))  # Convert degrees to radians
    ax.set_xticklabels([f"{d}°" for d in degree_ticks])

    # Optionally: make cardinal points stand out
    cardinal_degrees = [0, 90, 180, 270]
    for label, degree in zip(['N', 'E', 'S', 'W'], cardinal_degrees):
        angle_rad = np.deg2rad(degree)
        ax.text(
            angle_rad,    # angle in radians
            ax.get_rmax() + 0.1 * ax.get_rmax(),  # position just outside the circle
            label,
            horizontalalignment='center',
            verticalalignment='center',
            fontsize=12,
            fontweight='bold',
            color='black'
        )

    # Title
    ax.set_title(f"Polar Wind Chart - {request.station_name}", pad=20)

    # Save JPG
    jpg_filename = f"{file_id}_wind_chart.jpg"
    plt.savefig(jpg_filename, dpi=300, bbox_inches='tight')
    plt.close()

    return {
        "excel_file_url": f"/download/{excel_filename}",
        "chart_file_url": f"/download/{jpg_filename}"
    }



# Download Endpoint
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(".", filename)
    if os.path.isfile(file_path):
        return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
    return {"error": "File not found"}
