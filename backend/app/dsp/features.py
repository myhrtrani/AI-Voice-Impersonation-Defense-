"""
DSP Acoustic Feature Extraction Module.
Extracts:
  - Pitch (F0) variance and mean
  - Jitter (detrended Relative Average Perturbation / cycle perturbation)
  - Spectral Flatness (speech-band harmonic flatness)
  - Spectral Centroid
  - Pause / Silence Ratio

Note: Shimmer is explicitly excluded from this build per specifications.
"""

import numpy as np
import librosa
from typing import Dict, Any


def extract_pitch_and_jitter(
    y: np.ndarray,
    sr: int = 16000,
    fmin: float = 65.0,
    fmax: float = 400.0,
    hop_length: int = 160
) -> Dict[str, float]:
    """
    Extracts fundamental frequency (F0) pitch variance and detrended micro-jitter.
    
    Acoustic & Mathematical Context:
    - Standard clinical jitter (e.g. Praat Relative Average Perturbation / RAP) measures
      cycle-to-cycle random perturbation AFTER removing macro intonation trends (the natural
      rising/falling pitch contour across a sentence).
    - Without detrending, intentional conversational intonation elevates raw frame-to-frame delta.
    - Here we use a 3-point local perturbation operator: |T_i - 2*T_{i+1} + T_{i+2}| / (3 * mean(T))
      which cancels out linear intonation slopes and isolates true vocal cord micro-instability.
      
    Typical Reference Ranges:
    - Natural human vocal micro-jitter: ~0.4% to 2.5% (detrended)
    - AI / Neural vocoder flat synthesis: < 0.25% (unnatural mathematical perfection)
    - Glitched / noisy audio: > 3.5%
    """
    if len(y) < hop_length * 4:
        return {"pitch_mean": 0.0, "pitch_variance": 0.0, "jitter": 0.0, "pitch_anomaly_score": 0.0}
        
    try:
        # Fast YIN algorithm for pitch tracking on CPU
        f0 = librosa.yin(y, fmin=fmin, fmax=fmax, sr=sr, hop_length=hop_length)
        
        # Filter voiced frames within human vocal frequency bounds
        voiced_f0 = f0[(f0 >= fmin) & (f0 <= fmax) & (~np.isnan(f0))]
        
        if len(voiced_f0) < 5:
            return {"pitch_mean": 0.0, "pitch_variance": 0.0, "jitter": 0.0, "pitch_anomaly_score": 0.0}
            
        pitch_mean = float(np.mean(voiced_f0))
        pitch_var = float(np.var(voiced_f0))
        pitch_std = float(np.std(voiced_f0))
        
        # Convert pitch track to pitch periods T_i = 1 / f0_i (in seconds)
        periods = 1.0 / voiced_f0
        mean_period = np.mean(periods)
        
        if len(periods) >= 3 and mean_period > 0:
            # 3-point detrended relative average perturbation (RAP)
            # Cancels out linear macro-intonation rise/fall so we measure true micro-jitter
            second_diffs = np.abs(periods[:-2] - 2 * periods[1:-1] + periods[2:])
            jitter = float((np.mean(second_diffs) / (3.0 * mean_period)) * 100.0)
        elif len(periods) >= 2 and mean_period > 0:
            jitter = float((np.mean(np.abs(np.diff(periods))) / mean_period) * 100.0)
        else:
            jitter = 0.0
            
        # Calibrated Pitch & Jitter Anomaly Score (0.0 to 100.0)
        # 1. Robotic Pitch Flatness: Human conversational speech has std > 12 Hz. Flat synthetic speech < 5 Hz.
        flatness_anomaly = np.clip((12.0 - pitch_std) / 10.0, 0.0, 1.0)
        
        # 2. Hyper-smooth Jitter (< 0.20%) or Extreme Jitter (> 3.5%)
        if jitter < 0.25:
            jitter_anomaly = np.clip((0.25 - jitter) / 0.25, 0.0, 1.0)
        elif jitter > 3.0:
            jitter_anomaly = np.clip((jitter - 3.0) / 3.0, 0.0, 1.0)
        else:
            jitter_anomaly = 0.0
            
        pitch_anomaly_score = float(np.clip((0.6 * flatness_anomaly + 0.4 * jitter_anomaly) * 100.0, 0.0, 100.0))
        
        return {
            "pitch_mean": round(pitch_mean, 2),
            "pitch_variance": round(pitch_var, 2),
            "jitter": round(jitter, 3),
            "pitch_anomaly_score": round(pitch_anomaly_score, 2)
        }
    except Exception:
        return {"pitch_mean": 0.0, "pitch_variance": 0.0, "jitter": 0.0, "pitch_anomaly_score": 0.0}


