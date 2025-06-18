from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import matplotlib.pyplot as plt
import pandas as pd
import os
import uuid

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

    df = pd.DataFrame([{
        "Avg Wind Speed (m/s)": point.avg_wind_speed,
        "Avg Wind Direction (degrees)": point.avg_wind_direction
    } for point in request.data])

    excel_filename = f"{file_id}_wind_data.xlsx"
    df.to_excel(excel_filename, index=False)

    # Create Polar Chart
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, polar=True)

    theta = df["Avg Wind Direction (degrees)"] * (3.14159265 / 180.0)
    r = df["Avg Wind Speed (m/s)"]

    c = ax.scatter(theta, r, c=r, cmap='viridis', alpha=0.75)
    plt.colorbar(c, ax=ax, label='Wind Speed (m/s)')
    ax.set_title(f"Polar Wind Chart - {request.station_name}")

    jpg_filename = f"{file_id}_wind_chart.jpg"
    plt.savefig(jpg_filename)
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
