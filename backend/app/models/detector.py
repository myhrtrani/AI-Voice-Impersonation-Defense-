"""
Pretrained Synthetic Speech & Deepfake Audio Detector Module.

Production Pipeline:
--------------------
1. AASIST-L official pretrained neural detector
2. Hackathon-trained Random Forest HUMAN vs AI classifier
3. Conservative fusion:
       70% AASIST + 30% Random Forest
4. Existing scoring engine continues to handle
   WARNING / CRITICAL decisions.
"""

import os
import time
import numpy as np
import scipy.signal
import torch
from typing import Dict, Any, Tuple

from app.logger import get_logger, log_crash
from app.models.aasist import (
    AASIST_L,
    load_aasist_model,
    pad_to_aasist_length
)
from app.models.hackathon_classifier import hackathon_classifier


logger = get_logger("voice_defense.detector")


class SyntheticVoiceDetector:

    def __init__(self):
        self.model_name = (
            "NAVER Clova AASIST-L "
            "(Official Pretrained Checkpoint)"
        )

        self.weights_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "weights",
                "AASIST-L.pth"
            )
        )

        self.device = torch.device("cpu")
        self.param_count = 0
        self.file_size = 0

        try:
            self.model, self.param_count, self.file_size = (
                load_aasist_model(self.weights_path)
            )

            self.is_ready = True

            logger.info(
                "Loaded %s (%d trainable params, %.1f KB, "
                "strict=True, device=%s)",
                self.model_name,
                self.param_count,
                self.file_size / 1024,
                self.device
            )

        except Exception as e:
            log_crash(
                e,
                context="Loading AASIST-L Neural Network Weights",
                extra_details={
                    "weights_path": self.weights_path
                }
            )

            logger.error(
                "Failed to load AASIST-L weights: %s",
                e
            )

            self.model = None
            self.is_ready = False

    def infer(
        self,
        y: np.ndarray,
        sr: int = 16000
    ) -> Tuple[float, Dict[str, Any]]:

        """
        Runs AASIST-L and the hackathon-trained
        Random Forest classifier on an audio chunk.

        Returns:
            Tuple of:
            - fused model confidence score [0-100]
            - telemetry dictionary
        """

        if len(y) < int(sr * 0.2):
            return (
                0.0,
                {
                    "confidence": 0.0,
                    "reason": "Insufficient audio duration",
                    "inference_ms": 0.0
                }
            )

        t_start = time.perf_counter()

        spoof_prob = 0.0
        bonafide_prob = 1.0
        logits_raw = [0.0, 0.0]

        # ============================================================
        # 1. AASIST-L PRETRAINED DETECTOR
        # ============================================================

        if self.model is not None and self.is_ready:

            try:
                # Official AASIST-L input preparation.
                y_padded = pad_to_aasist_length(
                    y,
                    max_len=64600
                )

                tensor_input = (
                    torch.from_numpy(
                        y_padded.astype(np.float32)
                    )
                    .unsqueeze(0)
                    .to(self.device)
                )

                with torch.no_grad():

                    last_hidden, logits = self.model(
                        tensor_input
                    )

                    probs = torch.softmax(
                        logits,
                        dim=-1
                    )

                    # Official AASIST class mapping:
                    # Index 0 = SPOOF
                    # Index 1 = BONAFIDE

                    spoof_prob = float(
                        probs[0, 0].item()
                    )

                    bonafide_prob = float(
                        probs[0, 1].item()
                    )

                    logits_raw = [
                        float(logits[0, 0].item()),
                        float(logits[0, 1].item())
                    ]

            except Exception as e:

                log_crash(
                    e,
                    context=(
                        "AASIST-L Neural Inference "
                        "Forward Pass"
                    ),
                    extra_details={
                        "waveform_length": len(y),
                        "sr": sr
                    }
                )

                logger.error(
                    "AASIST-L inference error: %s",
                    e
                )

                spoof_prob = 0.5
                bonafide_prob = 0.5

        inference_ms = (
            time.perf_counter() - t_start
        ) * 1000.0

        model_score = round(
            spoof_prob * 100.0,
            2
        )

        # ============================================================
        # 2. SUPPORTING ACOUSTIC TELEMETRY
        # ============================================================

        try:

            corr = scipy.signal.correlate(
                y,
                y,
                mode="full",
                method="fft"
            )

            corr = corr[len(corr) // 2:]

            corr_norm = (
                corr / corr[0]
                if corr[0] > 0
                else corr
            )

            min_lag = int(
                sr * 0.0025
            )

            max_lag = min(
                int(sr * 0.02),
                len(corr_norm) - 1
            )

            autocorr_peak = (
                float(
                    np.max(
                        corr_norm[
                            min_lag:max_lag
                        ]
                    )
                )
                if max_lag > min_lag
                else 0.0
            )

        except Exception:

            autocorr_peak = 0.0

        # ============================================================
        # 3. BASE AASIST TELEMETRY
        # ============================================================

        telemetry = {

            "model_engine": self.model_name,

            "pretrained_loaded": (
                self.model is not None
                and self.is_ready
            ),

            "model_score": model_score,

            "spoof_probability": round(
                spoof_prob,
                4
            ),

            "bonafide_probability": round(
                bonafide_prob,
                4
            ),

            "raw_logits": [
                round(l, 4)
                for l in logits_raw
            ],

            "autocorr_peak": round(
                autocorr_peak,
                4
            ),

            "inference_time_ms": round(
                inference_ms,
                2
            )
        }

        # ============================================================
        # 4. HACKATHON RANDOM FOREST CLASSIFIER
        # ============================================================

        rf_score, rf_telemetry = (
            hackathon_classifier.infer(
                y,
                sr=sr
            )
        )

        telemetry.update(
            rf_telemetry
        )

        # ============================================================
        # 5. CONSERVATIVE FUSION
        # ============================================================
        #
        # AASIST = 70%
        # Random Forest = 30%
        #
        # Both scores represent AI / synthetic likelihood
        # on a 0-100 scale.
        # ============================================================

        if (
            rf_telemetry.get(
                "classifier_score"
            ) is not None
        ):

            fused_model_score = (
                0.20 * model_score
                + 0.80 * rf_score
            )

        else:

            # If RF fails, safely fall back
            # to the original AASIST score.

            fused_model_score = model_score

        # ============================================================
        # 6. STORE BOTH INDIVIDUAL SCORES + FUSED SCORE
        # ============================================================

        telemetry["aasist_score"] = round(
            model_score,
            2
        )

        telemetry["hackathon_rf_score"] = (

            round(
                rf_score,
                2
            )

            if (
                rf_telemetry.get(
                    "classifier_score"
                ) is not None
            )

            else None
        )

        telemetry["fused_model_score"] = round(
            fused_model_score,
            2
        )

        # ============================================================
        # 7. RETURN FUSED SCORE
        # ============================================================

        return (
            round(
                fused_model_score,
                2
            ),
            telemetry
        )


# Singleton detector instance used by
# production routers.

detector = SyntheticVoiceDetector()

