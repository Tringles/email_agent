"""Health check API tests."""

import pytest

from datetime import datetime
from fastapi.testclient import TestClient


class TestHealthAPI:
    """Health check endpoint tests."""
    
    def test_health_check(self, client: TestClient):
        """Test basic health check endpoint."""
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(data["timestamp"])
    
    def test_readiness_check(self, client: TestClient):
        """Test readiness check endpoint."""
        response = client.get("/api/v1/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data
        datetime.fromisoformat(data["timestamp"])

