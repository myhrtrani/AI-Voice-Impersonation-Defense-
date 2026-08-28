"""
Comprehensive Model Benchmark & Validation Test Suite (Checkpoint 3).

Evaluates the complete end-to-end pipeline across 8 rigorously labeled authentic & synthetic clips:
audio chunk -> noise reduction -> DSP/LFCC extraction -> model inference -> risk blend.
"""

import os
import sys
import time
import numpy as np
import librosa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.detector import detector
from app.dsp.preprocessor import strip_background_noise
from app.dsp.lfcc import compute_lfcc, analyze_lfcc_high_freq_artifacts
from app.dsp.features import extract_all_dsp_features
from app.scoring.engine import scoring_engine
from app.config import settings

VAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "validation"))
sr = settings.AUDIO.SAMPLE_RATE

clips = [
    # 4 Authentic Human Clips
    {"file": "human_clean_male.wav", "label": "AUTHENTIC", "desc": "Clean Human Male (F0~120Hz, natural -12dB/oct roll-off)"},
    {"file": "human_clean_female.wav", "label": "AUTHENTIC", "desc": "Clean Human Female (F0~215Hz, natural micro-jitter)"},
    {"file": "human_noisy_ambient.wav", "label": "AUTHENTIC", "desc": "Human Male + Ambient Room Noise (SNR ~ 14 dB)"},
    {"file": "human_noisy_heavy.wav", "label": "AUTHENTIC", "desc": "Human Male + Heavy Wideband Noise (SNR ~ 6 dB)"},

    # 4 Synthetic / AI Cloned Clips
    {"file": "synthetic_neural_tts.wav", "label": "SYNTHETIC", "desc": "Neural Vocoder TTS (5.5-6.9kHz upper ripple)"},
    {"file": "synthetic_voice_clone_male.wav", "label": "SYNTHETIC", "desc": "Male Voice Clone (flat F0, zero jitter, vocoder leakage)"},
    {"file": "synthetic_voice_clone_female.wav", "label": "SYNTHETIC", "desc": "Female Voice Clone (flat F0~225Hz, upper harmonics)"},
    {"file": "synthetic_fastspeech_vocoder.wav", "label": "SYNTHETIC", "desc": "FastSpeech-style Multi-band Synthesis"}
]


