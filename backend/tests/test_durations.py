import os
import sys
import json
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app

client = TestClient(app)
GENUINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "genuine_validation"))

def run_session(filename):
    filepath = os.path.join(GENUINE_DIR, filename)
    print(f"\n{'='*80}\n>>> RUNNING SESSION: {filename}\n{'='*80}")
    
    with open(filepath, "rb") as f:
        resp = client.post("/calls/upload", data={"transaction_context": "general"}, files={"file": (filename, f, "audio/wav")})
    
    session_id = resp.json()["session_id"]
    chunks = []
    with client.websocket_connect(f"/calls/{session_id}/stream") as ws:
        while True:
            data = ws.receive_json()
            if "error" in data:
                print("ERROR:", data["error"])
                break
            chunks.append(data)
            if data.get("is_complete"):
                break
            
    print(f"Total Chunks Processed: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"Chunk {i+1}:")
        print(f"  actual_chunk_duration: {c.get('actual_chunk_duration')}")
        print(f"  actual_chunk_samples: {c.get('actual_chunk_samples')}")
        print(f"  total_audio_duration: {c.get('total_audio_duration')}")
        print(f"  is_padded: {c.get('is_padded')}")
        print(f"  nominal_window_sec: {c.get('nominal_window_sec')}")
        print(f"  elapsed_seconds: {c.get('elapsed_seconds')}")

if __name__ == "__main__":
    run_session("librispeech_female_clean.wav")
    run_session("librispeech_male_noisy_heavy.wav")
