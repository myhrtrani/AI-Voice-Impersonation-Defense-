"""
WebSocket Real-Time Audio Streaming Pipeline (Mode A Replay & Mode B Live).

Guarantees identical JSON payload shape, feature extraction, and risk scoring logic
across both uploaded simulated replays and live WebRTC calls.
"""

import asyncio
import base64
import glob
import io
import json
import os
import time
from typing import Dict, Any, Optional

import librosa
import numpy as np
import soundfile as sf
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.db import (
    get_session_summary,
    record_alert,
    record_chunk_metric
)
from app.dsp.features import extract_all_dsp_features
from app.dsp.lfcc import analyze_lfcc_high_freq_artifacts, compute_lfcc
from app.dsp.preprocessor import strip_background_noise
from app.models.detector import detector
from app.scoring.engine import scoring_engine

router = APIRouter(tags=["Stream"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


def process_audio_chunk(
    audio_data: np.ndarray,
    sr: int,
    session_id: str,
    chunk_index: int,
    previous_rolling_score: Optional[float],
    previous_severity: str,
    transaction_context: str,
    elapsed_seconds: float,
    actual_chunk_duration_sec: float = 2.5,
    actual_chunk_samples: int = 40000,
    total_audio_duration_sec: float = 2.5,
    is_padded: bool = False
) -> Dict[str, Any]:
    """
    Core unified processing pipeline for a single 2.5s audio chunk.
    Runs noise stripping -> DSP & LFCC extraction -> model inference -> risk blend & alert evaluation.
    """
    # 1. Noise Preprocessing (Mandatory noise stripping)
    if settings.ENABLE_NOISE_REDUCTION:
        clean_audio, noise_meta = strip_background_noise(audio_data, sr=sr)
    else:
        clean_audio = audio_data
        noise_meta = {"noise_stripped": False}

    # 2. Linear Frequency Cepstral Coefficients (LFCC) Extraction
    lfcc_matrix, log_fb_energies = compute_lfcc(
        clean_audio,
        sr=sr,
        n_lfcc=settings.AUDIO.N_LFCC,
        n_filters=settings.AUDIO.N_FILTERBANKS,
        n_fft=settings.AUDIO.N_FFT,
        hop_length=settings.AUDIO.HOP_LENGTH,
        f_min=settings.AUDIO.MIN_FREQ,
        f_max=settings.AUDIO.MAX_FREQ
    )
    lfcc_artifacts = analyze_lfcc_high_freq_artifacts(
        lfcc_matrix,
        log_fb_energies,
        n_filters=settings.AUDIO.N_FILTERBANKS,
        f_min=settings.AUDIO.MIN_FREQ,
        f_max=settings.AUDIO.MAX_FREQ
    )
    lfcc_score = lfcc_artifacts["lfcc_artifact_score"]

    # 3. Standard DSP Feature Extraction (Pitch variance, Jitter, Flatness, Centroid, Silence)
    dsp_features = extract_all_dsp_features(
        clean_audio,
        sr=sr,
        n_fft=settings.AUDIO.N_FFT,
        hop_length=settings.AUDIO.HOP_LENGTH
    )

    # 4. Model Inference (Acoustic & Neural Vocoder Classifier)
    model_score, model_telemetry = detector.infer(clean_audio, sr=sr)

    # 5. Risk Scoring & Rolling EWMA
    chunk_risk = scoring_engine.compute_chunk_risk_score(
        model_score=model_score,
        lfcc_artifact_score=lfcc_score,
        pitch_anomaly_score=dsp_features["pitch_anomaly_score"],
        spectral_anomaly_score=dsp_features["spectral_anomaly_score"]
    )

    rolling_risk = scoring_engine.update_rolling_score(
        current_chunk_score=chunk_risk,
        previous_rolling_score=previous_rolling_score
    )

    # 6. Alert & Action Evaluation
    should_alert, severity, recommended_action = scoring_engine.evaluate_alert(
        rolling_risk_score=rolling_risk,
        transaction_context=transaction_context,
        previous_severity=previous_severity
    )

    # Determine UI status color
    if rolling_risk >= settings.SCORING.HIGH_RISK_MIN:
        status_color = "red"
    elif rolling_risk >= settings.SCORING.LOW_RISK_MAX:
        status_color = "yellow"
    else:
        status_color = "green"

    # Assemble comprehensive metric dict
    metric_record = {
        "chunk_index": chunk_index,
        "timestamp": time.time(),
        "chunk_risk_score": chunk_risk,
        "rolling_risk_score": rolling_risk,
        "model_score": model_score,
        "lfcc_artifact_score": lfcc_score,
        "pitch_variance": dsp_features["pitch_variance"],
        "pitch_mean": dsp_features["pitch_mean"],
        "jitter": dsp_features["jitter"],
        "spectral_flatness": dsp_features["spectral_flatness"],
        "spectral_centroid": dsp_features["spectral_centroid"],
        "silence_ratio": dsp_features["silence_ratio"],
        "noise_stripped": noise_meta.get("noise_stripped", True)
    }

    # Save to database
    record_chunk_metric(session_id, metric_record)

    if should_alert and severity != "NORMAL":
        alert_record = {
            "chunk_index": chunk_index,
            "timestamp": time.time(),
            "severity": severity,
            "risk_score": rolling_risk,
            "transaction_context": transaction_context,
            "recommended_action": recommended_action
        }
        record_alert(session_id, alert_record)

    # Construct frontend response payload (exact identical shape)
    return {
        "session_id": session_id,
        "chunk_index": chunk_index,
        "timestamp": metric_record["timestamp"],
        "elapsed_seconds": round(elapsed_seconds, 2),
        "actual_chunk_duration": round(actual_chunk_duration_sec, 2),
        "actual_chunk_samples": actual_chunk_samples,
        "total_audio_duration": round(total_audio_duration_sec, 2),
        "is_padded": is_padded,
        "nominal_window_sec": round(chunk_index * settings.AUDIO.CHUNK_DURATION_SEC, 2),
        "chunk_risk_score": chunk_risk,
        "rolling_risk_score": rolling_risk,
        "status_color": status_color,
        "severity": severity,
        "alert_fired": should_alert,
        "recommended_action": recommended_action,
        "transaction_context": transaction_context,
        "noise_stripped": noise_meta.get("noise_stripped", True),
        "features": {
            "pitch_variance": dsp_features["pitch_variance"],
            "pitch_mean": dsp_features["pitch_mean"],
            "jitter": dsp_features["jitter"],
            "spectral_flatness": dsp_features["spectral_flatness"],
            "spectral_centroid": dsp_features["spectral_centroid"],
            "silence_ratio": dsp_features["silence_ratio"],
            "lfcc_artifact_score": lfcc_score,
            "model_score": model_score
        },
        "is_complete": False
    }


@router.websocket("/calls/{session_id}/stream")
async def websocket_stream_endpoint(websocket: WebSocket, session_id: str):
    """
    Unified WebSocket Endpoint:
    Handles Mode A (server-paced replay of uploaded file) and
    Mode B (client-streamed live chunk analysis).
    """
    await websocket.accept()

    session = get_session_summary(session_id)
    transaction_context = session["transaction_context"] if session else "general"
    mode = session["mode"] if session else "mode_a_upload"

    target_sr = settings.AUDIO.SAMPLE_RATE
    chunk_samples = settings.AUDIO.CHUNK_SAMPLES  # 40,000 samples for 2.5s @ 16kHz
    chunk_duration = settings.AUDIO.CHUNK_DURATION_SEC

    previous_rolling_score = None
    previous_severity = "NORMAL"
    chunk_index = 0

    try:
        if mode == "mode_a_upload":
            # Mode A: Locate uploaded file and stream simulated chunks
            matching_files = glob.glob(os.path.join(UPLOAD_DIR, f"{session_id}.*"))
            if not matching_files:
                await websocket.send_json({"error": "Audio file for session not found"})
                await websocket.close()
                return

            audio_path = matching_files[0]
            # Load audio resampled to 16kHz mono
            y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
            total_samples = len(y)
            total_duration_sec = total_samples / target_sr
            num_chunks = max(1, int(np.ceil(total_samples / chunk_samples)))

            # Stream chunks sequentially
            for i in range(num_chunks):
                start_sample = i * chunk_samples
                end_sample = min(start_sample + chunk_samples, total_samples)
                raw_chunk = y[start_sample:end_sample]
                actual_chunk_samples = len(raw_chunk)
                actual_chunk_duration = actual_chunk_samples / target_sr
                is_padded = False

                # Pad short trailing chunk if needed
                if actual_chunk_samples < chunk_samples:
                    audio_chunk = np.pad(raw_chunk, (0, chunk_samples - actual_chunk_samples), mode='constant')
                    is_padded = True
                else:
                    audio_chunk = raw_chunk

                chunk_index += 1
                elapsed_audio = min(total_duration_sec, start_sample / target_sr + actual_chunk_duration)

                payload = process_audio_chunk(
                    audio_data=audio_chunk,
                    sr=target_sr,
                    session_id=session_id,
                    chunk_index=chunk_index,
                    previous_rolling_score=previous_rolling_score,
                    previous_severity=previous_severity,
                    transaction_context=transaction_context,
                    elapsed_seconds=elapsed_audio,
                    actual_chunk_duration_sec=actual_chunk_duration,
                    actual_chunk_samples=actual_chunk_samples,
                    total_audio_duration_sec=total_duration_sec,
                    is_padded=is_padded
                )

                previous_rolling_score = payload["rolling_risk_score"]
                previous_severity = payload["severity"]

                # Mark last chunk
                if i == num_chunks - 1:
                    payload["is_complete"] = True

                await websocket.send_json(payload)

                # Real-time replay pacing (1.8s for smooth UI transition)
                await asyncio.sleep(1.8)

        else:
            # Mode B: Receive live audio chunks from client over WebSocket
            while True:
                data = await websocket.receive()
                if "bytes" in data:
                    raw_bytes = data["bytes"]
                    # Decode audio chunk from soundfile buffer (WAV/OGG/WebM)
                    try:
                        audio_chunk, sr = sf.read(io.BytesIO(raw_bytes))
                        if len(audio_chunk.shape) > 1:
                            audio_chunk = np.mean(audio_chunk, axis=1)  # Stereo to mono
                        if sr != target_sr:
                            audio_chunk = librosa.resample(audio_chunk, orig_sr=sr, target_sr=target_sr)
                    except Exception:
                        # Fallback for raw float32 / int16 PCM bytes
                        audio_chunk = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                elif "text" in data:
                    msg = json.loads(data["text"])
                    if msg.get("action") == "end_call":
                        await websocket.send_json({"is_complete": True, "message": "Call ended"})
                        break
                    elif msg.get("action") == "update_context":
                        transaction_context = msg.get("context", "general")
                        continue
                    elif "audio_base64" in msg:
                        raw_bytes = base64.b64decode(msg["audio_base64"])
                        try:
                            audio_chunk, sr = sf.read(io.BytesIO(raw_bytes))
                            if len(audio_chunk.shape) > 1:
                                audio_chunk = np.mean(audio_chunk, axis=1)
                            if sr != target_sr:
                                audio_chunk = librosa.resample(audio_chunk, orig_sr=sr, target_sr=target_sr)
                        except Exception:
                            audio_chunk = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                    else:
                        continue
                else:
                    continue

                chunk_index += 1
                elapsed = chunk_index * chunk_duration

                payload = process_audio_chunk(
                    audio_data=audio_chunk,
                    sr=target_sr,
                    session_id=session_id,
                    chunk_index=chunk_index,
                    previous_rolling_score=previous_rolling_score,
                    previous_severity=previous_severity,
                    transaction_context=transaction_context,
                    elapsed_seconds=elapsed
                )

                previous_rolling_score = payload["rolling_risk_score"]
                previous_severity = payload["severity"]

                await websocket.send_json(payload)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
