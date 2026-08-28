"""
Seed preset sample files to uploads/ directory for instant 1-click Mode A testing.
"""

import os
import shutil
from app.db import create_session

SAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "samples"))
UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)

presets = [
    {"file": "sample_human_clean.wav", "session_id": "session_preset_clean", "context": "general"},
    {"file": "sample_human_noisy.wav", "session_id": "session_preset_noisy", "context": "general"},
    {"file": "sample_synthetic_clone.wav", "session_id": "session_preset_synthetic", "context": "otp_share"},
]


def seed():
    for p in presets:
        src = os.path.join(SAMPLES_DIR, p["file"])
        dst = os.path.join(UPLOADS_DIR, f"{p['session_id']}.wav")
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            try:
                create_session(p["session_id"], "mode_a_upload", p["context"])
            except Exception:
                pass
            print(f"Seeded: {dst}")


if __name__ == "__main__":
    seed()
