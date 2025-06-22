
# Wind Data API with FastAPI 🚀

This project is a FastAPI-based backend that fetches wind speed and direction data from NASA POWER API for a given location and date range, generates polar charts and an Excel file with the results, and provides endpoints to download the generated files.

## Features

✅ Fetches daily wind data (speed and direction) from NASA POWER API  
✅ Generates:
- Daily Wind Scatter Polar Chart
- Wind Rose Bar Chart
- Monthly Summary Polar Chart

✅ Exports the data and charts into an Excel file  
✅ Serves the Excel file through a download endpoint  
✅ CORS configuration for local and production environments

---

## Requirements

- Python 3.9+
- The following Python packages (you can install via `requirements.txt`):

```text
fastapi
uvicorn
httpx
pydantic
python-dotenv
matplotlib
pandas
numpy
openpyxl
```

---

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

2. **Create a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the root directory:

```env
ENVIRONMENT=local
```

For production:

```env
ENVIRONMENT=production
```

---

## Running the Application

### Local Development

```bash
uvicorn main:app --reload --port 8000
```

This will start the FastAPI server at:  
[http://localhost:8000](http://localhost:8000)

---

## API Endpoints

### `POST /generate-files`

Generates the wind data Excel file with charts.

#### Request Body (JSON):

```json
{
  "station_name": "Your Station",
  "latitude": 12.3456,
  "longitude": -78.9101,
  "start": "2025-01-01",
  "end": "2025-01-31"
}
```

#### Response:

```json
{
  "excel_file_url": "/download/<generated_excel_filename.xlsx>"
}
```

---

### `GET /download/{filename}`

Downloads the generated Excel file.

Example:

```http
GET /download/12345_wind_data_with_charts.xlsx
```

---

## Project Structure

```text
.
├── main.py               # Main FastAPI app
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
└── README.md             # This file
```

---

## Notes

- NASA POWER API is public, no authentication required.
- The Excel file will include:
  - Wind Data sheet (daily)
  - Monthly Summary
  - Info sheet
  - 3 sheets with charts (Scatter, Wind Rose, Monthly Summary Polar)

---

## License

MIT License - Sergio Cruz
