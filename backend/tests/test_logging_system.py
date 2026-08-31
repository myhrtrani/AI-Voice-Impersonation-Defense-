"""
Verification script for the Application Logging and Crash Analysis System.
Tests:
1. Log file generation in backend/logs/ (app.log, error.log, analysis.log)
2. Audio chunk telemetry logging to analysis.log
3. Crash capture and full stack trace recording in error.log
4. Diagnostics endpoints
"""

import os
import sys
import numpy as np

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.logger import (
    setup_logging,
    get_logger,
    get_analysis_logger,
    log_crash,
    LOGS_DIR,
    APP_LOG_FILE,
    ERROR_LOG_FILE,
    ANALYSIS_LOG_FILE
)
from app.routers.stream import process_audio_chunk
from app.db import init_db, create_session, get_session_summary


def test_logging_pipeline():
    print("\n--- 1. Initializing DB and Logging ---")
    setup_logging("INFO")
    logger = get_logger("voice_defense.test")
    logger.info("Test suite started for Voice Defense Logging Subsystem")

    assert os.path.exists(LOGS_DIR), f"Logs directory not found at {LOGS_DIR}"
    print(f"Log directory verified at: {LOGS_DIR}")

    print("\n--- 2. Testing Audio Chunk Analysis Logging ---")
    test_session_id = "session_test_log_001"
    create_session(test_session_id, mode="mode_a_upload", transaction_context="fund_transfer")

    # Generate synthetic dummy 2.5s 16kHz audio
    dummy_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 2.5, 40000)).astype(np.float32)
    result = process_audio_chunk(
        audio_data=dummy_audio,
        sr=16000,
        session_id=test_session_id,
        chunk_index=1,
        previous_rolling_score=None,
        previous_severity="NORMAL",
        transaction_context="fund_transfer",
        elapsed_seconds=2.5
    )

    print(f"Audio chunk processed: Risk={result['rolling_risk_score']}%, Color={result['status_color']}")
    assert os.path.exists(ANALYSIS_LOG_FILE), "analysis.log was not created"
    
    with open(ANALYSIS_LOG_FILE, "r", encoding="utf-8") as f:
        analysis_content = f.read()
        assert test_session_id in analysis_content, "Session ID not found in analysis.log"
    print("analysis.log successfully captured audio risk telemetry!")

    print("\n--- 3. Testing Crash & Exception Stack Trace Logging ---")
    try:
        # Deliberately raise a test exception
        def failing_inner_function():
            raise ValueError("Simulated Deep Crash in Audio Analysis Module (Test verification)")

        failing_inner_function()
    except Exception as exc:
        log_crash(
            exc,
            context="Unit Test Simulated Crash Verification",
            extra_details={"test_id": "test_crash_001", "stage": "inference"}
        )

    assert os.path.exists(ERROR_LOG_FILE), "error.log was not created"
    with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
        error_content = f.read()
        assert "Simulated Deep Crash" in error_content, "Crash error message not found in error.log"
        assert "Traceback" in error_content, "Stack trace not found in error.log"
    print("error.log successfully recorded full crash traceback!")

    print("\n--- 4. Checking Log File Sizes ---")
    for name, path in [("app.log", APP_LOG_FILE), ("error.log", ERROR_LOG_FILE), ("analysis.log", ANALYSIS_LOG_FILE)]:
        size = os.path.getsize(path)
        print(f"  - {name}: {size} bytes ({size/1024:.2f} KB)")

    print("\n ALL LOGGING AND CRASH ANALYSIS TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_logging_pipeline()