def run_full_validation_suite():
    print("\n" + "=" * 110)
    print(" [CHECKPOINT 3] PRETRAINED MODEL BENCHMARK & VALIDATION SUITE")
    print(f" Model Engine: {detector.model_name}")
    print(f" Target Test Suite: 8 Labeled Audio Clips (4 Authentic Human, 4 AI Synthetic/Cloned)")
    print("=" * 110)

    results = []
    tp, tn, fp, fn = 0, 0, 0, 0
    total_model_time_ms = 0.0
    total_pipeline_time_ms = 0.0

    print(f"\n {'#':<3} | {'Clip Filename':<28} | {'Ground Truth':<11} | {'Model %':<8} | {'LFCC %':<8} | {'Blended %':<10} | {'Model ms':<9} | {'Pipeline ms'}")
    print("-" * 110)

    for idx, c in enumerate(clips, 1):
        file_path = os.path.join(VAL_DIR, c["file"])
        if not os.path.exists(file_path):
            print(f"File missing: {c['file']}")
            continue

        raw_y, _ = librosa.load(file_path, sr=sr)
        duration_sec = len(raw_y) / sr

        # Complete Ingestion Pipeline Benchmark
        t_pipe_start = time.perf_counter()

        # 1. Mandatory Noise Stripping
        clean_y, noise_meta = strip_background_noise(raw_y, sr=sr)

        # 2. DSP & LFCC Extraction
        lfcc_m, fb_e = compute_lfcc(clean_y, sr=sr)
        lfcc_res = analyze_lfcc_high_freq_artifacts(lfcc_m, fb_e)
        dsp_res = extract_all_dsp_features(clean_y, sr=sr)

        # 3. Model Inference (Isolated Latency Measurement)
        t_model_start = time.perf_counter()
        model_score, model_meta = detector.infer(clean_y, sr=sr)
        model_time_ms = (time.perf_counter() - t_model_start) * 1000.0

        # 4. Risk Blend
        chunk_risk = scoring_engine.compute_chunk_risk_score(
            model_score=model_score,
            lfcc_artifact_score=lfcc_res["lfcc_artifact_score"],
            pitch_anomaly_score=dsp_res["pitch_anomaly_score"],
            spectral_anomaly_score=dsp_res["spectral_anomaly_score"]
        )

        pipe_time_ms = (time.perf_counter() - t_pipe_start) * 1000.0
        total_model_time_ms += model_time_ms
        total_pipeline_time_ms += pipe_time_ms

        # Classification decision based on general threshold (> 40 = Suspicious/Synthetic)
        predicted_label = "SYNTHETIC" if chunk_risk >= 40.0 else "AUTHENTIC"
        is_correct = (predicted_label == c["label"])

        if c["label"] == "SYNTHETIC":
            if predicted_label == "SYNTHETIC":
                tp += 1
            else:
                fn += 1
        else:
            if predicted_label == "AUTHENTIC":
                tn += 1
            else:
                fp += 1

        res = {
            "index": idx,
            "filename": c["file"],
            "desc": c["desc"],
            "ground_truth": c["label"],
            "predicted": predicted_label,
            "is_correct": is_correct,
            "model_score": model_score,
            "lfcc_score": lfcc_res["lfcc_artifact_score"],
            "pitch_mean": dsp_res["pitch_mean"],
            "pitch_var": dsp_res["pitch_variance"],
            "jitter": dsp_res["jitter"],
            "flatness": dsp_res["spectral_flatness"],
            "centroid": dsp_res["spectral_centroid"],
            "blended_risk": chunk_risk,
            "model_time_ms": model_time_ms,
            "pipe_time_ms": pipe_time_ms
        }
        results.append(res)

        print(f" {idx:<3} | {c['file']:<28} | {c['label']:<11} | {model_score:<8.2f} | {lfcc_res['lfcc_artifact_score']:<8.2f} | {chunk_risk:<10.2f} | {model_time_ms:<9.2f} | {pipe_time_ms:.2f} ms")

    print("=" * 110)

    # Detailed Per-Clip Acoustic Telemetry Table
    print("\n>>> DETAILED ACOUSTIC TELEMETRY PER TEST CLIP:")
    print(f" {'#':<3} | {'Ground Truth':<10} | {'F0 Mean':<9} | {'F0 Var':<10} | {'Jitter %':<9} | {'Flatness':<10} | {'Centroid Hz':<12} | {'LFCC Upper %'}")
    print("-" * 110)
    for r in results:
        print(f" {r['index']:<3} | {r['ground_truth']:<10} | {r['pitch_mean']:<9.2f} | {r['pitch_var']:<10.2f} | {r['jitter']:<9.3f} | {r['flatness']:<10.5f} | {r['centroid']:<12.1f} | {r['lfcc_score']:.2f}%")
    print("-" * 110)

    # Statistical Evaluation Metrics
    n = len(results)
    accuracy = ((tp + tn) / n) * 100.0 if n > 0 else 0.0
    precision = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    avg_model_ms = total_model_time_ms / n
    avg_pipe_ms = total_pipeline_time_ms / n

    print("\n>>> VALIDATION PERFORMANCE METRICS (N = 8 benchmark clips):")
    print(f"  Confusion Matrix       : TP={tp} | TN={tn} | FP={fp} | FN={fn}")
    print(f"  Accuracy               : {accuracy:.1f}%")
    print(f"  Precision (Synthetic)  : {precision:.1f}%")
    print(f"  Recall (Synthetic)     : {recall:.1f}%")
    print(f"  F1 Score               : {f1:.1f}%")
    print(f"  Avg Model Latency      : {avg_model_ms:.2f} ms per 6.0s clip ({avg_model_ms / (6.0/2.5):.2f} ms per 2.5s chunk)")
    print(f"  Avg Pipeline Latency   : {avg_pipe_ms:.2f} ms total per clip ({avg_pipe_ms / (6.0/2.5):.2f} ms per 2.5s chunk)")
    print("=" * 110 + "\n")

    return results, {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "acc": accuracy, "prec": precision, "rec": recall, "f1": f1}


if __name__ == "__main__":
    run_full_validation_suite()
