"""
FastAPI Application Entry Point.
AI-Powered Real-Time Voice Impersonation & Synthetic-Speech Risk Detector.
"""

import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.logger import (
    setup_logging,
    get_logger,
    log_crash,
    LOGS_DIR,
    APP_LOG_FILE,
    ERROR_LOG_FILE,
    ANALYSIS_LOG_FILE
)
from app.db import init_db
from app.routers import calls, stream, signaling

# Initialize centralized logging immediately upon loading module
setup_logging(settings.LOG_LEVEL)
logger = get_logger("voice_defense.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and log server readiness
    logger.info("=" * 60)
    logger.info("Starting %s v%s", settings.PROJECT_NAME, settings.VERSION)
    logger.info("Logs Directory: %s", LOGS_DIR)
    logger.info("Noise Reduction Enabled: %s", settings.ENABLE_NOISE_REDUCTION)
    logger.info("Target Audio Sample Rate: %d Hz", settings.AUDIO.SAMPLE_RATE)
    logger.info("Target Chunk Size: %.1fs (%d samples)", settings.AUDIO.CHUNK_DURATION_SEC, settings.AUDIO.CHUNK_SAMPLES)
    
    try:
        init_db()
        logger.info("Database initialized successfully at: %s", settings.DB_PATH)
    except Exception as e:
        log_crash(e, context="Database Initialization on Startup")
        raise e

    yield

    # Shutdown logic
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    logger.info("=" * 60)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-Time Voice Impersonation & Synthetic-Speech Risk Detection API",
    lifespan=lifespan
)


# Global Crash & Request Logging Middleware
class CrashAndRequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Don't clutter logs for rapid polling health checks, but still catch any crash
        is_health = path == "/health"

        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            if not is_health:
                logger.info(
                    "%s %s -> %d (%s) [%.1fms]",
                    method, path, response.status_code, client_ip, duration_ms
                )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_crash(
                exc,
                context=f"HTTP Request Failure ({method} {path})",
                extra_details={
                    "client_ip": client_ip,
                    "method": method,
                    "path": path,
                    "query_params": str(request.query_params),
                    "duration_ms": round(duration_ms, 2)
                }
            )
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "message": "An internal server error occurred. Full stack trace logged to backend/logs/error.log",
                    "detail": str(exc)
                }
            )


app.add_middleware(CrashAndRequestLoggingMiddleware)

# CORS Middleware for local development and front-end integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Sub-Routers
app.include_router(calls.router)
app.include_router(stream.router)
app.include_router(signaling.router)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint verifying API readiness, scoring configuration, and log file status.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "noise_reduction_enabled": settings.ENABLE_NOISE_REDUCTION,
        "sample_rate": settings.AUDIO.SAMPLE_RATE,
        "chunk_duration_sec": settings.AUDIO.CHUNK_DURATION_SEC,
        "logs": {
            "log_dir": LOGS_DIR,
            "app_log_exists": os.path.exists(APP_LOG_FILE),
            "error_log_exists": os.path.exists(ERROR_LOG_FILE),
            "analysis_log_exists": os.path.exists(ANALYSIS_LOG_FILE),
        },
        "active_thresholds": {
            "low_max": settings.SCORING.LOW_RISK_MAX,
            "high_min": settings.SCORING.HIGH_RISK_MIN,
            "ewma_alpha": settings.SCORING.EWMA_ALPHA,
            "lfcc_weight": settings.SCORING.WEIGHT_LFCC,
            "model_weight": settings.SCORING.WEIGHT_MODEL
        }
    }


@app.get("/logs/status", tags=["Diagnostics"])
async def get_logs_status():
    """
    Diagnostics endpoint providing real-time status and sizes of all active log files.
    """
    def get_file_info(path: str):
        if os.path.exists(path):
            size_bytes = os.path.getsize(path)
            modified = time.ctime(os.path.getmtime(path))
            return {"exists": True, "size_bytes": size_bytes, "size_kb": round(size_bytes / 1024, 2), "last_modified": modified}
        return {"exists": False, "size_bytes": 0, "size_kb": 0.0, "last_modified": None}

    return {
        "log_directory": LOGS_DIR,
        "files": {
            "app_log": {"path": APP_LOG_FILE, **get_file_info(APP_LOG_FILE)},
            "error_log": {"path": ERROR_LOG_FILE, **get_file_info(ERROR_LOG_FILE)},
            "analysis_log": {"path": ANALYSIS_LOG_FILE, **get_file_info(ANALYSIS_LOG_FILE)}
        }
    }


@app.get("/logs/recent", tags=["Diagnostics"])
async def get_recent_logs(file_type: str = "app", lines: int = 50):
    """
    Retrieves the most recent N lines of a specified log file (app, error, or analysis).
    """
    target_file = APP_LOG_FILE
    if file_type == "error":
        target_file = ERROR_LOG_FILE
    elif file_type == "analysis":
        target_file = ANALYSIS_LOG_FILE

    if not os.path.exists(target_file):
        return {"file": target_file, "lines_returned": 0, "content": []}

    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            recent_lines = [line.rstrip() for line in all_lines[-max(1, min(lines, 500)):]]
        return {
            "file": target_file,
            "total_file_lines": len(all_lines),
            "lines_returned": len(recent_lines),
            "content": recent_lines
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
