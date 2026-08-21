import os
import pytest


def test_generate_files_invalid_body(client):
    """Test that invalid request body returns 422 Validation Error."""
    response = client.post("/generate-files", json={})
    assert response.status_code == 422


def test_generate_files_missing_fields(client, invalid_wind_request):
    """Test that request with missing fields returns 422."""
    response = client.post("/generate-files", json=invalid_wind_request)
    assert response.status_code == 422


def test_download_file_not_found(client):
    """Test that downloading non-existent file returns error."""
    response = client.get("/download/nonexistent_file.xlsx")
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"] == "File not found"


def test_download_file_success(client, tmp_path, monkeypatch):
    """Test that downloading an existing file returns the file.

    The /download endpoint resolves files relative to the current working
    directory (os.path.join(".", filename) in main.py). To validate the
    happy path without polluting the project root, we change into pytest's
    tmp_path fixture, create an .xlsx file there, hit the endpoint, and
    rely on monkeypatch to restore the original CWD at teardown.
    """
    monkeypatch.chdir(tmp_path)

    filename = "test_download_success.xlsx"
    file_path = tmp_path / filename
    file_path.write_bytes(b"fake excel content")

    response = client.get(f"/download/{filename}")

    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
