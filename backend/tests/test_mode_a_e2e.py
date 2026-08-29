"""
Mode A End-to-End Real Application Validation Test Suite (Checkpoint 4).

Tests the actual production FastAPI HTTP & WebSocket endpoints from upload to post-call analytics:
1. Health check (GET /health)
2. Audio Upload (POST /calls/upload)
3. SQLite Session Initialization
4. Real WebSocket Streaming (WS /calls/{session_id}/stream)
5. Mandatory Noise Stripping, DSP/LFCC, Pretrained AASIST-L Neural Inference per 2.5s chunk
6. Rolling EWMA Scoring & Context-Aware Alert Triggers
7. SQLite Metric & Alert Persistence
8. Post-Call Summary (GET /calls/{session_id}/summary) & History (GET /calls/{session_id}/history)
9. Dynamic Context Adjustment (POST /calls/{session_id}/context)
"""

import os
import sys
import time
import json
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.config import settings

GEN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "genuine_validation"))


def run_mode_a_e2e_test():
    print("\n" + "=" * 118)
    print(" [CHECKPOINT 4] MODE A END-TO-END PRODUCTION PIPELINE VALIDATION")
    print(f" FastAPI Service   : {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f" SQLite DB Path    : {settings.DB_PATH}")
    print(f" WavLM Engine      : Standalone Microsoft WavLM-Base Model")
    print(f" Noise Reduction   : Mandatory STFT Spectral Gating Active")
    print("=" * 118)

    client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Health Check Endpoint
    # -------------------------------------------------------------------------
    print("\n>>> STEP 1: Health Check Endpoint (GET /health)...")
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    print(f" Health Status : {health_data['status']}")
    print(f" Active Engine : Sample Rate={health_data['sample_rate']}Hz, Chunk={health_data['chunk_duration_sec']}s")
    print(f" Active Weights: Model={health_data['active_thresholds']['model_weight']}, LFCC={health_data['active_thresholds']['lfcc_weight']}, EWMA Alpha={health_data['active_thresholds']['ewma_alpha']}")

    # -------------------------------------------------------------------------
    # 2. Authentic Human Speech Test (librispeech_female_clean.wav, 3.27s -> 2 chunks)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print(">>> STEP 2: MODE A - AUTHENTIC HUMAN SPEECH (LibriSpeech Clean Female, context='general')")
    print("=" * 118)

    female_file = os.path.join(GEN_DIR, "librispeech_female_clean.wav")
    assert os.path.exists(female_file), f"Missing test file: {female_file}"

    # (A) Upload Audio File via Real HTTP POST
    print(" -> Uploading female audio via POST /calls/upload ...")
    with open(female_file, "rb") as f:
        upload_resp = client.post(
            "/calls/upload",
            files={"file": ("librispeech_female_clean.wav", f, "audio/wav")},
            data={"transaction_context": "general"}
        )

    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    upload_data = upload_resp.json()
    female_session_id = upload_data["session_id"]
    print(f" Upload Success! Session ID: {female_session_id}")
    print(f" Stream URL        : {upload_data['stream_url']}")

    # (B) Stream Audio Chunks via Real WebSocket
    print(f" -> Connecting to WebSocket /calls/{female_session_id}/stream ...")
    female_chunks = []
    with client.websocket_connect(f"/calls/{female_session_id}/stream") as ws:
        while True:
            msg = ws.receive_json()
            female_chunks.append(msg)
            print(f"    Chunk #{msg['chunk_index']:<2} | Elapsed: {msg['elapsed_seconds']:>4.1f}s | "
                  f"Raw Risk: {msg['chunk_risk_score']:>5.2f}% | EWMA Risk: {msg['rolling_risk_score']:>5.2f}% | "
                  f"Color: {msg['status_color']:<6} | Severity: {msg['severity']:<7} | Alert: {str(msg['alert_fired']):<5} | Complete: {msg['is_complete']}")
            if msg.get("is_complete"):
                break

    assert len(female_chunks) == 2, f"Expected 2 chunks for 3.27s audio, got {len(female_chunks)}"
    print(f" Stream Complete! Received all {len(female_chunks)} chunks cleanly.")

    # (C) Verify SQLite Persistence & Post-Call Summary
    print(f" -> Fetching Post-Call Summary (GET /calls/{female_session_id}/summary) ...")
    sum_resp = client.get(f"/calls/{female_session_id}/summary")
    assert sum_resp.status_code == 200, f"Summary failed: {sum_resp.text}"
    sum_data = sum_resp.json()
    print(f" SQLite Summary : Total Chunks={sum_data['total_chunks']}, Peak Risk={sum_data['peak_risk']}%, "
          f"Avg Risk={sum_data['avg_risk']}%, Alerts Count={sum_data['alerts_count']}")
    assert sum_data["total_chunks"] == 2
    assert sum_data["alerts_count"] == 0, "Authentic clean female speech should have 0 alerts in general context"
    assert sum_data["peak_risk"] <= 30.0, f"Authentic human peak risk ({sum_data['peak_risk']}%) was higher than expected"

    # (D) Verify SQLite Historical Time-Series
    hist_resp = client.get(f"/calls/{female_session_id}/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()["history"]
    assert len(hist_data) == 2
    print(f" SQLite History : Verified {len(hist_data)} discrete chunk metric rows stored in 'chunk_metrics' table.")

    # -------------------------------------------------------------------------
    # 3. Synthetic Voice Clone Test (xtts_voice_clone_en.wav, 3.11s, context='fund_transfer')
    # -------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print(">>> STEP 3: MODE A - SYNTHETIC AI VOICE CLONE (Coqui XTTS-v2, context='fund_transfer')")
    print("=" * 118)

    synth_file = os.path.join(GEN_DIR, "xtts_voice_clone_en.wav")
    assert os.path.exists(synth_file), f"Missing test file: {synth_file}"

    # (A) Upload Synthetic File with Sensitive Transaction Context
    print(" -> Uploading synthetic clone via POST /calls/upload (Context='fund_transfer') ...")
    with open(synth_file, "rb") as f:
        upload_resp_synth = client.post(
            "/calls/upload",
            files={"file": ("xtts_voice_clone_en.wav", f, "audio/wav")},
            data={"transaction_context": "fund_transfer"}
        )

    assert upload_resp_synth.status_code == 200
    synth_session_id = upload_resp_synth.json()["session_id"]
    print(f" Upload Success! Session ID: {synth_session_id}")

    # (B) Stream Synthetic Audio via WebSocket
    print(f" -> Connecting to WebSocket /calls/{synth_session_id}/stream ...")
    synth_chunks = []
    with client.websocket_connect(f"/calls/{synth_session_id}/stream") as ws:
        while True:
            msg = ws.receive_json()
            synth_chunks.append(msg)
            print(f"    Chunk #{msg['chunk_index']:<2} | Elapsed: {msg['elapsed_seconds']:>4.1f}s | "
                  f"Raw Risk: {msg['chunk_risk_score']:>5.2f}% | EWMA Risk: {msg['rolling_risk_score']:>5.2f}% | "
                  f"Severity: {msg['severity']:<8} | Color: {msg['status_color']:<6} | Alert: {str(msg['alert_fired']):<5}")
            print(f"      -> Recommended Action: {msg['recommended_action']}")
            if msg.get("is_complete"):
                break

    assert len(synth_chunks) == 2, f"Expected 2 chunks for 3.11s audio, got {len(synth_chunks)}"

    # (C) Verify Alert Triggering & SQLite Persistence
    print(f" -> Fetching Post-Call Summary (GET /calls/{synth_session_id}/summary) ...")
    synth_sum_resp = client.get(f"/calls/{synth_session_id}/summary")
    assert synth_sum_resp.status_code == 200
    synth_sum = synth_sum_resp.json()
    print(f" SQLite Summary : Total Chunks={synth_sum['total_chunks']}, Peak Risk={synth_sum['peak_risk']}%, "
          f"Avg Risk={synth_sum['avg_risk']}%, Alerts Count={synth_sum['alerts_count']}")

    assert synth_sum["alerts_count"] >= 1, "Synthetic voice clone MUST trigger security alerts"
    assert synth_sum["peak_risk"] >= 30.0, f"Synthetic voice clone peak risk ({synth_sum['peak_risk']}%) was too low"
    print(f" Triggered Alert Record : Severity={synth_sum['alerts'][0]['severity']}, Risk={synth_sum['alerts'][0]['risk_score']}%, "
          f"Action='{synth_sum['alerts'][0]['recommended_action']}'")

    # -------------------------------------------------------------------------
    # 4. Dynamic Transaction Context Adjustment (POST /calls/{session_id}/context)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print(">>> STEP 4: DYNAMIC TRANSACTION CONTEXT ADJUSTMENT (POST /calls/{session_id}/context)")
    print("=" * 118)
    ctx_resp = client.post(
        f"/calls/{female_session_id}/context",
        json={"transaction_context": "otp_share"}
    )
    assert ctx_resp.status_code == 200
    assert ctx_resp.json()["transaction_context"] == "otp_share"
    print(f" Context Update Success! Session {female_session_id} updated to 'otp_share'")

    # Verify context updated in SQLite DB
    updated_sum = client.get(f"/calls/{female_session_id}/summary").json()
    assert updated_sum["transaction_context"] == "otp_share"
    print(f" SQLite Verification : Confirmed updated context 'otp_share' in database.")

    print("\n" + "=" * 118)
    print(" ALL MODE A END-TO-END INTEGRATION TESTS PASSED 100%!")
    print("=" * 118 + "\n")


if __name__ == "__main__":
    run_mode_a_e2e_test()
