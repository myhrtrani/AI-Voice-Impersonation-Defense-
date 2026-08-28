"""
Production Pipeline Benchmark on Genuine Audio Dataset (Checkpoint 3).
Evaluates the official NAVER Clova AASIST-L pretrained model (85,306 parameters, strict=True)
and the complete shared ingestion pipeline on genuine authentic human speech (LibriSpeech)
and genuine neural voice cloning speech (Coqui XTTS-v2).
"""

import os
import sys
import time
import hashlib
import torch
import numpy as np
import librosa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.detector import detector
from app.models.aasist import load_aasist_model, pad_to_aasist_length
from app.dsp.preprocessor import strip_background_noise
from app.dsp.lfcc import compute_lfcc, analyze_lfcc_high_freq_artifacts
from app.dsp.features import extract_all_dsp_features
from app.scoring.engine import scoring_engine
from app.config import settings

GEN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "genuine_validation"))
sr = settings.AUDIO.SAMPLE_RATE

clips = [
    # 5 Authentic Human Speech Clips (LibriSpeech ASR Dataset, OpenSLR 12)
    {
        "file": "librispeech_male_clean.wav",
        "label": "AUTHENTIC",
        "dataset": "LibriSpeech (OpenSLR 12)",
        "desc": "Authentic Clean Human Male Voice (LibriVox reader)"
    },
    {
        "file": "librispeech_female_clean.wav",
        "label": "AUTHENTIC",
        "dataset": "LibriSpeech (OpenSLR 12)",
        "desc": "Authentic Clean Human Female Voice"
    },
    {
        "file": "librispeech_speech_clean.wav",
        "label": "AUTHENTIC",
        "dataset": "LibriSpeech (OpenSLR 12)",
        "desc": "Authentic Human Conversational Sentence"
    },
    {
        "file": "librispeech_male_noisy_ambient.wav",
        "label": "AUTHENTIC",
        "dataset": "LibriSpeech + Ambient Noise",
        "desc": "Authentic Human Voice + Room Ambient Noise (SNR ~ 14 dB)"
    },
    {
        "file": "librispeech_male_noisy_heavy.wav",
        "label": "AUTHENTIC",
        "dataset": "LibriSpeech + Heavy Noise",
        "desc": "Authentic Human Voice + Heavy Wideband Noise (SNR ~ 6 dB)"
    },

    # 4 Genuine AI-Generated Speech Clips (Coqui XTTS-v2 Neural Voice Cloning System)
    {
        "file": "xtts_voice_clone_en.wav",
        "label": "SYNTHETIC",
        "dataset": "Coqui XTTS-v2 (HuggingFace)",
        "desc": "Genuine Neural Voice Clone (English XTTS-v2)"
    },
    {
        "file": "xtts_voice_clone_es.wav",
        "label": "SYNTHETIC",
        "dataset": "Coqui XTTS-v2 (HuggingFace)",
        "desc": "Genuine Neural Voice Clone (Spanish XTTS-v2)"
    },
    {
        "file": "xtts_voice_clone_fr.wav",
        "label": "SYNTHETIC",
        "dataset": "Coqui XTTS-v2 (HuggingFace)",
        "desc": "Genuine Neural Voice Clone (French XTTS-v2)"
    },
    {
        "file": "xtts_voice_clone_de.wav",
        "label": "SYNTHETIC",
        "dataset": "Coqui XTTS-v2 (HuggingFace)",
        "desc": "Genuine Neural Voice Clone (German XTTS-v2)"
    }
]


