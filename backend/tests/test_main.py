import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "BidSense API"
    assert data["version"] == "0.1.0"
    assert "status" in data


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_tenders_endpoint():
    """Test the tenders endpoint."""
    response = client.get("/api/v1/tenders")
    assert response.status_code == 200
    data = response.json()
    assert "tenders" in data
    assert "total" in data


def test_awards_search_endpoint():
    """Test the awards search endpoint."""
    response = client.get("/api/v1/awards/search?query=construction")
    assert response.status_code == 200
    data = response.json()
    assert "awards" in data
    assert "total" in data 