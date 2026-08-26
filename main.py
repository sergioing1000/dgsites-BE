"""FastAPI application entry point for dgsites-BE.

Initialises the FastAPI instance, configures CORS based on the active
environment, and mounts the weather-data API router.

Environment variables:
    ENVIRONMENT: Deployment target (``local`` | ``production``).
        Controls the CORS origin allow-list.
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.weather import router as weather_router

# Load .env file before any configuration that reads environment variables.
load_dotenv()

app = FastAPI(
    title="dgsites-BE",
    description="Backend API for weather data and Excel report generation",
    version="1.0.0",
)

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

# Mount API routers
app.include_router(weather_router)
