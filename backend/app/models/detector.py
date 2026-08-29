"""
Pretrained Synthetic Speech & Deepfake Audio Detector Module.
Integrates Official NAVER Clova AASIST-L Pretrained Neural Model (85,306 parameters).

Production Pipeline:
--------------------
1. Model: Official AASIST-L (Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention Networks)
2. Pretrained Checkpoint: AASIST-L.pth (426,428 bytes, strict=True loaded)
3. Input Handling: 16,000 Hz waveform repetition-padded to official length 64,600 samples
4. Class Mapping: Index 0 = SPOOF (Synthetic), Index 1 = BONAFIDE (Authentic Human)
5. Output: Model Confidence Score [0.0 - 100.0] representing P(Spoof)
6. Supporting Telemetry: Acoustic features & raw logits for diagnostics.
"""

import os
import time
import asyncio
import threading
import numpy as np
import scipy.signal
import torch
from typing import Dict, Any, Tuple

from app.models.aasist import AASIST_L, load_aasist_model, load_fusion_model, pad_to_aasist_length


_fusion_model = None
_fusion_model_lock = threading.Lock()


def _get_fusion_model():
    global _fusion_model
    if _fusion_model is None:
        with _fusion_model_lock:
            if _fusion_model is None:
                _fusion_model = load_fusion_model()
    return _fusion_model


def _standardized_audio_tensor(audio_data: np.ndarray) -> torch.Tensor:
    padded_audio = pad_to_aasist_length(audio_data, max_len=64600)
    return torch.from_numpy(padded_audio.astype(np.float32)).unsqueeze(0)


def run_aasist_inference(audio_data: np.ndarray) -> torch.Tensor:
    """Run the cached standalone AASIST branch on standardized audio."""
    model = _get_fusion_model().aasist
    tensor_input = _standardized_audio_tensor(audio_data)
    with torch.no_grad():
        _, logits = model(tensor_input)
    return logits.cpu()


def run_wavlm_inference(audio_data: np.ndarray) -> torch.Tensor:
    """Run the cached frozen WavLM branch and its two-class head."""
    model = _get_fusion_model()
    tensor_input = _standardized_audio_tensor(audio_data)
    with torch.no_grad():
        frame_embeddings = model.wavlm(input_values=tensor_input).last_hidden_state
        mean_embeddings = frame_embeddings.mean(dim=1)
        std_embeddings = frame_embeddings.var(dim=1, unbiased=False).add(1e-6).sqrt()
        logits = model.wavlm_classifier(torch.cat([mean_embeddings, std_embeddings], dim=-1))
    return logits.cpu()


def fuse_scores(
    aasist_logits: torch.Tensor,
    wavlm_logits: torch.Tensor,
    weight_aasist: float = 0.4,
    weight_wavlm: float = 0.6
) -> Dict[str, Any]:
    """Fuse spoof probabilities, where class index 0 is the spoof class."""
    if weight_aasist < 0 or weight_wavlm < 0 or not np.isclose(weight_aasist + weight_wavlm, 1.0):
        raise ValueError("Ensemble weights must be non-negative and sum to 1.0")

    aasist_probabilities = torch.softmax(torch.as_tensor(aasist_logits), dim=-1)
    wavlm_probabilities = torch.softmax(torch.as_tensor(wavlm_logits), dim=-1)
    aasist_probability = float(aasist_probabilities[..., 0].reshape(-1)[0].item())
    wavlm_probability = float(wavlm_probabilities[..., 0].reshape(-1)[0].item())
    final_probability = weight_aasist * aasist_probability + weight_wavlm * wavlm_probability

    return {
        "aasist_probability": aasist_probability,
        "wavlm_probability": wavlm_probability,
        "final_probability": final_probability,
        "aasist_score": round(aasist_probability * 100.0, 2),
        "wavlm_score": round(wavlm_probability * 100.0, 2),
        "unified_score": round(final_probability * 100.0, 2),
        "aasist_logits": torch.as_tensor(aasist_logits).reshape(-1, 2)[0].tolist(),
        "wavlm_logits": torch.as_tensor(wavlm_logits).reshape(-1, 2)[0].tolist()
    }


