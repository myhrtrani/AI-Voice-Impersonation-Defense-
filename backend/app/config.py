"""
Configuration and Threshold Settings for Voice Impersonation Risk Detector.
All thresholds and weights are centralized here and configurable per environment.
"""

from pydantic import BaseModel
from typing import Dict, Any


class ScoringConfig(BaseModel):
    # Base risk thresholds (0 - 100)
    LOW_RISK_MAX: float = 40.0
    MEDIUM_RISK_MAX: float = 70.0
    HIGH_RISK_MIN: float = 60.0

    # EWMA smoothing factor (alpha)
    # Higher alpha = more responsive to new chunk; Lower alpha = smoother
    EWMA_ALPHA: float = 0.85

    # Feature weights in chunk risk blend (must sum to ~1.0)
    # Model and LFCC are the primary synthetic detectors and need enough weight
    # to push realistic deepfakes (which have perfect human pitch) over the 60% threshold.
    WEIGHT_MODEL: float = 0.25       # Pretrained synthetic speech detector confidence
    WEIGHT_LFCC: float = 0.25        # LFCC high-frequency artifact score
    WEIGHT_PITCH_JITTER: float = 0.30 # Pitch flatness and cycle jitter anomaly
    WEIGHT_SPECTRAL: float = 0.20    # Spectral flatness & centroid distribution

    CONTEXT_THRESHOLD_OFFSETS: Dict[str, float] = {
        "general": 0.0,            # CRITICAL at 60.0%
        "credential_reset": 0.0,   # CRITICAL at 60.0%
        "otp_share": 0.0,          # CRITICAL at 60.0%
        "fund_transfer": 0.0,      # CRITICAL at 60.0%
    }

    # WARNING threshold offsets (LOW_RISK_MAX + offset) — kept context-specific
    CONTEXT_WARNING_OFFSETS: Dict[str, float] = {
        "general": 15.0,            # WARNING at 55.0%
        "credential_reset": -10.0, # WARNING at 30.0%
        "otp_share": -20.0,        # WARNING at 20.0%
        "fund_transfer": -25.0,    # WARNING at 20.0% (clamped by max(20.0, ...))
    }

    # Recommended action text mapped by severity & context
    RECOMMENDED_ACTIONS: Dict[str, Dict[str, str]] = {
        "CRITICAL": {
            "fund_transfer": "CRITICAL RISK: Synthetic voice detected. Immediately halt transaction and initiate callback verification.",
            "otp_share": "CRITICAL RISK: High probability AI voice clone. DO NOT disclose OTP or 2FA codes.",
            "credential_reset": "CRITICAL RISK: Impersonation risk detected. Require in-person or out-of-band identity check.",
            "general": "CRITICAL ALERT: Synthetic speech detected. Exercise extreme caution and verify caller identity."
        },
        "WARNING": {
            "fund_transfer": "WARNING: Elevated synthetic speech indicators. Verify caller identity before approving funds.",
            "otp_share": "WARNING: Acoustic anomalies detected. Confirm caller legitimacy before reading security codes.",
            "credential_reset": "WARNING: Pitch and spectral artifacts detected. Apply step-up authentication.",
            "general": "WARNING: Suspicious audio characteristics detected."
        },
        "NORMAL": {
            "default": "Audio characteristics match natural human speech patterns."
        }
    }


class AudioConfig(BaseModel):
    SAMPLE_RATE: int = 16000
    CHUNK_DURATION_SEC: float = 2.5   # Chunk window size in seconds
    CHUNK_SAMPLES: int = int(16000 * 2.5) # 40,000 samples
    N_FFT: int = 512
    HOP_LENGTH: int = 160             # 10ms frame hop at 16kHz
    N_LFCC: int = 20                  # Number of Linear Frequency Cepstral Coefficients
    N_FILTERBANKS: int = 30           # Number of linear filterbanks
    MIN_FREQ: float = 50.0
    MAX_FREQ: float = 8000.0          # Full Nyquist for 16kHz audio


class Settings(BaseModel):
    PROJECT_NAME: str = "AI Voice Impersonation Risk Detector"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/calls"
    DB_PATH: str = "voice_detector.db"
    LOG_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"
    ENABLE_NOISE_REDUCTION: bool = True
    # Feature flag to enable calibrated logistic fusion (mean aggregation)
    USE_CALIBRATED_SCORING: bool = False
    # Path to persisted calibrator (joblib) used when USE_CALIBRATED_SCORING is True
    CALIBRATOR_PATH: str = "models/calibrator.joblib"
    SCORING: ScoringConfig = ScoringConfig()
    AUDIO: AudioConfig = AudioConfig()


settings = Settings()

# Supported languages for multilingual detection
SUPPORTED_LANGUAGES = ["english", "hindi", "malayalam"]

# Language-specific pitch thresholds for prosody-aware anomaly detection.
# Hindi and Malayalam have wider natural pitch ranges than English.
LANGUAGE_PITCH_CONFIG = {
    "english":   {"pitch_std_threshold": 8.0,  "fmin": 65.0, "fmax": 400.0},
    "hindi":     {"pitch_std_threshold": 10.0, "fmin": 60.0, "fmax": 450.0},
    "malayalam": {"pitch_std_threshold": 10.0, "fmin": 60.0, "fmax": 450.0},
}

