"""
Controlled A/B/C Experiment Script.
A: Clean human source audio
B: The same audio with known added background noise
C: Noisy audio after current noise-reduction preprocessing
"""

import os
import sys
import time
import numpy as np
import soundfile as sf
import librosa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.dsp.lfcc import compute_lfcc, analyze_lfcc_high_freq_artifacts
from app.dsp.features import extract_all_dsp_features
from app.dsp.preprocessor import strip_background_noise

sr = 16000

# 1. Load A: Clean reference
path_a = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "sample_human_clean.wav"))
y_a, _ = librosa.load(path_a, sr=sr)
lfcc_a_m, fb_a = compute_lfcc(y_a, sr=sr)
lfcc_a = analyze_lfcc_high_freq_artifacts(lfcc_a_m, fb_a)
dsp_a = extract_all_dsp_features(y_a, sr=sr)

# 2. Load B: Noisy sample (A + noise)
path_b = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "sample_human_noisy.wav"))
y_b, _ = librosa.load(path_b, sr=sr)
lfcc_b_m, fb_b = compute_lfcc(y_b, sr=sr)
lfcc_b = analyze_lfcc_high_freq_artifacts(lfcc_b_m, fb_b)
dsp_b = extract_all_dsp_features(y_b, sr=sr)

# 3. Process C: Noisy audio through current noise reduction
t0 = time.perf_counter()
y_c, meta_c = strip_background_noise(y_b, sr=sr)
t_c_ms = (time.perf_counter() - t0) * 1000.0

path_c = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "sample_human_noisy_STRIPPED.wav"))
sf.write(path_c, y_c, sr)

lfcc_c_m, fb_c = compute_lfcc(y_c, sr=sr)
lfcc_c = analyze_lfcc_high_freq_artifacts(lfcc_c_m, fb_c)
dsp_c = extract_all_dsp_features(y_c, sr=sr)

# Calculate SNRs
min_len = min(len(y_a), len(y_b), len(y_c))
y_a_cut = y_a[:min_len]
y_b_cut = y_b[:min_len]
y_c_cut = y_c[:min_len]

noise_b = y_b_cut - y_a_cut
signal_power = np.mean(y_a_cut ** 2)
noise_b_power = np.mean(noise_b ** 2)
snr_b_db = 10.0 * np.log10(signal_power / (noise_b_power + 1e-12))

error_c = y_c_cut - y_a_cut
error_c_power = np.mean(error_c ** 2)
snr_c_db = 10.0 * np.log10(signal_power / (error_c_power + 1e-12))

print("\n" + "=" * 100)
print(" CONTROLLED A/B/C EXPERIMENT: CLEAN (A) vs NOISY (B) vs NOISE-STRIPPED (C)")
print("=" * 100)
print(f" Processing Time for C         : {t_c_ms:.2f} ms total ({t_c_ms / (len(y_c)/40000):.2f} ms per 2.5s chunk)")
print(f" Estimated Input SNR (B)       : {snr_b_db:.2f} dB (Speech vs Added Noise)")
print(f" Residual Reconstruction SNR (C): {snr_c_db:.2f} dB (Signal vs Clean Reference Difference)")
print(f" Power Attenuation Telemetry   : {meta_c.get('snr_attenuation_db', 0.0)} dB")
print("-" * 100)

metrics = [
    ("LFCC High-Freq Artifact Score", lfcc_a['lfcc_artifact_score'], lfcc_b['lfcc_artifact_score'], lfcc_c['lfcc_artifact_score'], "0-100"),
    ("LFCC Upper Band Energy Ratio", lfcc_a['high_band_ratio'], lfcc_b['high_band_ratio'], lfcc_c['high_band_ratio'], "ratio"),
    ("LFCC Upper Cepstral Variance", lfcc_a['upper_cepstral_var'], lfcc_b['upper_cepstral_var'], lfcc_c['upper_cepstral_var'], "var"),
    ("LFCC Delta Dynamics", lfcc_a['lfcc_delta_smoothness'], lfcc_b['lfcc_delta_smoothness'], lfcc_c['lfcc_delta_smoothness'], "var"),
    ("Spectral Flatness", dsp_a['spectral_flatness'], dsp_b['spectral_flatness'], dsp_c['spectral_flatness'], "ratio"),
    ("Spectral Centroid (Hz)", dsp_a['spectral_centroid'], dsp_b['spectral_centroid'], dsp_c['spectral_centroid'], "Hz"),
    ("F0 Mean (Hz)", dsp_a['pitch_mean'], dsp_b['pitch_mean'], dsp_c['pitch_mean'], "Hz"),
    ("F0 Variance (Hz^2)", dsp_a['pitch_variance'], dsp_b['pitch_variance'], dsp_c['pitch_variance'], "Hz^2"),
    ("Jitter / RAP (%)", dsp_a['jitter'], dsp_b['jitter'], dsp_c['jitter'], "%"),
]

print(f" {'Metric Name':<30} | {'A: Clean Ref':<14} | {'B: Noisy Audio':<14} | {'C: Noise-Stripped':<18} | {'Trajectory vs Clean A'}")
print("-" * 100)
for name, a_val, b_val, c_val, unit in metrics:
    dist_b = abs(b_val - a_val)
    dist_c = abs(c_val - a_val)
    if dist_c < dist_b:
        mov = f"CLOSER to A (delta: -{dist_b - dist_c:.4f})"
    elif dist_c > dist_b:
        mov = f"FARTHER from A (delta: +{dist_c - dist_b:.4f})"
    else:
        mov = "UNCHANGED"
    print(f" {name:<30} | {a_val:<14.4f} | {b_val:<14.4f} | {c_val:<18.4f} | {mov}")
print("=" * 100 + "\n")
