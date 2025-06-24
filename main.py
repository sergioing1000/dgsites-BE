# main.py
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import date
from dotenv import load_dotenv
import os
import uuid
import httpx

from generate_excel import generate_excel_with_charts

# Load .env file
load_dotenv()

app = FastAPI()

ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

if ENVIRONMENT == "production":
    allowed_origins = ["https://solar-sergioapp.netlify.app"]
else:
    allowed_origins = ["http://localhost:3000", "null"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class WindDataRequest(BaseModel):
    station_name: str
    latitude: float
    longitude: float
    start: date
    end: date

@app.post("/generate-files")
async def generate_files(request: WindDataRequest):
    file_id = str(uuid.uuid4())

    nasa_api_url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=WS2M,WD2M"
        f"&community=RE"
        f"&latitude={request.latitude}"
        f"&longitude={request.longitude}"
        f"&start={request.start.strftime('%Y%m%d')}"
        f"&end={request.end.strftime('%Y%m%d')}"
        "&format=JSON"
    )

    solar_api_url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=ALLSKY_SFC_SW_DWN"
        f"&community=RE"
        f"&latitude={request.latitude}"
        f"&longitude={request.longitude}"
        f"&start={request.start.strftime('%Y%m%d')}"
        f"&end={request.end.strftime('%Y%m%d')}"
        "&format=JSON"
    )

    async with httpx.AsyncClient() as client:
        nasa_response = await client.get(nasa_api_url)
        solar_response = await client.get(solar_api_url)

    if nasa_response.status_code != 200:
        return {"error": "Failed to fetch wind data from NASA POWER API"}
    
    if solar_response.status_code != 200:
        return {"error": "Failed to fetch solar data from NASA POWER API"}

    nasa_json = nasa_response.json()
    solar_json = solar_response.json()

    excel_filename = generate_excel_with_charts(
        file_id=file_id,
        station_name=request.station_name,
        latitude=request.latitude,
        longitude=request.longitude,
        start_date=request.start,
        end_date=request.end,
        nasa_data=nasa_json,
        solar_data=solar_json
    )

    return {
        "excel_file_url": f"/download/{excel_filename}"
    }

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(".", filename)
    if os.path.isfile(file_path):
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    return {"error": "File not found"}