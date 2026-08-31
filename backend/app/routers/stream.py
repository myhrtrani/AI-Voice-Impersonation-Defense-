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
from app.logger import get_logger, log_analysis_chunk, log_crash
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
logger = get_logger("voice_defense.stream")

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
    t_start = time.perf_counter()

    try:
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
            hop_length=settings.AUDIO.HOP_LENGTH
        )
        lfcc_artifacts = analyze_lfcc_high_freq_artifacts(
            lfcc_matrix,
            log_fb_energies,
            n_filters=settings.AUDIO.N_FILTERBANKS
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

        latency_ms = (time.perf_counter() - t_start) * 1000.0

        # Log structured chunk analysis to analysis.log
        log_analysis_chunk(
            session_id=session_id,
            chunk_index=chunk_index,
            chunk_risk=chunk_risk,
            rolling_risk=rolling_risk,
            model_score=model_score,
            lfcc_score=lfcc_score,
            pitch_variance=dsp_features["pitch_variance"],
            jitter=dsp_features["jitter"],
            spectral_flatness=dsp_features["spectral_flatness"],
            status_color=status_color,
            severity=severity,
            alert_fired=should_alert,
            latency_ms=latency_ms
        )

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
            logger.warning(
                "ALERT TRIGGERED [%s] Session=%s Chunk=#%d Risk=%.1f%% Action='%s'",
                severity, session_id, chunk_index, rolling_risk, recommended_action
            )

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

    except Exception as e:
        log_crash(
            e,
            context=f"Audio Chunk Processing Failure (Session: {session_id}, Chunk: #{chunk_index})",
            extra_details={
                "session_id": session_id,
                "chunk_index": chunk_index,
                "samples_count": len(audio_data),
                "sampling_rate": sr,
                "context": transaction_context
            }
        )
        raise e


@router.websocket("/calls/{session_id}/stream")
async def websocket_stream_endpoint(websocket: WebSocket, session_id: str):
    """
    Unified WebSocket Endpoint:
    Handles Mode A (server-paced replay of uploaded file) and
    Mode B (client-streamed live chunk analysis).
    """
    await websocket.accept()
    logger.info("WebSocket connected for session: %s", session_id)

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
                err_msg = f"Audio file for session {session_id} not found in uploads directory"
                logger.error(err_msg)
                await websocket.send_json({"error": err_msg})
                await websocket.close()
                return

            audio_path = matching_files[0]
            logger.info("Starting Mode A audio stream replay from: %s", audio_path)
            # Load audio resampled to 16kHz mono
            y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
            total_samples = len(y)
            total_duration_sec = total_samples / target_sr
            num_chunks = max(1, int(np.ceil(total_samples / chunk_samples)))

            logger.info("Audio loaded: duration=%.2fs (%d samples), total_chunks=%d", total_duration_sec, total_samples, num_chunks)

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
                    logger.info("Mode A stream completed for session: %s (Total chunks=%d, Peak risk=%.1f%%)", session_id, chunk_index, payload["rolling_risk_score"])

                await websocket.send_json(payload)

                # Real-time replay pacing (1.8s for smooth UI transition)
                await asyncio.sleep(1.8)

        else:
            # Mode B: Receive live audio chunks from client over WebSocket
            logger.info("Starting Mode B live stream listener for session: %s", session_id)
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
                    except Exception as decode_err:
                        # Fallback for raw float32 / int16 PCM bytes
                        logger.warning("Soundfile decode failed (%s), falling back to raw PCM", decode_err)
                        audio_chunk = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                elif "text" in data:
                    msg = json.loads(data["text"])
                    if msg.get("action") == "end_call":
                        logger.info("Mode B live call end received for session: %s", session_id)
                        await websocket.send_json({"is_complete": True, "message": "Call ended"})
                        break
                    elif msg.get("action") == "update_context":
                        transaction_context = msg.get("context", "general")
                        logger.info("Mode B context updated to '%s' for session: %s", transaction_context, session_id)
                        continue
                    elif "audio_base64" in msg:
                        raw_bytes = base64.b64decode(msg["audio_base64"])
                        try:
                            audio_chunk, sr = sf.read(io.BytesIO(raw_bytes))
                            if len(audio_chunk.shape) > 1:
                                audio_chunk = np.mean(audio_chunk, axis=1)
                            if sr != target_sr:
                                audio_chunk = librosa.resample(audio_chunk, orig_sr=sr, target_sr=target_sr)
                        except Exception as decode_err:
                            logger.warning("Base64 soundfile decode failed (%s), falling back to raw PCM", decode_err)
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
        logger.info("WebSocket disconnected normally for session: %s (Total chunks=%d)", session_id, chunk_index)
    except Exception as e:
        log_crash(
            e,
            context=f"WebSocket Stream Pipeline Crash (Session: {session_id}, Mode: {mode})",
            extra_details={"session_id": session_id, "mode": mode, "chunk_index": chunk_index}
        )
        try:
            await websocket.send_json({"error": str(e), "message": "Streaming error occurred. Full trace logged to error.log"})
        except Exception:
            pass
