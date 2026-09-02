"""
REST Endpoints for System Tuning, Model Weights, Risk Thresholds, and DSP Health Self-Tests.
"""

import time
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.config import settings, ScoringConfig
from app.logger import get_logger, log_crash
from app.db import save_persisted_config
from app.dsp.preprocessor import strip_background_noise
from app.dsp.lfcc import compute_lfcc, analyze_lfcc_high_freq_artifacts
from app.dsp.features import extract_all_dsp_features
from app.scoring.engine import scoring_engine

router = APIRouter(prefix="/settings", tags=["Settings"])
logger = get_logger("voice_defense.settings")


class UpdateSettingsRequest(BaseModel):
    low_risk_max: Optional[float] = Field(None, ge=10.0, le=90.0)
    high_risk_min: Optional[float] = Field(None, ge=20.0, le=100.0)
    ewma_alpha: Optional[float] = Field(None, ge=0.05, le=1.0)
    weight_model: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_lfcc: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_pitch_jitter: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_spectral: Optional[float] = Field(None, ge=0.0, le=1.0)
    enable_noise_reduction: Optional[bool] = None
    context_offsets: Optional[Dict[str, float]] = None


@router.get("")
async def get_current_settings():
    """
    Returns complete active configuration, thresholds, feature weights, and audio parameters.
    """
    return {
        "status": "success",
        "scoring": {
            "low_risk_max": settings.SCORING.LOW_RISK_MAX,
            "medium_risk_max": settings.SCORING.MEDIUM_RISK_MAX,
            "high_risk_min": settings.SCORING.HIGH_RISK_MIN,
            "ewma_alpha": settings.SCORING.EWMA_ALPHA,
            "weights": {
                "model": settings.SCORING.WEIGHT_MODEL,
                "lfcc": settings.SCORING.WEIGHT_LFCC,
                "pitch_jitter": settings.SCORING.WEIGHT_PITCH_JITTER,
                "spectral": settings.SCORING.WEIGHT_SPECTRAL,
            },
            "context_offsets": settings.SCORING.CONTEXT_THRESHOLD_OFFSETS,
            "recommended_actions": settings.SCORING.RECOMMENDED_ACTIONS
        },
        "audio": {
            "sample_rate": settings.AUDIO.SAMPLE_RATE,
            "chunk_duration_sec": settings.AUDIO.CHUNK_DURATION_SEC,
            "chunk_samples": settings.AUDIO.CHUNK_SAMPLES,
            "n_fft": settings.AUDIO.N_FFT,
            "hop_length": settings.AUDIO.HOP_LENGTH,
            "n_lfcc": settings.AUDIO.N_LFCC,
            "n_filterbanks": settings.AUDIO.N_FILTERBANKS
        },
        "system": {
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "enable_noise_reduction": settings.ENABLE_NOISE_REDUCTION,
            "use_calibrated_scoring": settings.USE_CALIBRATED_SCORING,
            "log_level": settings.LOG_LEVEL
        }
    }


@router.put("")
async def update_settings(req: UpdateSettingsRequest):
    """
    Updates runtime settings and persists them into the SQLite database.
    """
    try:
        updated_dict = {}

        if req.low_risk_max is not None:
            settings.SCORING.LOW_RISK_MAX = float(req.low_risk_max)
            updated_dict["low_risk_max"] = req.low_risk_max

        if req.high_risk_min is not None:
            settings.SCORING.HIGH_RISK_MIN = float(req.high_risk_min)
            settings.SCORING.MEDIUM_RISK_MAX = float(req.high_risk_min)
            updated_dict["high_risk_min"] = req.high_risk_min

        if req.ewma_alpha is not None:
            settings.SCORING.EWMA_ALPHA = float(req.ewma_alpha)
            updated_dict["ewma_alpha"] = req.ewma_alpha

        if req.weight_model is not None:
            settings.SCORING.WEIGHT_MODEL = float(req.weight_model)
            updated_dict["weight_model"] = req.weight_model

        if req.weight_lfcc is not None:
            settings.SCORING.WEIGHT_LFCC = float(req.weight_lfcc)
            updated_dict["weight_lfcc"] = req.weight_lfcc

        if req.weight_pitch_jitter is not None:
            settings.SCORING.WEIGHT_PITCH_JITTER = float(req.weight_pitch_jitter)
            updated_dict["weight_pitch_jitter"] = req.weight_pitch_jitter

        if req.weight_spectral is not None:
            settings.SCORING.WEIGHT_SPECTRAL = float(req.weight_spectral)
            updated_dict["weight_spectral"] = req.weight_spectral

        if req.enable_noise_reduction is not None:
            settings.ENABLE_NOISE_REDUCTION = bool(req.enable_noise_reduction)
            updated_dict["enable_noise_reduction"] = req.enable_noise_reduction

        if req.context_offsets is not None:
            settings.SCORING.CONTEXT_THRESHOLD_OFFSETS.update(req.context_offsets)
            updated_dict["context_offsets"] = settings.SCORING.CONTEXT_THRESHOLD_OFFSETS

        # Persist to database
        save_persisted_config(updated_dict)
        logger.info("System settings updated & saved successfully: %s", updated_dict)

        return {
            "status": "success",
            "message": "Settings updated and saved successfully",
            "updated": updated_dict
        }
    except Exception as e:
        log_crash(e, context="Update Settings Endpoint", extra_details=req.model_dump())
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.post("/reset")
async def reset_settings():
    """
    Resets settings to hardcoded factory defaults.
    """
    try:
        settings.SCORING = ScoringConfig()
        settings.ENABLE_NOISE_REDUCTION = True
        save_persisted_config({
            "low_risk_max": 40.0,
            "high_risk_min": 70.0,
            "ewma_alpha": 0.35,
            "weight_model": 0.40,
            "weight_lfcc": 0.30,
            "weight_pitch_jitter": 0.15,
            "weight_spectral": 0.15,
            "enable_noise_reduction": True,
            "context_offsets": {
                "general": 0.0,
                "credential_reset": -10.0,
                "otp_share": -20.0,
                "fund_transfer": -25.0
            }
        })
        logger.info("Settings reset to factory defaults")
        return {
            "status": "success",
            "message": "Settings have been reset to factory defaults"
        }
    except Exception as e:
        log_crash(e, context="Reset Settings Endpoint")
        raise HTTPException(status_code=500, detail=f"Failed to reset settings: {str(e)}")


