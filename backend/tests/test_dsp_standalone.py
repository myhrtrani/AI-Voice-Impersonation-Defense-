"""
Standalone DSP & LFCC Feature Extraction Test Harness.

Tests the audio processing pipeline on sample audio files and prints
detailed raw metrics and the high-frequency LFCC artifact score with
accurate mathematical definitions, units, and contextual guidance.
"""

import os
import sys
import argparse
import numpy as np
import soundfile as sf
import librosa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.dsp.lfcc import compute_lfcc, analyze_lfcc_high_freq_artifacts
from app.dsp.features import extract_all_dsp_features
from app.config import settings


def run_standalone_dsp_test(file_path: str):
    print("\n" + "=" * 88)
    print(f" [CHECKPOINT 1] DSP & LFCC FEATURE EXTRACTION TEST")
    print(f" Target Audio File: {os.path.basename(file_path)}")
    print(f" Full Path: {file_path}")
    print("=" * 88)

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    # Load audio at target sample rate (16kHz mono)
    target_sr = settings.AUDIO.SAMPLE_RATE
    y, sr = librosa.load(file_path, sr=target_sr, mono=True)
    duration_sec = len(y) / sr
    print(f" Audio Loaded: Duration = {duration_sec:.2f}s | Sample Rate = {sr} Hz | Total Samples = {len(y):,}")
    print("-" * 88)

    # 1. Linear Frequency Cepstral Coefficients (LFCC) Extraction
    lfcc_matrix, log_fb_energies = compute_lfcc(
        y,
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

    # 2. Standard DSP Feature Extraction
    dsp = extract_all_dsp_features(
        y,
        sr=sr,
        n_fft=settings.AUDIO.N_FFT,
        hop_length=settings.AUDIO.HOP_LENGTH
    )

    # 3. Formatted Telemetry Printout
    print("\n>>> RAW EXTRACTED DSP & LFCC METRICS:")
    print(f"  {'Metric Name':<32} | {'Raw Value':<14} | {'Unit / Normalization':<22} | {'Heuristic Guidance'}")
    print("  " + "-" * 84)
    print(f"  {'LFCC High-Freq Artifact Score':<32} | {lfcc_artifacts['lfcc_artifact_score']:<14.2f} | {'Index (0 - 100)':<22} | Anomaly blend (Human: <40, Neural TTS: >60)")
    print(f"  {'LFCC Upper Band Energy Ratio':<32} | {lfcc_artifacts['high_band_ratio']:<14.4f} | {'Ratio (4.8-8k / Total)':<22} | Upper linear band energy share")
    print(f"  {'LFCC Upper Cepstral Variance':<32} | {lfcc_artifacts['upper_cepstral_var']:<14.4f} | {'Variance (coeffs 10-20)':<22} | Cepstral ripple across frames")
    print(f"  {'LFCC Delta Smoothness':<32} | {lfcc_artifacts['lfcc_delta_smoothness']:<14.4f} | {'Delta Variance':<22} | Frame-to-frame dynamic variability")
    print(f"  {'Pitch (F0) Mean':<32} | {dsp['pitch_mean']:<14.2f} | {'Hertz (Hz)':<22} | Fundamental vocal frequency")
    print(f"  {'Pitch (F0) Variance':<32} | {dsp['pitch_variance']:<14.2f} | {'Hz^2 (F0 Variance)':<22} | Natural intonation (>50) vs robotic (<15)")
    print(f"  {'Cycle-to-Cycle Jitter (RAP)':<32} | {dsp['jitter']:<14.3f} | {'Percentage (%)':<22} | Detrended local pitch perturbation")
    print(f"  {'Spectral Flatness':<32} | {dsp['spectral_flatness']:<14.5f} | {'Ratio [0, 1] (0-4kHz)':<22} | Speech-band tonality (0=pure tone, 1=white noise)")
    print(f"  {'Spectral Centroid':<32} | {dsp['spectral_centroid']:<14.2f} | {'Hertz (Hz)':<22} | Center of spectral energy distribution")
    print(f"  {'Silence Ratio':<32} | {dsp['silence_ratio']:<14.3f} | {'Fraction [0, 1]':<22} | Proportion of non-voiced frames")
    print(f"  {'Active Speech Ratio':<32} | {dsp['active_speech_ratio']:<14.3f} | {'Fraction [0, 1]':<22} | Active speech frames")
    print("=" * 88 + "\n")

    return {
        "lfcc": lfcc_artifacts,
        "dsp": dsp
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone DSP and LFCC Feature Extraction Test")
    parser.add_argument("--file", type=str, default=None, help="Path to audio file to analyze (.wav)")
    args = parser.parse_args()

    default_sample = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "sample_human_clean.wav"))
    target = args.file if args.file else default_sample

    run_standalone_dsp_test(target)