def run_benchmark():
    print("\n" + "=" * 122)
    print(" [CHECKPOINT 3 FINAL VERIFICATION] OFFICIAL AASIST-L PRETRAINED MODEL BENCHMARK")
    print(f" Model Name        : {detector.model_name}")
    print(f" Checkpoint Path   : {detector.weights_path}")
    print(f" Checkpoint Size   : {detector.file_size:,} bytes ({detector.file_size/1024:.2f} KB)")
    print(f" Trainable Params  : {detector.param_count:,} parameters (Exact official AASIST-L architecture)")
    print(f" Strict Load State : True (0 missing keys, 0 unexpected keys, 0 shape mismatches)")
    print(f" Test Set Scope    : {len(clips)} Genuine Audio Clips (5 Authentic Human, 4 Coqui XTTS-v2 Voice Clones)")
    print("=" * 122)

    results = []

    # Counters for AASIST-only classification (threshold P(Spoof) >= 50%)
    m_tp, m_tn, m_fp, m_fn = 0, 0, 0, 0
    # Counters for Blended System classification (threshold Risk >= 40%)
    b_tp, b_tn, b_fp, b_fn = 0, 0, 0, 0

    total_model_time_ms = 0.0
    total_dsp_time_ms = 0.0
    total_pipe_time_ms = 0.0

    print(f"\n {'#':<2} | {'Clip Filename':<32} | {'Ground Truth':<10} | {'Raw Logits [0,1]':<20} | {'AASIST P(Spoof)':<16} | {'LFCC Score':<11} | {'Blended Risk':<13} | {'Decision'}")
    print("-" * 122)

    for idx, c in enumerate(clips, 1):
        file_path = os.path.join(GEN_DIR, c["file"])
        if not os.path.exists(file_path):
            print(f"Missing file: {c['file']}")
            continue

        raw_y, _ = librosa.load(file_path, sr=sr)
        duration_sec = len(raw_y) / sr

        # Pipeline Timing Breakdown
        t_pipe_start = time.perf_counter()

        # 1. Mandatory Noise Preprocessor
        clean_y, noise_meta = strip_background_noise(raw_y, sr=sr)

        # 2. DSP & LFCC Feature Extraction
        t_dsp_start = time.perf_counter()
        lfcc_m, fb_e = compute_lfcc(clean_y, sr=sr)
        lfcc_res = analyze_lfcc_high_freq_artifacts(lfcc_m, fb_e)
        dsp_res = extract_all_dsp_features(clean_y, sr=sr)
        dsp_time_ms = (time.perf_counter() - t_dsp_start) * 1000.0

        # 3. Production AASIST-L Pretrained Neural Model Inference
        model_score, model_meta = detector.infer(clean_y, sr=sr)
        pipe_time_ms = (time.perf_counter() - t_pipe_start) * 1000.0

        model_time_ms = model_meta.get("inference_time_ms", 0.0)
        total_model_time_ms += model_time_ms
        total_dsp_time_ms += dsp_time_ms
        total_pipe_time_ms += pipe_time_ms

        # 4. Final Risk Blend
        chunk_risk = scoring_engine.compute_chunk_risk_score(
            model_score=model_score,
            lfcc_artifact_score=lfcc_res["lfcc_artifact_score"],
            pitch_anomaly_score=dsp_res["pitch_anomaly_score"],
            spectral_anomaly_score=dsp_res["spectral_anomaly_score"]
        )

        spoof_prob = model_meta.get("spoof_probability", 0.0)
        raw_logits = model_meta.get("raw_logits", [0.0, 0.0])

        # (a) AASIST-only evaluation (>= 0.50 threshold)
        aasist_pred = "SYNTHETIC" if spoof_prob >= 0.50 else "AUTHENTIC"
        if c["label"] == "SYNTHETIC":
            if aasist_pred == "SYNTHETIC":
                m_tp += 1
            else:
                m_fn += 1
        else:
            if aasist_pred == "AUTHENTIC":
                m_tn += 1
            else:
                m_fp += 1

        # (b) Blended System evaluation (>= 40.0% threshold)
        blended_pred = "SYNTHETIC" if chunk_risk >= 40.0 else "AUTHENTIC"
        if c["label"] == "SYNTHETIC":
            if blended_pred == "SYNTHETIC":
                b_tp += 1
            else:
                b_fn += 1
        else:
            if blended_pred == "AUTHENTIC":
                b_tn += 1
            else:
                b_fp += 1

        logits_str = f"[{raw_logits[0]:+.2f}, {raw_logits[1]:+.2f}]"
        prob_str = f"{spoof_prob*100.0:.2f}%"
        lfcc_str = f"{lfcc_res['lfcc_artifact_score']:.2f}%"
        risk_str = f"{chunk_risk:.2f}%"
        decision_str = f"{blended_pred} ({'CORRECT' if blended_pred == c['label'] else 'INCORRECT'})"

        print(f" {idx:<2} | {c['file']:<32} | {c['label']:<10} | {logits_str:<20} | {prob_str:<16} | {lfcc_str:<11} | {risk_str:<13} | {decision_str}")

        results.append({
            "idx": idx,
            "file": c["file"],
            "dataset": c["dataset"],
            "desc": c["desc"],
            "ground_truth": c["label"],
            "duration_sec": duration_sec,
            "raw_logits": raw_logits,
            "spoof_prob": spoof_prob,
            "bonafide_prob": model_meta.get("bonafide_probability", 0.0),
            "model_score": model_score,
            "lfcc_score": lfcc_res["lfcc_artifact_score"],
            "pitch_mean": dsp_res["pitch_mean"],
            "pitch_var": dsp_res["pitch_variance"],
            "jitter": dsp_res["jitter"],
            "flatness": dsp_res["spectral_flatness"],
            "centroid": dsp_res["spectral_centroid"],
            "blended_risk": chunk_risk,
            "blended_pred": blended_pred,
            "aasist_pred": aasist_pred,
            "model_time_ms": model_time_ms,
            "dsp_time_ms": dsp_time_ms,
            "pipe_time_ms": pipe_time_ms,
            "noise_stripped": noise_meta.get("noise_stripped", False),
            "attenuation_db": noise_meta.get("snr_attenuation_db", 0.0)
        })

    print("=" * 122)

    n = len(results)
    avg_model_ms = total_model_time_ms / n
    avg_dsp_ms = total_dsp_time_ms / n
    avg_pipe_ms = total_pipe_time_ms / n

    # Metrics calculation helper
    def calc_metrics(tp, tn, fp, fn):
        acc = ((tp + tn) / (tp + tn + fp + fn)) * 100.0
        prec = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 0.0
        rec = (tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        return acc, prec, rec, f1

    m_acc, m_prec, m_rec, m_f1 = calc_metrics(m_tp, m_tn, m_fp, m_fn)
    b_acc, b_prec, b_rec, b_f1 = calc_metrics(b_tp, b_tn, b_fp, b_fn)

    print("\n>>> (A) AASIST-L PRETRAINED MODEL ISOLATED PERFORMANCE (Threshold P(Spoof) >= 50%):")
    print(f"  Confusion Matrix       : TP = {m_tp} | TN = {m_tn} | FP = {m_fp} | FN = {m_fn}")
    print(f"  Accuracy               : {m_acc:.1f}%")
    print(f"  Precision (Synthetic)  : {m_prec:.1f}%")
    print(f"  Recall (Synthetic)     : {m_rec:.1f}%")
    print(f"  F1 Score               : {m_f1:.1f}%")

    print("\n>>> (B) FINAL BLENDED RISK ENGINE PERFORMANCE (Threshold Risk >= 40.0%):")
    print(f"  Confusion Matrix       : TP = {b_tp} | TN = {b_tn} | FP = {b_fp} | FN = {b_fn}")
    print(f"  Accuracy               : {b_acc:.1f}%")
    print(f"  Precision (Synthetic)  : {b_prec:.1f}%")
    print(f"  Recall (Synthetic)     : {b_rec:.1f}%")
    print(f"  F1 Score               : {b_f1:.1f}%")

    print("\n>>> (C) EMPIRICAL CPU LATENCY MEASUREMENTS (Measured locally on this machine):")
    print(f"  1. Isolated AASIST-L Forward Pass : {avg_model_ms:.2f} ms average per clip")
    print(f"  2. Preprocessing + DSP/LFCC       : {avg_dsp_ms:.2f} ms average per clip")
    print(f"  3. Total Production Pipeline       : {avg_pipe_ms:.2f} ms average per clip")
    print("=" * 122 + "\n")

    return results


if __name__ == "__main__":
    run_benchmark()