async def predict_ensemble_async(
    audio_data: np.ndarray,
    weight_aasist: float = 0.4,
    weight_wavlm: float = 0.6
) -> Dict[str, Any]:
    """Run AASIST-L and WavLM concurrently without blocking the event loop."""
    loop = asyncio.get_running_loop()
    task_aasist = loop.run_in_executor(None, run_aasist_inference, audio_data)
    task_wavlm = loop.run_in_executor(None, run_wavlm_inference, audio_data)
    aasist_logits, wavlm_logits = await asyncio.gather(task_aasist, task_wavlm)
    return fuse_scores(aasist_logits, wavlm_logits, weight_aasist, weight_wavlm)


class SyntheticVoiceDetector:
    def __init__(self):
        self.model_name = "NAVER Clova AASIST-L (Official Pretrained Checkpoint)"
        self.weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "weights", "AASIST-L.pth"))
        self.device = torch.device("cpu")
        self.param_count = 0
        self.file_size = 0

        try:
            self.model, self.param_count, self.file_size = load_aasist_model(self.weights_path)
            self.is_ready = True
            print(f" Loaded {self.model_name} ({self.param_count:,} trainable params, {self.file_size/1024:.1f} KB, strict=True)")
        except Exception as e:
            print(f"Warning: Failed to load AASIST-L weights: {e}")
            self.model = None
            self.is_ready = False

    def infer(self, y: np.ndarray, sr: int = 16000) -> Tuple[float, Dict[str, Any]]:
        """
        Runs official pretrained AASIST-L neural inference on an audio chunk.

        Args:
            y: Audio waveform as 1D float32 numpy array.
            sr: Sampling rate (16000 Hz).

        Returns:
            Tuple of (model_confidence_score [0-100], telemetry_dict)
        """
        if len(y) < int(sr * 0.2):  # Less than 200ms
            return 0.0, {"confidence": 0.0, "reason": "Insufficient audio duration", "inference_ms": 0.0}

        t_start = time.perf_counter()

        spoof_prob = 0.0
        bonafide_prob = 1.0
        logits_raw = [0.0, 0.0]

        if self.model is not None and self.is_ready:
            try:
                # 1. Official Input Preparation: repetition-padding to 64,600 samples
                y_padded = pad_to_aasist_length(y, max_len=64600)
                tensor_input = torch.from_numpy(y_padded.astype(np.float32)).unsqueeze(0).to(self.device)

                # 2. Forward Pass through Official AASIST-L
                with torch.no_grad():
                    last_hidden, logits = self.model(tensor_input)
                    probs = torch.softmax(logits, dim=-1)

                    # Official ASVspoof/AASIST Class Mapping:
                    # Index 0 = SPOOF (Synthetic / AI Voice Clone)
                    # Index 1 = BONAFIDE (Authentic Human Voice)
                    spoof_prob = float(probs[0, 0].item())
                    bonafide_prob = float(probs[0, 1].item())
                    logits_raw = [float(logits[0, 0].item()), float(logits[0, 1].item())]
            except Exception as e:
                print(f"AASIST-L inference error: {e}")
                spoof_prob = 0.5
                bonafide_prob = 0.5

        inference_ms = (time.perf_counter() - t_start) * 1000.0
        model_score = round(spoof_prob * 100.0, 2)

        # 3. Supporting Heuristic Acoustic Telemetry (Diagnostics only)
        try:
            corr = scipy.signal.correlate(y, y, mode='full', method='fft')
            corr = corr[len(corr)//2:]
            corr_norm = corr / corr[0] if corr[0] > 0 else corr
            min_lag = int(sr * 0.0025)
            max_lag = min(int(sr * 0.02), len(corr_norm) - 1)
            autocorr_peak = float(np.max(corr_norm[min_lag:max_lag])) if max_lag > min_lag else 0.0
        except Exception:
            autocorr_peak = 0.0

        telemetry = {
            "model_engine": self.model_name,
            "pretrained_loaded": (self.model is not None and self.is_ready),
            "model_score": model_score,
            "spoof_probability": round(spoof_prob, 4),
            "bonafide_probability": round(bonafide_prob, 4),
            "raw_logits": [round(l, 4) for l in logits_raw],
            "autocorr_peak": round(autocorr_peak, 4),
            "inference_time_ms": round(inference_ms, 2)
        }

        return model_score, telemetry


# Singleton detector instance used by production routers
detector = SyntheticVoiceDetector()
