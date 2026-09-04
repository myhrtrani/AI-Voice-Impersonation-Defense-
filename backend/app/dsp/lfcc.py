"""
Linear Frequency Cepstral Coefficients (LFCC) Extraction & High-Frequency Artifact Scanner.

Technical Context:
Standard MFCC (Mel-Frequency Cepstral Coefficients) compresses higher frequencies using a
logarithmic / mel scale, mimicking human auditory perception. While ideal for ASR (speech recognition),
this compression discards fine spectral resolution in upper frequency bands (4kHz - 8kHz).

Neural vocoders (e.g. HiFiGAN, WaveGlow, VITS, Diffusion TTS) reconstruct high-frequency bands
with characteristic synthesis artifacts: periodic buzz, checkerboard grid anomalies, unnatural
spectral flatness, and unnatural high-band energy distribution.

LFCC uses LINEARLY spaced filterbanks across the full Nyquist range, preserving high-frequency
resolution so neural vocoder artifacts can be detected with high precision.
"""

import numpy as np
from scipy.fftpack import dct
import librosa
from typing import Dict, Any, Tuple


def create_linear_filterbank(
    n_filters: int = 30,
    n_fft: int = 512,
    sr: int = 16000,
    f_min: float = 0.0,
    f_max: float = 8000.0
) -> np.ndarray:
    """
    Constructs a linear-spaced triangular filterbank matrix.
    """
    f_max = min(f_max, sr / 2.0)
    linear_freqs = np.linspace(f_min, f_max, n_filters + 2)
    fft_freqs = np.linspace(0, sr / 2.0, n_fft // 2 + 1)
    filterbank = np.zeros((n_filters, len(fft_freqs)))
    
    for m in range(1, n_filters + 1):
        f_left = linear_freqs[m - 1]
        f_center = linear_freqs[m]
        f_right = linear_freqs[m + 1]
        
        # Rising slope
        up_idx = np.where((fft_freqs >= f_left) & (fft_freqs <= f_center))[0]
        if len(up_idx) > 0 and (f_center - f_left) > 0:
            filterbank[m - 1, up_idx] = (fft_freqs[up_idx] - f_left) / (f_center - f_left)
            
        # Falling slope
        down_idx = np.where((fft_freqs >= f_center) & (fft_freqs <= f_right))[0]
        if len(down_idx) > 0 and (f_right - f_center) > 0:
            filterbank[m - 1, down_idx] = (f_right - fft_freqs[down_idx]) / (f_right - f_center)
            
    return filterbank


def compute_lfcc(
    y: np.ndarray,
    sr: int = 16000,
    n_lfcc: int = 20,
    n_filters: int = 30,
    n_fft: int = 512,
    hop_length: int = 160,
    f_min: float = 50.0,
    f_max: float = 8000.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes Linear Frequency Cepstral Coefficients (LFCC) and filterbank log energies.
    
    Returns:
        lfcc: Array of shape (n_lfcc, n_frames)
        filterbank_energies: Array of shape (n_filters, n_frames)
    """
    if len(y) == 0:
        return np.zeros((n_lfcc, 1)), np.zeros((n_filters, 1))
        
    stft = librosa.stft(y=y, n_fft=n_fft, hop_length=hop_length, win_length=n_fft, window='hamming')
    power_spec = np.abs(stft) ** 2
    
    fb = create_linear_filterbank(n_filters=n_filters, n_fft=n_fft, sr=sr, f_min=f_min, f_max=f_max)
    fb_energies = np.dot(fb, power_spec)
    
    log_fb_energies = np.log(np.maximum(fb_energies, 1e-10))
    lfcc = dct(log_fb_energies, type=2, axis=0, norm='ortho')[:n_lfcc, :]
    
    return lfcc, log_fb_energies


def analyze_lfcc_high_freq_artifacts(
    lfcc: np.ndarray,
    log_fb_energies: np.ndarray,
    n_filters: int = 30
) -> Dict[str, float]:
    """
    Analyzes high-frequency cepstral and spectral regions for neural vocoder artifacts.
    
    Returns:
        Dictionary with:
            - lfcc_artifact_score (0.0 to 100.0): High-frequency vocoder anomaly index
            - high_band_ratio: Ratio of upper linear band energy (4.8kHz - 8kHz) to total energy
            - upper_cepstral_var: Variance of upper LFCC coefficients (coeffs 10-20)
            - lfcc_delta_smoothness: Dynamic variability of frame-to-frame cepstral transitions
    """
    if lfcc.shape[1] < 2:
        return {
            "lfcc_artifact_score": 0.0,
            "high_band_ratio": 0.0,
            "upper_cepstral_var": 0.0,
            "lfcc_delta_smoothness": 0.0
        }
        
    n_lfcc, n_frames = lfcc.shape
    
    # 1. Upper linear band energy ratio (upper 40% of linear filters, ~4.8kHz to 8kHz)
    high_band_start = int(n_filters * 0.60)
    high_band_power = np.exp(log_fb_energies[high_band_start:, :])
    total_power = np.exp(log_fb_energies)
    high_band_ratio = float(np.mean(np.sum(high_band_power, axis=0) / (np.sum(total_power, axis=0) + 1e-8)))
    
    # 2. Upper cepstral coefficient variance (indices 10 to n_lfcc-1)
    upper_coeffs = lfcc[min(10, n_lfcc - 1):, :]
    upper_var = float(np.mean(np.var(upper_coeffs, axis=1)))
    
    # 3. Dynamic delta smoothness (Human speech intonation produces high delta variance > 3.0;
    #    Robotic flat synthesis produces unnaturally uniform delta variance < 2.0)
    lfcc_deltas = np.diff(lfcc, axis=1)
    delta_variance = float(np.mean(np.var(lfcc_deltas, axis=1)))
    
    # 4. Calibration:
    # High-band anomaly (natural voice has < 0.01 energy above 4.8kHz; vocoders elevate upper energy)
    high_band_anomaly = np.clip((high_band_ratio - 0.010) / 0.035, 0.0, 1.0)
    
    # Upper cepstral anomaly (vocoder harmonic ripple)
    cepstral_anomaly = np.clip(upper_var / 0.60, 0.0, 1.0)
    
    # Dynamic smoothness anomaly (low delta movement in synthetic voice)
    if delta_variance < 2.5:
        dyn_anomaly = np.clip((2.5 - delta_variance) / 2.0, 0.0, 1.0)
    else:
        dyn_anomaly = 0.0
        
    # Blended LFCC artifact score (0.0 - 100.0)
    raw_lfcc_score = (0.50 * high_band_anomaly + 0.25 * cepstral_anomaly + 0.25 * dyn_anomaly) * 100.0
    lfcc_artifact_score = float(np.clip(raw_lfcc_score, 0.0, 100.0))
    
    return {
        "lfcc_artifact_score": round(lfcc_artifact_score, 2),
        "high_band_ratio": round(high_band_ratio, 4),
        "upper_cepstral_var": round(upper_var, 4),
        "lfcc_delta_smoothness": round(delta_variance, 4)
    }
