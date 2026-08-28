import librosa, numpy as np, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.models.detector import detector
from app.dsp.preprocessor import strip_background_noise
from app.dsp.lfcc import compute_lfcc, analyze_lfcc_high_freq_artifacts
from app.dsp.features import extract_all_dsp_features
from app.scoring.engine import scoring_engine

for name in ["librispeech_female_clean.wav", "librispeech_speech_clean.wav", "xtts_voice_clone_en.wav"]:
    path = os.path.join(os.path.dirname(__file__), "..", "samples", "genuine_validation", name)
    y, sr = librosa.load(path, sr=16000)
    chunk_len = 40000
    num_chunks = int(np.ceil(len(y) / chunk_len))
    print(f"\n=== {name} ({len(y)/sr:.2f}s, {num_chunks} chunks) ===")
    prev_ewma = None
    for i in range(num_chunks):
        c = y[i*chunk_len : (i+1)*chunk_len]
        if len(c) < chunk_len:
            c = np.pad(c, (0, chunk_len - len(c)))
        clean_c, _ = strip_background_noise(c, sr=16000)
        lfcc_m, fb_e = compute_lfcc(clean_c, sr=16000)
        lfcc_res = analyze_lfcc_high_freq_artifacts(lfcc_m, fb_e)
        dsp_res = extract_all_dsp_features(clean_c, sr=16000)
        m_score, meta = detector.infer(clean_c, sr=16000)
        risk = scoring_engine.compute_chunk_risk_score(
            m_score,
            lfcc_res['lfcc_artifact_score'],
            dsp_res['pitch_anomaly_score'],
            dsp_res['spectral_anomaly_score']
        )
        prev_ewma = scoring_engine.update_rolling_score(risk, prev_ewma)
        alert, sev, act = scoring_engine.evaluate_alert(prev_ewma, transaction_context="general")
        print(f"Chunk {i+1}: AASIST={m_score:.2f}%, LFCC={lfcc_res['lfcc_artifact_score']:.2f}%, ChunkRisk={risk:.2f}%, EWMARisk={prev_ewma:.2f}%, Severity={sev}, Alert={alert}")
