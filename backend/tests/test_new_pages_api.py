"""
Unit and Integration Tests for Analytics, Settings, and Localization APIs.
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db import create_session, record_chunk_metric, record_alert, delete_session


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_thresholds" in data


def test_analytics_overview(client):
    # Seed a dummy session
    session_id = "test_analytics_session_1"
    create_session(session_id, mode="mode_a_upload", transaction_context="fund_transfer")
    record_chunk_metric(session_id, {
        "chunk_index": 0,
        "chunk_risk_score": 85.0,
        "rolling_risk_score": 85.0,
        "model_score": 80.0,
        "lfcc_artifact_score": 75.0,
        "pitch_variance": 5.0,
        "jitter": 0.01,
        "spectral_flatness": 0.05,
        "spectral_centroid": 2500.0,
        "silence_ratio": 0.02
    })
    record_alert(session_id, {
        "chunk_index": 0,
        "severity": "CRITICAL",
        "risk_score": 85.0,
        "transaction_context": "fund_transfer",
        "recommended_action": "Halt transaction"
    })

    # Query analytics overview
    response = client.get("/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_sessions"] >= 1
    assert "context_breakdown" in data
    assert "threat_interception_rate" in data

    # Query sessions list
    resp_sessions = client.get("/analytics/sessions?limit=10")
    assert resp_sessions.status_code == 200
    sess_data = resp_sessions.json()
    assert sess_data["status"] == "success"
    assert len(sess_data["sessions"]) >= 1

    # Cleanup
    delete_session(session_id)


def test_settings_api(client):
    # 1. Get Settings
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert "scoring" in data
    assert "audio" in data
    assert "system" in data

    # 2. Update Settings
    update_payload = {
        "low_risk_max": 35.0,
        "high_risk_min": 75.0,
        "ewma_alpha": 0.40,
        "weight_lfcc": 0.35,
        "enable_noise_reduction": True
    }
    resp_update = client.put("/settings", json=update_payload)
    assert resp_update.status_code == 200
    updated_data = resp_update.json()
    assert updated_data["status"] == "success"
    assert updated_data["updated"]["low_risk_max"] == 35.0

    # 3. Test DSP Pipeline self-test
    resp_test = client.post("/settings/test-pipeline")
    assert resp_test.status_code == 200
    test_data = resp_test.json()
    assert test_data["status"] == "success"
    assert test_data["pipeline_healthy"] is True
    assert "latency_ms" in test_data
    assert "metrics" in test_data

    # 4. Reset Settings
    resp_reset = client.post("/settings/reset")
    assert resp_reset.status_code == 200
    reset_data = resp_reset.json()
    assert reset_data["status"] == "success"


def test_localization_api(client):
    # 1. Get Languages
    response = client.get("/localization/languages")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["languages"]) >= 5
    assert "acoustic_profiles" in data

    # 2. Set Preference
    pref_payload = {
        "language": "es",
        "acoustic_profile": "syllable_timed"
    }
    resp_pref = client.post("/localization/preference", json=pref_payload)
    assert resp_pref.status_code == 200
    pref_data = resp_pref.json()
    assert pref_data["status"] == "success"
    assert pref_data["saved"]["preferred_language"] == "es"
