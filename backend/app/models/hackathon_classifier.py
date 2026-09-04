"""
Chunk-level HUMAN vs AI voice classifier.

This model is an additional ML signal.
It does NOT replace AASIST-L.
"""

import os
import time
from typing import Dict, Any, Tuple

import joblib
import librosa
import numpy as np


class HackathonVoiceClassifier:
    """
    Random Forest classifier trained on 2.5-second audio chunks.

    Classes:
        0 = HUMAN
        1 = AI
    """

    def __init__(self):
        self.model = None
        self.is_ready = False

        self.model_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "models",
                "hackathon_voice_classifier_chunked.joblib",
            )
        )

        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"Classifier model not found: {self.model_path}"
                )

            self.model = joblib.load(self.model_path)

            if self.model.n_features_in_ != 189:
                raise RuntimeError(
                    f"Expected 189 features, "
                    f"model expects {self.model.n_features_in_}"
                )

            if list(self.model.classes_) != [0, 1]:
                raise RuntimeError(
                    f"Expected classes [0, 1], "
                    f"got {self.model.classes_}"
                )

            self.is_ready = True

        except Exception as exc:
            print(
                f"Hackathon classifier unavailable: {exc}"
            )
            self.model = None
            self.is_ready = False

    @staticmethod
    def extract_features(
        y: np.ndarray,
        sr: int
    ) -> np.ndarray:

        features = []

        # ----------------------------------------------------
        # MFCC: 80 features
        # ----------------------------------------------------

        mfcc = librosa.feature.mfcc(
            y=y,
            sr=sr,
            n_mfcc=20
        )

        features.extend(np.mean(mfcc, axis=1))
        features.extend(np.std(mfcc, axis=1))
        features.extend(np.min(mfcc, axis=1))
        features.extend(np.max(mfcc, axis=1))

        # ----------------------------------------------------
        # MFCC delta: 80 features
        # ----------------------------------------------------

        delta = librosa.feature.delta(mfcc)

        features.extend(np.mean(delta, axis=1))
        features.extend(np.std(delta, axis=1))
        features.extend(np.min(delta, axis=1))
        features.extend(np.max(delta, axis=1))

        # ----------------------------------------------------
        # Spectral: 20 features
        # ----------------------------------------------------

        spectral_features = [
            librosa.feature.spectral_centroid(
                y=y,
                sr=sr
            ),
            librosa.feature.spectral_bandwidth(
                y=y,
                sr=sr
            ),
            librosa.feature.spectral_rolloff(
                y=y,
                sr=sr
            ),
            librosa.feature.spectral_flatness(
                y=y
            ),
            librosa.feature.zero_crossing_rate(
                y=y
            ),
        ]

        for feature in spectral_features:
            features.append(float(np.mean(feature)))
            features.append(float(np.std(feature)))
            features.append(float(np.min(feature)))
            features.append(float(np.max(feature)))

        # ----------------------------------------------------
        # Pitch: 4 features
        # ----------------------------------------------------

        try:

            pitch = librosa.yin(
                y,
                fmin=50,
                fmax=500,
                sr=sr
            )

            pitch = pitch[
                np.isfinite(pitch)
            ]

            if len(pitch) > 0:

                features.extend([
                    float(np.mean(pitch)),
                    float(np.std(pitch)),
                    float(np.min(pitch)),
                    float(np.max(pitch)),
                ])

            else:

                features.extend([
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ])

        except Exception:

            features.extend([
                0.0,
                0.0,
                0.0,
                0.0,
            ])

        # ----------------------------------------------------
        # RMS: 4 features
        # ----------------------------------------------------

        rms = librosa.feature.rms(y=y)

        features.extend([
            float(np.mean(rms)),
            float(np.std(rms)),
            float(np.min(rms)),
            float(np.max(rms)),
        ])

        # ----------------------------------------------------
        # Peak: 1 feature
        # ----------------------------------------------------

        features.append(
            float(np.max(np.abs(y)))
        )

        result = np.asarray(
            features,
            dtype=np.float32
        )

        if result.shape != (189,):
            raise RuntimeError(
                f"Expected 189 features, "
                f"got {result.shape}"
            )

        if not np.all(np.isfinite(result)):
            raise RuntimeError(
                "Classifier feature vector contains "
                "NaN or infinity."
            )

        return result

    def infer(
        self,
        y: np.ndarray,
        sr: int = 16000
    ) -> Tuple[float, Dict[str, Any]]:

        if not self.is_ready:
            return 0.0, {
                "classifier_loaded": False,
                "classifier_score": None,
            }

        if len(y) < int(sr * 0.2):
            return 0.0, {
                "classifier_loaded": True,
                "classifier_score": None,
                "reason": "Insufficient audio duration",
            }

        start = time.perf_counter()

        try:

            # Production audio is 2.5 seconds / 40,000 samples.
            # If a slightly different length arrives, use the available
            # audio and pad to the training window size.
            target_samples = int(
                sr * 2.5
            )

            if len(y) > target_samples:
                y = y[:target_samples]

            elif len(y) < target_samples:

                y = np.pad(
                    y,
                    (
                        0,
                        target_samples - len(y)
                    ),
                    mode="constant"
                )

            features = self.extract_features(
                y.astype(np.float32),
                sr
            )

            probabilities = self.model.predict_proba(
                features.reshape(1, -1)
            )[0]

            ai_position = list(
                self.model.classes_
            ).index(1)

            human_position = list(
                self.model.classes_
            ).index(0)

            ai_probability = float(
                probabilities[ai_position]
            )

            human_probability = float(
                probabilities[human_position]
            )

            elapsed_ms = (
                time.perf_counter() - start
            ) * 1000.0

            return (
                ai_probability * 100.0,
                {
                    "classifier_loaded": True,
                    "classifier_engine": (
                        "Hackathon Random Forest "
                        "2.5s Chunk Classifier"
                    ),
                    "classifier_score": round(
                        ai_probability * 100.0,
                        2
                    ),
                    "classifier_ai_probability": round(
                        ai_probability,
                        4
                    ),
                    "classifier_human_probability": round(
                        human_probability,
                        4
                    ),
                    "classifier_inference_time_ms": round(
                        elapsed_ms,
                        2
                    ),
                }
            )

        except Exception as exc:

            return 0.0, {
                "classifier_loaded": True,
                "classifier_score": None,
                "classifier_error": str(exc),
            }


# Singleton
hackathon_classifier = HackathonVoiceClassifier()