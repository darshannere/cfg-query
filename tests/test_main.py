"""Tests for FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_index_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_query_endpoint_returns_results(client):
    with patch("app.main.query_service") as mock_service:
        mock_service.generate_sql = AsyncMock(return_value="SELECT * FROM orders LIMIT 5")
        mock_service.execute_query = AsyncMock(return_value={
            "data": [{"order_id": "1", "total_amount": 100.0}]
        })

        response = client.post(
            "/api/query",
            json={"query": "show me 5 orders"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "sql" in data
        assert "results" in data
        assert data["sql"] == "SELECT * FROM orders LIMIT 5"
        assert len(data["results"]["data"]) == 1

def test_query_endpoint_validates_input(client):
    response = client.post("/api/query", json={})
    assert response.status_code == 422  # Validation error
