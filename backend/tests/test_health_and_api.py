"""
FastAPI Health Check and Endpoint Unit Tests.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["noise_reduction_enabled"] is True
    assert "active_thresholds" in data
    assert data["active_thresholds"]["lfcc_weight"] == 0.30


def test_start_live_endpoint():
    response = client.post("/calls/start-live", json={"transaction_context": "otp_share"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["mode"] == "mode_b_live"
    assert data["transaction_context"] == "otp_share"
    assert "session_id" in data
    assert len(data["ice_servers"]) > 0


def test_context_update():
    # Start session first
    start_resp = client.post("/calls/start-live", json={"transaction_context": "general"})
    session_id = start_resp.json()["session_id"]
    
    # Update context
    up_resp = client.post(f"/calls/{session_id}/context", json={"transaction_context": "fund_transfer"})
    assert up_resp.status_code == 200
    assert up_resp.json()["transaction_context"] == "fund_transfer"
    
    # Verify summary reflects updated context
    sum_resp = client.get(f"/calls/{session_id}/summary")
    assert sum_resp.status_code == 200
    assert sum_resp.json()["transaction_context"] == "fund_transfer"
