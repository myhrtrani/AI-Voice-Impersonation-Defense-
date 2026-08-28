"""
Verification Script for Official NAVER Clova AASIST-L.
"""

import os
import sys
import torch
import librosa
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from official_AASIST_source import Model
from download_official_aasist import GENUINE_DIR

d_args = {
    'architecture': 'AASIST',
    'nb_samp': 64600,
    'first_conv': 128,
    'filts': [70, [1, 32], [32, 32], [32, 24], [24, 24]],
    'gat_dims': [24, 32],
    'pool_ratios': [0.4, 0.5, 0.7, 0.5],
    'temperatures': [2.0, 2.0, 100.0, 100.0]
}

model = Model(d_args)
ckpt = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "models", "weights", "AASIST-L.pth"))
sd = torch.load(ckpt, map_location='cpu', weights_only=True)
model.load_state_dict(sd, strict=True)
model.eval()

def pad(x, max_len=64600):
    x_len = x.shape[0]
    if x_len >= max_len:
        return x[:max_len]
    num_repeats = int(max_len / x_len) + 1
    return np.tile(x, num_repeats)[:max_len]

files = [
    ("librispeech_male_clean.wav", "AUTHENTIC"),
    ("librispeech_female_clean.wav", "AUTHENTIC"),
    ("librispeech_speech_clean.wav", "AUTHENTIC"),
    ("librispeech_male_noisy_ambient.wav", "AUTHENTIC"),
    ("librispeech_male_noisy_heavy.wav", "AUTHENTIC"),
    ("xtts_voice_clone_en.wav", "SYNTHETIC"),
    ("xtts_voice_clone_es.wav", "SYNTHETIC"),
    ("xtts_voice_clone_fr.wav", "SYNTHETIC"),
    ("xtts_voice_clone_de.wav", "SYNTHETIC"),
]

print("\n" + "=" * 105)
print(" OFFICIAL AASIST-L EVALUATION ON GENUINE AUDIO DATASET (N=9)")
print(" Model: NAVER Clova AASIST-L (85,306 parameters, strict=True loaded)")
print("=" * 105)
print(f" {'#':<2} | {'Filename':<34} | {'Ground Truth':<10} | {'Raw Logits [0, 1]':<22} | {'Logit 1 - Logit 0':<18} | {'Softmax P(Spoof)'}")
print("-" * 105)

for idx, (f, gt) in enumerate(files, 1):
    path = os.path.join(GENUINE_DIR, f)
    y, _ = librosa.load(path, sr=16000)
    y_padded = pad(y, 64600)
    tensor_x = torch.from_numpy(y_padded.astype(np.float32)).unsqueeze(0)
    with torch.no_grad():
        last_hidden, out = model(tensor_x)
        probs = torch.softmax(out, dim=-1)
        l0 = out[0, 0].item()
        l1 = out[0, 1].item()
        p1 = probs[0, 1].item()
    print(f" {idx:<2} | {f:<34} | {gt:<10} | [{l0:+.4f}, {l1:+.4f}]         | {l1 - l0:+.4f}             | {p1:.4f}")

print("=" * 105 + "\n")
