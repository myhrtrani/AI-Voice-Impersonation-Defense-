import os
import sys
import numpy as np
import librosa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.dsp.preprocessor import strip_background_noise
from app.dsp.lfcc import compute_lfcc, analyze_lfcc_high_freq_artifacts
from app.dsp.features import extract_all_dsp_features
from app.models.detector import detector
from app.scoring.engine import scoring_engine

GENUINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "genuine_validation"))

def run_math_proof():
    filepath = os.path.join(GENUINE_DIR, "xtts_voice_clone_en.wav")
    y, sr = librosa.load(filepath, sr=16000, mono=True)
    
    # Grab exactly Chunk 1 (first 40000 samples)
    chunk = y[:40000]
    
    # Run the exact production pipeline steps
    clean_audio, _ = strip_background_noise(chunk, sr=sr)
    
    # LFCC
    lfcc_matrix, log_fb_energies = compute_lfcc(clean_audio, sr=sr)
    lfcc_artifacts = analyze_lfcc_high_freq_artifacts(lfcc_matrix, log_fb_energies)
    lfcc_score = lfcc_artifacts["lfcc_artifact_score"]
    
    # DSP
    dsp_features = extract_all_dsp_features(clean_audio, sr=sr)
    pitch_anomaly = dsp_features["pitch_anomaly_score"]
    spectral_anomaly = dsp_features["spectral_anomaly_score"]
    
    # Model
    model_score, _ = detector.infer(clean_audio, sr=sr)
    
    # Weights
    w_m = scoring_engine.config.WEIGHT_MODEL
    w_l = scoring_engine.config.WEIGHT_LFCC
    w_p = scoring_engine.config.WEIGHT_PITCH_JITTER
    w_s = scoring_engine.config.WEIGHT_SPECTRAL
    
    print("\n--- EXACT CHUNK 1 COMPONENTS ---")
    print(f"Model Score: {model_score} | Weight: {w_m} | Contribution: {model_score * w_m}")
    print(f"LFCC Score: {lfcc_score} | Weight: {w_l} | Contribution: {lfcc_score * w_l}")
    print(f"Pitch Anomaly: {pitch_anomaly} | Weight: {w_p} | Contribution: {pitch_anomaly * w_p}")
    print(f"Spectral Anomaly: {spectral_anomaly} | Weight: {w_s} | Contribution: {spectral_anomaly * w_s}")
    
    raw_risk = (model_score * w_m) + (lfcc_score * w_l) + (pitch_anomaly * w_p) + (spectral_anomaly * w_s)
    print(f"Raw Chunk Risk Math: {raw_risk} -> Rounded: {round(max(0.0, min(100.0, raw_risk)), 2)}%")
    
    # EWMA Math
    print("\n--- EWMA CALCULATION ---")
    alpha = scoring_engine.config.EWMA_ALPHA
    print(f"EWMA = {alpha} * {raw_risk} + (1 - {alpha}) * {raw_risk}  (since prev=None)")
    
    # Let's run Chunk 2 to show the second EWMA
    chunk2 = y[40000:80000]
    clean2, _ = strip_background_noise(chunk2, sr=sr)
    lf2, logfb2 = compute_lfcc(clean2, sr=sr)
    lf_art2 = analyze_lfcc_high_freq_artifacts(lf2, logfb2)
    dsp2 = extract_all_dsp_features(clean2, sr=sr)
    m2, _ = detector.infer(clean2, sr=sr)
    
    raw_2 = (m2 * w_m) + (lf_art2["lfcc_artifact_score"] * w_l) + (dsp2["pitch_anomaly_score"] * w_p) + (dsp2["spectral_anomaly_score"] * w_s)
    raw_2 = round(max(0.0, min(100.0, raw_2)), 2)
    
    ewma_prev = round(max(0.0, min(100.0, raw_risk)), 2)
    ewma_2 = alpha * raw_2 + (1 - alpha) * ewma_prev
    print(f"Chunk 2 Raw: {raw_2}%")
    print(f"Chunk 2 EWMA Math = {alpha} * {raw_2} + (1 - {alpha}) * {ewma_prev} = {ewma_2} -> Rounded: {round(max(0.0, min(100.0, ewma_2)), 2)}%")
    

if __name__ == "__main__":
    run_math_proof()
