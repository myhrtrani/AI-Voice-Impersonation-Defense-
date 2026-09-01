"""
Risk Scoring Engine and Non-Spamming Alert State Machine.

Blend Formula & Weighting Rationale:
------------------------------------
chunk_risk_score = (
    0.40 * model_score +
    0.30 * lfcc_artifact_score +
    0.15 * pitch_jitter_score +
    0.15 * spectral_anomaly_score
)

Why LFCC gets 30% weight:
LFCC (Linear Frequency Cepstral Coefficients) explicitly uses a linear-spaced filterbank across
the full 0 - 8000 Hz spectrum without Mel-scale compression. Neural vocoders (HiFi-GAN, WaveGlow,
ElevenLabs-style neural synthesizers) leave subtle phase discontinuities, checkerboard artifacts,
and high-frequency spectral ripple in the 4kHz - 8kHz band. LFCC is the most direct mathematical
indicator of these high-band vocoder fingerprints, making it a critical anchor alongside the ML model.

Smoothing & Anti-Spam:
- EWMA (Exponentially Weighted Moving Average, alpha=0.35) prevents transient background pops or mic clicks
  from triggering false alarms, while responding quickly to sustained synthetic speech.
- Context sensitivity offsets dynamically lower threshold for high-value targets (e.g., fund transfers & OTP shares).
- Alert state machine tracks previous severity level to prevent spamming notifications on every chunk.
"""

from typing import Dict, Any, Optional, Tuple
from app.config import settings


class RiskScoringEngine:
    def __init__(self):
        self.config = settings.SCORING

    def compute_chunk_risk_score(
        self,
        model_score: float,
        lfcc_artifact_score: float,
        pitch_anomaly_score: float,
        spectral_anomaly_score: float
    ) -> float:
        """
        Calculates blended 0.0 to 100.0 risk score for an individual chunk.
        """
        w_model = self.config.WEIGHT_MODEL
        w_lfcc = self.config.WEIGHT_LFCC
        w_pitch = self.config.WEIGHT_PITCH_JITTER
        w_spec = self.config.WEIGHT_SPECTRAL

        # Use fixed configured feature weights (data-driven fusion preferred).
        # Hand-crafted adaptive shifting of weights was removed to ensure
        # scoring behavior is driven by validation/learned calibration rather
        # than a hard-coded rule.
        w_model_eff = w_model
        w_lfcc_eff = w_lfcc

        score = (
            w_model_eff * model_score +
            w_lfcc_eff * lfcc_artifact_score +
            w_pitch * pitch_anomaly_score +
            w_spec * spectral_anomaly_score
        )
        return round(float(max(0.0, min(100.0, score))), 2)

    def update_rolling_score(
        self,
        current_chunk_score: float,
        previous_rolling_score: Optional[float]
    ) -> float:
        """
        Computes Exponentially Weighted Moving Average (EWMA).
        """
        if previous_rolling_score is None:
            return current_chunk_score

        alpha = self.config.EWMA_ALPHA
        rolling = alpha * current_chunk_score + (1.0 - alpha) * previous_rolling_score
        return round(float(max(0.0, min(100.0, rolling))), 2)

    def evaluate_alert(
        self,
        rolling_risk_score: float,
        transaction_context: str = "general",
        previous_severity: str = "NORMAL",
        base_high_risk_min: Optional[float] = None
    ) -> Tuple[bool, str, str]:
        """
        Evaluates whether an alert should fire, ensuring no alert spam.
        
        Returns:
            Tuple of (should_fire_alert, current_severity, recommended_action)
        """
        # Context-dependent sensitivity offsets (CRITICAL and WARNING use separate offsets)
        crit_offset = self.config.CONTEXT_THRESHOLD_OFFSETS.get(transaction_context, 0.0)
        warn_offset = self.config.CONTEXT_WARNING_OFFSETS.get(transaction_context, 0.0)

        # Allow optional override of the configured HIGH_RISK_MIN (used by Mode A Analysis page)
        effective_high_min = base_high_risk_min if base_high_risk_min is not None else self.config.HIGH_RISK_MIN

        # Adjusted thresholds
        crit_threshold = max(35.0, effective_high_min + crit_offset)
        warn_threshold = max(20.0, self.config.LOW_RISK_MAX + warn_offset)

        # Determine current severity
        if rolling_risk_score >= crit_threshold:
            current_severity = "CRITICAL"
        elif rolling_risk_score >= warn_threshold:
            current_severity = "WARNING"
        else:
            current_severity = "NORMAL"

        # Determine recommended action text
        actions = self.config.RECOMMENDED_ACTIONS
        if current_severity in actions:
            action_map = actions[current_severity]
            recommended_action = action_map.get(transaction_context, action_map.get("general", actions["NORMAL"]["default"]))
        else:
            recommended_action = actions["NORMAL"]["default"]

        # Anti-spam rule:
        # Fire alert only if:
        # 1. Escalated from NORMAL -> WARNING or CRITICAL
        # 2. Escalated from WARNING -> CRITICAL
        # 3. Re-entered WARNING or CRITICAL after dropping to NORMAL
        severity_ranks = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2}
        prev_rank = severity_ranks.get(previous_severity, 0)
        curr_rank = severity_ranks.get(current_severity, 0)

        should_fire = False
        if curr_rank > prev_rank:
            should_fire = True
        elif prev_rank == 0 and curr_rank > 0:
            should_fire = True

        return should_fire, current_severity, recommended_action


# Singleton scoring engine instance
scoring_engine = RiskScoringEngine()
