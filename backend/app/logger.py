"""
Logging and Crash Diagnostic Subsystem for Voice Impersonation Defense.
Provides centralized, rotating file logs for:
  - app.log      : Standard application lifecycle and API events
  - error.log    : Crashes, unhandled exceptions, and error stack traces
  - analysis.log : High-resolution audio DSP and ML risk analysis metrics
"""

import os
import sys
import logging
import traceback
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional

# Resolve backend log directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

APP_LOG_FILE = os.path.join(LOGS_DIR, "app.log")
ERROR_LOG_FILE = os.path.join(LOGS_DIR, "error.log")
ANALYSIS_LOG_FILE = os.path.join(LOGS_DIR, "analysis.log")

# Formatters
DETAILED_FORMAT = (
    "%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s"
)
CONSOLE_FORMAT = (
    "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
ANALYSIS_FORMAT = (
    "%(asctime)s %(message)s"
)

# Global flag to avoid multiple initializations
_LOGGING_INITIALIZED = False


def setup_logging(log_level: str = "INFO"):
    """
    Initializes root, application, error, and analysis loggers with rotating file handlers.
    Max file size: 10MB each, up to 5 backups.
    """
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Base formatter
    formatter = logging.Formatter(DETAILED_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    console_formatter = logging.Formatter(CONSOLE_FORMAT, datefmt="%H:%M:%S")

    # 1. Main App Rotating File Handler (app.log) - 10MB x 5 backups
    app_file_handler = RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    app_file_handler.setLevel(numeric_level)
    app_file_handler.setFormatter(formatter)

    # 2. Error / Crash Rotating File Handler (error.log) - Captures WARNING & ERROR
    error_file_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.WARNING)
    error_file_handler.setFormatter(formatter)

    # 3. Console Stream Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)

    # Configure Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(error_file_handler)
    root_logger.addHandler(console_handler)

    # Configure Analysis Logger (analysis.log)
    analysis_formatter = logging.Formatter(ANALYSIS_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    analysis_file_handler = RotatingFileHandler(
        ANALYSIS_LOG_FILE,
        maxBytes=15 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    analysis_file_handler.setLevel(logging.INFO)
    analysis_file_handler.setFormatter(analysis_formatter)

    analysis_logger = logging.getLogger("voice_defense.analysis")
    analysis_logger.setLevel(logging.INFO)
    analysis_logger.propagate = False
    analysis_logger.handlers = []
    analysis_logger.addHandler(analysis_file_handler)

    # Intercept Uvicorn loggers so server events go to app.log / error.log
    for uvi_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        uvi_logger = logging.getLogger(uvi_logger_name)
        uvi_logger.handlers = []
        uvi_logger.addHandler(app_file_handler)
        uvi_logger.addHandler(error_file_handler)
        uvi_logger.addHandler(console_handler)
        uvi_logger.propagate = False

    _LOGGING_INITIALIZED = True
    logging.getLogger("voice_defense").info(
        "Logging initialized. Log files created at: %s", LOGS_DIR
    )


# Module-level logger getters
def get_logger(name: str = "voice_defense") -> logging.Logger:
    """Returns application logger."""
    if not _LOGGING_INITIALIZED:
        setup_logging()
    return logging.getLogger(name)


def get_analysis_logger() -> logging.Logger:
    """Returns dedicated audio analysis logger."""
    if not _LOGGING_INITIALIZED:
        setup_logging()
    return logging.getLogger("voice_defense.analysis")


def log_analysis_chunk(
    session_id: str,
    chunk_index: int,
    chunk_risk: float,
    rolling_risk: float,
    model_score: float,
    lfcc_score: float,
    pitch_variance: float,
    jitter: float,
    spectral_flatness: float,
    status_color: str,
    severity: str,
    alert_fired: bool,
    latency_ms: Optional[float] = None
):
    """
    Logs structured telemetry line to analysis.log for offline inspection and risk auditing.
    """
    ana_logger = get_analysis_logger()
    latency_str = f" | Latency={latency_ms:.1f}ms" if latency_ms is not None else ""
    ana_logger.info(
        f"[SESSION:{session_id}] Chunk #{chunk_index:03d} | Risk={rolling_risk:5.1f}% (raw={chunk_risk:5.1f}%) "
        f"| Model={model_score:5.1f}% | LFCC={lfcc_score:5.1f}% | PitchVar={pitch_variance:6.1f} | Jitter={jitter:5.3f} "
        f"| SpecFlat={spectral_flatness:5.3f} | Status={status_color.upper()} | Severity={severity} | Alert={alert_fired}{latency_str}"
    )


def log_crash(
    error: Exception,
    context: str = "Application Unhandled Exception",
    extra_details: Optional[Dict[str, Any]] = None
):
    """
    Logs comprehensive crash report to error.log with full traceback and contextual metadata.
    """
    logger = get_logger("voice_defense.crash")
    details_str = f" Context: {context}"
    if extra_details:
        details_str += f" | Details: {extra_details}"
    
    tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
    tb_str = "".join(tb_lines)
    
    logger.error(
        f"CRASH / EXCEPTION DETECTED:\n"
        f"================================================================================\n"
        f"{details_str}\n"
        f"Exception Type: {type(error).__name__}\n"
        f"Exception Message: {str(error)}\n"
        f"Traceback:\n{tb_str}"
        f"================================================================================"
    )

