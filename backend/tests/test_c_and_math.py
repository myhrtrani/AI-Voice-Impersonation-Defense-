import os
import sys
import json
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app

client = TestClient(app)
GENUINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "genuine_validation"))

def run_session(filename, context, is_synthetic=False):
    filepath = os.path.join(GENUINE_DIR, filename)
    print(f"\n{'='*80}\n>>> RUNNING SESSION: {filename} | Context: {context}\n{'='*80}")
    
    # Upload
    with open(filepath, "rb") as f:
        resp = client.post("/calls/upload", data={"transaction_context": context}, files={"file": (filename, f, "audio/wav")})
    
    if resp.status_code != 200:
        return
        
    session_id = resp.json()["session_id"]
    print(f" Session ID: {session_id}")
    
    chunks = []
    with client.websocket_connect(f"/calls/{session_id}/stream") as ws:
        while True:
            data = ws.receive_json()
            if "error" in data:
                break
            if data.get("is_complete"):
                break
            chunks.append(data)
            
            c_idx = len(chunks)
            print(f"  Chunk {c_idx} | Duration: {data.get('features', {}).get('duration_sec', 2.5)}s")
            print(f"    Raw Risk: {data['chunk_risk_score']}% | EWMA Risk: {data['rolling_risk_score']}%")
            print(f"    Severity: {data['severity']} | Alert Fired: {data['alert_fired']}")
            
            if is_synthetic and c_idx == 1:
                f = data.get('features', {})
                print(f"    [MATH DUMP CHUNK 1]")
                print(f"      w_model=0.40, w_lfcc=0.30, w_pitch=0.15, w_spec=0.15")
                # print all keys in features
                print(f"      model_score = {f.get('model_score', f.get('model_engine', '??'))} or maybe it's in top-level?")
                # Let's just dump the JSON of 'features'
                print(f"      features json: {json.dumps(f, indent=2)}")
                
    sum_resp = client.get(f"/calls/{session_id}/summary")
    s_data = sum_resp.json()
    print(f" SQLite Persistence (GET /summary): HTTP {sum_resp.status_code}")
    print(f"  Peak Risk: {s_data.get('peak_risk_score', s_data.get('peak_rolling_risk'))}%")
    print(f"  Avg Raw Risk: {s_data.get('avg_raw_risk')}%")
    print(f"  Avg Rolling Risk: {s_data.get('avg_rolling_risk')}%")
    
    if is_synthetic and len(chunks) >= 2:
        r1 = chunks[0]['chunk_risk_score']
        r2 = chunks[1]['chunk_risk_score']
        e1 = chunks[0]['rolling_risk_score']
        e2 = chunks[1]['rolling_risk_score']
        print(f"\n[DATABASE PARITY CHECK (SYNTHETIC SESSION)]")
        print(f"  Manual Avg Raw = ({r1} + {r2}) / 2 = {(r1+r2)/2:.2f}% | SQLite = {s_data.get('avg_raw_risk')}%")
        print(f"  Manual Avg Rolling = ({e1} + {e2}) / 2 = {(e1+e2)/2:.2f}% | SQLite = {s_data.get('avg_rolling_risk')}%")

if __name__ == "__main__":
    run_session("xtts_voice_clone_en.wav", "fund_transfer", is_synthetic=True)
    run_session("librispeech_male_noisy_heavy.wav", "general", is_synthetic=False)