@router.post("/test-pipeline")
async def test_dsp_pipeline():
    """
    Runs a fast synthetic acoustic test chunk through the DSP & Feature Extraction pipeline
    to benchmark execution latency and verify sensor health.
    """
    try:
        start_time = time.perf_counter()
        
        # 1. Generate 2.5s simulated synthetic audio chunk (16kHz, 40000 samples)
        sr = 16000
        duration = 2.5
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        # 220Hz harmonic tone + robotic overtone simulation
        test_audio = 0.5 * np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.normal(0, 0.05, len(t))

        # 2. Preprocess & Noise Reduction
        clean_audio = test_audio
        stripped = False
        if settings.ENABLE_NOISE_REDUCTION:
            clean_audio, noise_meta = strip_background_noise(test_audio, sr=sr)
            stripped = noise_meta.get("noise_stripped", False)

        # 3. LFCC Feature Extraction
        lfcc_mat, log_fb = compute_lfcc(
            clean_audio,
            sr=sr,
            n_lfcc=settings.AUDIO.N_LFCC,
            n_filters=settings.AUDIO.N_FILTERBANKS,
            n_fft=settings.AUDIO.N_FFT,
            hop_length=settings.AUDIO.HOP_LENGTH
        )
        lfcc_analysis = analyze_lfcc_high_freq_artifacts(lfcc_mat, log_fb, n_filters=settings.AUDIO.N_FILTERBANKS)
        lfcc_score = lfcc_analysis["lfcc_artifact_score"]

        # 4. Acoustic Features
        dsp_features = extract_all_dsp_features(
            clean_audio,
            sr=sr,
            n_fft=settings.AUDIO.N_FFT,
            hop_length=settings.AUDIO.HOP_LENGTH
        )

        # 5. Composite Risk Score
        pitch_score = dsp_features.get("pitch_anomaly_score", 0.0)
        spec_score = dsp_features.get("spectral_anomaly_score", 0.0)
        dummy_model_score = 45.0
        
        composite_score = scoring_engine.compute_chunk_risk_score(
            model_score=dummy_model_score,
            lfcc_artifact_score=lfcc_score,
            pitch_anomaly_score=pitch_score,
            spectral_anomaly_score=spec_score
        )

        total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return {
            "status": "success",
            "pipeline_healthy": True,
            "latency_ms": total_latency_ms,
            "target_latency_budget_ms": 50.0,
            "metrics": {
                "noise_reduction_applied": stripped,
                "lfcc_artifact_score": round(float(lfcc_score), 2),
                "pitch_mean_hz": round(float(dsp_features.get("pitch_mean", 0.0)), 2),
                "pitch_variance": round(float(dsp_features.get("pitch_variance", 0.0)), 2),
                "jitter": round(float(dsp_features.get("jitter", 0.0)), 4),
                "spectral_flatness": round(float(dsp_features.get("spectral_flatness", 0.0)), 4),
                "spectral_centroid_hz": round(float(dsp_features.get("spectral_centroid", 0.0)), 2),
                "silence_ratio": round(float(dsp_features.get("silence_ratio", 0.0)), 3),
                "computed_composite_risk": composite_score
            }
        }
    except Exception as e:
        log_crash(e, context="Test Pipeline Endpoint")
        raise HTTPException(status_code=500, detail=f"Pipeline self-test failed: {str(e)}")
