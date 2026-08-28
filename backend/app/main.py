"""
FastAPI Application Entry Point.
AI-Powered Real-Time Voice Impersonation & Synthetic-Speech Risk Detector.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.db import init_db
from app.routers import calls, stream, signaling


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB
    init_db()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-Time Voice Impersonation & Synthetic-Speech Risk Detection API",
    lifespan=lifespan
)

# CORS Middleware for local development and front-end integration
# NOTE FOR DEPLOYMENT: Replace allow_origins=["*"] with your production frontend URL (e.g., https://your-app.vercel.app)
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
    Health check endpoint verifying API readiness and scoring configuration.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "noise_reduction_enabled": settings.ENABLE_NOISE_REDUCTION,
        "sample_rate": settings.AUDIO.SAMPLE_RATE,
        "chunk_duration_sec": settings.AUDIO.CHUNK_DURATION_SEC,
        "active_thresholds": {
            "low_max": settings.SCORING.LOW_RISK_MAX,
            "high_min": settings.SCORING.HIGH_RISK_MIN,
            "ewma_alpha": settings.SCORING.EWMA_ALPHA,
            "lfcc_weight": settings.SCORING.WEIGHT_LFCC,
            "model_weight": settings.SCORING.WEIGHT_MODEL
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
