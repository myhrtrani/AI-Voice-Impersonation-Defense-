"""
Synthetic Voice Model & Risk Scoring Benchmark.

Compares an authentic human voice clip against an AI synthetic/cloned speech clip
to confirm that Score(Real) < Score(Synthetic) and that LFCC captures vocoder artifacts.
"""

import os
import sys
import argparse
import librosa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.detector import detector
from app.dsp.lfcc import compute_lfcc, analyze_lfcc_high_freq_artifacts
from app.dsp.features import extract_all_dsp_features
from app.dsp.preprocessor import strip_background_noise
from app.scoring.engine import scoring_engine
from app.config import settings


def evaluate_audio_clip(file_path: str, label: str):
    sr = settings.AUDIO.SAMPLE_RATE
    y, _ = librosa.load(file_path, sr=sr, mono=True)
    
    # 1. Noise preprocessing
    clean_y, _ = strip_background_noise(y, sr=sr)
    
    # 2. LFCC extraction
    lfcc_m, fb_e = compute_lfcc(clean_y, sr=sr)
    lfcc_res = analyze_lfcc_high_freq_artifacts(lfcc_m, fb_e)
    
    # 3. DSP extraction
    dsp_res = extract_all_dsp_features(clean_y, sr=sr)
    
    # 4. Model inference
    model_score, model_meta = detector.infer(clean_y, sr=sr)
    
    # 5. Risk blend
    chunk_score = scoring_engine.compute_chunk_risk_score(
        model_score=model_score,
        lfcc_artifact_score=lfcc_res["lfcc_artifact_score"],
        pitch_anomaly_score=dsp_res["pitch_anomaly_score"],
        spectral_anomaly_score=dsp_res["spectral_anomaly_score"]
    )
    
    return {
        "label": label,
        "filename": os.path.basename(file_path),
        "duration_sec": len(y) / sr,
        "model_score": model_score,
        "lfcc_score": lfcc_res["lfcc_artifact_score"],
        "pitch_anomaly": dsp_res["pitch_anomaly_score"],
        "spectral_anomaly": dsp_res["spectral_anomaly_score"],
        "total_risk_score": chunk_score
    }


def run_real_vs_synthetic_benchmark(real_path: str, synth_path: str):
    print("\n" + "=" * 80)
    print(" [CHECKPOINT 3] REAL HUMAN SPEECH vs AI SYNTHETIC CLONE BENCHMARK")
    print("=" * 80)

    res_real = evaluate_audio_clip(real_path, "HUMAN AUTHENTIC")
    res_synth = evaluate_audio_clip(synth_path, "AI SYNTHETIC CLONE")

    print(f"\n>>> BENCHMARK RESULTS:")
    print(f"  {'Metric / Signal':<32} | {'Human Real Clip':<18} | {'AI Clone Clip':<18} | {'Delta (Synthetic - Real)'}")
    print("  " + "-" * 78)
    print(f"  {'Model Confidence Score':<32} | {res_real['model_score']:<18.2f} | {res_synth['model_score']:<18.2f} | {res_synth['model_score'] - res_real['model_score']:+.2f}")
    print(f"  {'LFCC High-Freq Artifact Score':<32} | {res_real['lfcc_score']:<18.2f} | {res_synth['lfcc_score']:<18.2f} | {res_synth['lfcc_score'] - res_real['lfcc_score']:+.2f}")
    print(f"  {'Pitch / Jitter Anomaly Score':<32} | {res_real['pitch_anomaly']:<18.2f} | {res_synth['pitch_anomaly']:<18.2f} | {res_synth['pitch_anomaly'] - res_real['pitch_anomaly']:+.2f}")
    print(f"  {'Spectral Anomaly Score':<32} | {res_real['spectral_anomaly']:<18.2f} | {res_synth['spectral_anomaly']:<18.2f} | {res_synth['spectral_anomaly'] - res_real['spectral_anomaly']:+.2f}")
    print("  " + "=" * 78)
    print(f"  {'TOTAL BLENDED RISK SCORE':<32} | {res_real['total_risk_score']:<18.2f} | {res_synth['total_risk_score']:<18.2f} | {res_synth['total_risk_score'] - res_real['total_risk_score']:+.2f}")
    print("  " + "=" * 78)

    # Verification criteria
    is_valid = res_real['total_risk_score'] < res_synth['total_risk_score']
    print(f"\n>>> VERIFICATION RESULT: {'[PASSED] Score(Real) < Score(Synthetic)' if is_valid else '[FAILED]'}")
    print("=" * 80 + "\n")
    return is_valid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real vs Synthetic Audio Detector Benchmark")
    parser.add_argument("--real", type=str, default=None, help="Path to real human audio file (.wav)")
    parser.add_argument("--synth", type=str, default=None, help="Path to synthetic clone audio file (.wav)")
    args = parser.parse_args()

    default_real = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "sample_human_clean.wav"))
    default_synth = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "sample_synthetic_clone.wav"))

    r_target = args.real if args.real else default_real
    s_target = args.synth if args.synth else default_synth

    run_real_vs_synthetic_benchmark(r_target, s_target)
