"""
Audio Sample Generator for Testing & Calibrating Voice Impersonation Detector.

Acoustic Physical Modeling:
1. sample_human_clean.wav: Human vocal tract simulation using a Rosenberg smooth glottal flow wave,
   natural micro-jitter, intonation phrase dynamics, and F1/F2/F3 formant filtering with steep -12dB/octave high-frequency roll-off.
2. sample_synthetic_clone.wav: Neural vocoder / AI clone simulation with high-frequency vocoder phase artifacts (5.5-7.5kHz),
   rigid zero-jitter pitch (<0.1%), and mechanical envelope transitions.
3. sample_human_noisy.wav: Human speech mixed with realistic background noise for noise-stripping validation.
"""

import os
import numpy as np
import scipy.signal
import soundfile as sf

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)


def generate_formant_speech(
    duration: float = 7.5,
    sr: int = 16000,
    base_f0: float = 135.0,
    is_synthetic: bool = False
) -> np.ndarray:
    """
    Synthesizes speech-like audio with acoustic physics formants.
    """
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    if not is_synthetic:
        # Natural human speech: dynamic intonation contour + natural vocal jitter
        # Phrase intonation contour (rises and falls naturally across sentences)
        pitch_contour = base_f0 + 18.0 * np.sin(2 * np.pi * 0.4 * t) + 8.0 * np.sin(2 * np.pi * 0.9 * t)
        
        # Natural micro-jitter (~0.8% random perturbation)
        jitter_noise = np.random.normal(0, 0.008 * base_f0, len(t))
        f0_track = pitch_contour + jitter_noise
        
        # Continuous phase integration
        phase = 2 * np.pi * np.cumsum(f0_track) / sr
        
        # Smooth glottal source with natural -12dB/octave acoustic rolloff
        glottal = (
            1.0 * np.sin(phase) +
            0.50 * np.sin(2 * phase) +
            0.25 * np.sin(3 * phase) +
            0.12 * np.sin(4 * phase) +
            0.06 * np.sin(5 * phase) +
            0.03 * np.sin(6 * phase)
        )
        
        # Resonant Formant Filters (/a/ vowel resonances: 700Hz, 1220Hz, 2500Hz)
        b1, a1 = scipy.signal.iirpeak(700.0, 5.0, fs=sr)
        b2, a2 = scipy.signal.iirpeak(1220.0, 6.0, fs=sr)
        b3, a3 = scipy.signal.iirpeak(2500.0, 8.0, fs=sr)
        
        # Lowpass filter above 3600 Hz to match natural human vocal tract acoustics
        b_lp, a_lp = scipy.signal.butter(4, 3600.0, btype='low', fs=sr)
        
        filtered = (
            0.55 * scipy.signal.lfilter(b1, a1, glottal) +
            0.30 * scipy.signal.lfilter(b2, a2, glottal) +
            0.15 * scipy.signal.lfilter(b3, a3, glottal)
        )
        speech = scipy.signal.lfilter(b_lp, a_lp, filtered)
        
        # Natural conversational cadence / breath pauses
        cadence = np.clip(np.sin(2 * np.pi * 0.35 * t) ** 2, 0.08, 1.0)
        speech = speech * cadence
        
        speech = speech / (np.max(np.abs(speech)) + 1e-6) * 0.80
        return speech.astype(np.float32)

    else:
        # Synthetic AI Clone / Neural Vocoder Simulation:
        # 1. Robotic, flat pitch (< 1.5 Hz variance)
        f0_track = np.full_like(t, base_f0) + 0.8 * np.sin(2 * np.pi * 0.15 * t)
        phase = 2 * np.pi * np.cumsum(f0_track) / sr
        
        # 2. Dense synthetic harmonics with elevated high-frequency plateau (HiFi-GAN / vocoder ripple)
        harmonics = np.zeros_like(t)
        for h in range(1, 28):
            weight = 1.0 / (h ** 0.6)  # Flatter decay than human vocal cords
            harmonics += weight * np.sin(h * phase)
            
        # 3. Upper-band vocoder phase ripple / carrier artifacts (5.5kHz - 7.5kHz buzz)
        vocoder_artifact = 0.28 * np.sin(2 * np.pi * 5800 * t) + 0.24 * np.sin(2 * np.pi * 6900 * t)
        
        speech = harmonics + vocoder_artifact
        cadence = np.clip(np.sin(2 * np.pi * 0.4 * t) ** 4, 0.2, 1.0)
        speech = speech * cadence
        
        speech = speech / (np.max(np.abs(speech)) + 1e-6) * 0.80
        return speech.astype(np.float32)


def generate_all_samples():
    sr = 16000
    print("Generating calibrated audio samples in backend/samples/ ...")
    
    # 1. Human clean
    human_clean = generate_formant_speech(duration=7.5, sr=sr, base_f0=135.0, is_synthetic=False)
    p1 = os.path.join(SAMPLES_DIR, "sample_human_clean.wav")
    sf.write(p1, human_clean, sr)
    print(f"Saved: {p1} ({len(human_clean)/sr:.1f}s)")
    
    # 2. Synthetic AI clone
    synthetic_clone = generate_formant_speech(duration=7.5, sr=sr, base_f0=135.0, is_synthetic=True)
    p2 = os.path.join(SAMPLES_DIR, "sample_synthetic_clone.wav")
    sf.write(p2, synthetic_clone, sr)
    print(f"Saved: {p2} ({len(synthetic_clone)/sr:.1f}s)")
    
    # 3. Human noisy (Human clean + ambient office / fan / mic noise)
    noise = np.random.normal(0, 0.08, len(human_clean)) + 0.05 * np.sin(2 * np.pi * 120 * np.linspace(0, 7.5, len(human_clean)))
    human_noisy = human_clean + noise
    human_noisy = human_noisy / (np.max(np.abs(human_noisy)) + 1e-6) * 0.80
    p3 = os.path.join(SAMPLES_DIR, "sample_human_noisy.wav")
    sf.write(p3, human_noisy, sr)
    print(f"Saved: {p3} ({len(human_noisy)/sr:.1f}s)")
    
    print("All samples regenerated successfully.")


if __name__ == "__main__":
    generate_all_samples()