def extract_spectral_features(
    y: np.ndarray,
    sr: int = 16000,
    n_fft: int = 512,
    hop_length: int = 160
) -> Dict[str, float]:
    """
    Extracts speech-band spectral flatness and spectral centroid.
    
    Acoustic & Mathematical Context:
    - Spectral Flatness (Wiener entropy) = Geometric Mean / Arithmetic Mean of power spectrum.
    - Evaluated across the primary speech band (0 to 4000 Hz) to avoid unvoiced high-frequency
      noise floor inflation.
    - Pure harmonic speech (vowels) concentrates energy in sharp peaks (Flatness ~ 0.01 - 0.15).
    - Vocoder noise / unvoiced hiss / metallic artifacts exhibit elevated flatness (> 0.25).
    """
    if len(y) < n_fft:
        return {"spectral_flatness": 0.0, "spectral_centroid": 0.0, "spectral_anomaly_score": 0.0}
        
    try:
        # Compute STFT
        stft = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
        power_spec = np.abs(stft) ** 2  # (n_fft // 2 + 1, n_frames)
        
        # Restrict spectral flatness calculation to speech band (0 to 4000 Hz, first 128 bins)
        speech_bins = min(128, power_spec.shape[0])
        speech_power = power_spec[:speech_bins, :]
        
        # Geometric mean over speech band with log-domain stability
        log_power = np.log(np.maximum(speech_power, 1e-10))
        geom_mean = np.exp(np.mean(log_power, axis=0))
        arith_mean = np.mean(speech_power, axis=0) + 1e-10
        flatness_per_frame = geom_mean / arith_mean
        
        # Energy-weighted average across frames (gives more weight to active voiced phonemes)
        frame_energies = np.sum(speech_power, axis=0)
        total_energy = np.sum(frame_energies) + 1e-10
        mean_flatness = float(np.sum(flatness_per_frame * frame_energies) / total_energy)
        
        # Full-band Spectral Centroid (frequency center of mass)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)
        mean_centroid = float(np.mean(centroid))
        
        # Spectral anomaly scoring (0 - 100)
        flatness_anomaly = np.clip((mean_flatness - 0.12) / 0.25, 0.0, 1.0)
        
        if mean_centroid > 3200:
            centroid_anomaly = np.clip((mean_centroid - 3200) / 1500, 0.0, 1.0)
        elif mean_centroid < 800 and mean_centroid > 0:
            centroid_anomaly = np.clip((800 - mean_centroid) / 500, 0.0, 1.0)
        else:
            centroid_anomaly = 0.0
            
        spectral_anomaly_score = float(np.clip((0.6 * flatness_anomaly + 0.4 * centroid_anomaly) * 100.0, 0.0, 100.0))
        
        return {
            "spectral_flatness": round(mean_flatness, 5),
            "spectral_centroid": round(mean_centroid, 2),
            "spectral_anomaly_score": round(spectral_anomaly_score, 2)
        }
    except Exception:
        return {"spectral_flatness": 0.0, "spectral_centroid": 0.0, "spectral_anomaly_score": 0.0}


def extract_pause_patterns(
    y: np.ndarray,
    sr: int = 16000,
    top_db: float = 30.0,
    hop_length: int = 160
) -> Dict[str, float]:
    """
    Analyzes silence vs active speech ratio and vocal pause patterns.
    """
    if len(y) == 0:
        return {"silence_ratio": 0.0, "active_speech_ratio": 0.0}
        
    try:
        non_silent = librosa.effects.split(y, top_db=top_db, hop_length=hop_length)
        if len(non_silent) == 0:
            return {"silence_ratio": 1.0, "active_speech_ratio": 0.0}
            
        active_samples = sum(end - start for start, end in non_silent)
        total_samples = len(y)
        active_ratio = float(active_samples / total_samples)
        silence_ratio = float(1.0 - active_ratio)
        
        return {
            "silence_ratio": round(silence_ratio, 3),
            "active_speech_ratio": round(active_ratio, 3)
        }
    except Exception:
        return {"silence_ratio": 0.0, "active_speech_ratio": 1.0}


def extract_all_dsp_features(
    y: np.ndarray,
    sr: int = 16000,
    n_fft: int = 512,
    hop_length: int = 160
) -> Dict[str, Any]:
    """
    Comprehensive DSP feature extraction orchestrator for a single audio chunk.
    """
    pitch_jitter = extract_pitch_and_jitter(y, sr=sr, hop_length=hop_length)
    spectral = extract_spectral_features(y, sr=sr, n_fft=n_fft, hop_length=hop_length)
    pause = extract_pause_patterns(y, sr=sr, hop_length=hop_length)
    
    return {
        **pitch_jitter,
        **spectral,
        **pause
    }
