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
    HIGH_RISK_MIN: float = 70.0

    # EWMA smoothing factor (alpha)
    # Higher alpha = more responsive to new chunk; Lower alpha = smoother
    EWMA_ALPHA: float = 0.35

    # Feature weights in chunk risk blend (must sum to ~1.0)
    # LFCC is heavily weighted as the primary discriminative high-frequency artifact detector
    WEIGHT_MODEL: float = 0.40       # Pretrained synthetic speech detector confidence
    WEIGHT_LFCC: float = 0.30        # LFCC high-frequency artifact score
    WEIGHT_PITCH_JITTER: float = 0.15 # Pitch flatness and cycle jitter anomaly
    WEIGHT_SPECTRAL: float = 0.15    # Spectral flatness & centroid distribution

    # Transaction context sensitivity offsets
    # Reduces threshold for triggering warnings in sensitive financial / security transactions
    CONTEXT_THRESHOLD_OFFSETS: Dict[str, float] = {
        "general": 0.0,            # Standard threshold (~70.0)
        "credential_reset": -10.0, # Triggers warning at ~60.0
        "otp_share": -20.0,        # Triggers warning at ~50.0
        "fund_transfer": -25.0,    # Triggers warning at ~45.0
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

