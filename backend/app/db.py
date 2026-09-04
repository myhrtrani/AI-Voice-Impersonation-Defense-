"""
SQLite Database Layer for Call Sessions, Real-Time Chunk Metrics, and Security Alerts.
Uses standard Python sqlite3 with thread-safe / auto-initialization.
"""

import sqlite3
import time
from typing import Dict, Any, List, Optional
from app.config import settings
from app.logger import get_logger, log_crash

logger = get_logger("voice_defense.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite schema."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Sessions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            transaction_context TEXT NOT NULL DEFAULT 'general',
            created_at REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            peak_risk REAL DEFAULT 0.0,
            avg_risk REAL DEFAULT 0.0,
            total_chunks INTEGER DEFAULT 0
        )
        """)
        
        # Chunk Metrics Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunk_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            chunk_risk_score REAL NOT NULL,
            rolling_risk_score REAL NOT NULL,
            model_score REAL NOT NULL,
            lfcc_artifact_score REAL NOT NULL,
            pitch_variance REAL NOT NULL,
            pitch_mean REAL DEFAULT 0.0,
            jitter REAL NOT NULL,
            spectral_flatness REAL NOT NULL,
            spectral_centroid REAL NOT NULL,
            silence_ratio REAL NOT NULL,
            noise_stripped INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
        """)
        
        # Alerts Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            severity TEXT NOT NULL,
            risk_score REAL NOT NULL,
            transaction_context TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
        """)
        
        conn.commit()
        conn.close()
    except Exception as e:
        log_crash(e, context="Database Schema Initialization (init_db)")
        raise e


# Auto-initialize DB on import
init_db()


def create_session(session_id: str, mode: str, transaction_context: str = "general") -> Dict[str, Any]:
    try:
        init_db()
        conn = get_db_connection()
        cursor = conn.cursor()
        now = time.time()
        cursor.execute(
            "INSERT OR REPLACE INTO sessions (session_id, mode, transaction_context, created_at, status) VALUES (?, ?, ?, ?, 'active')",
            (session_id, mode, transaction_context, now)
        )
        conn.commit()
        conn.close()
        return {"session_id": session_id, "mode": mode, "transaction_context": transaction_context, "created_at": now}
    except Exception as e:
        log_crash(e, context=f"Create Session ({session_id})", extra_details={"mode": mode, "context": transaction_context})
        raise e


def update_session_context(session_id: str, new_context: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET transaction_context = ? WHERE session_id = ?", (new_context, session_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_crash(e, context=f"Update Session Context ({session_id})", extra_details={"new_context": new_context})
        return False


def record_chunk_metric(session_id: str, metric: Dict[str, Any]):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO chunk_metrics (
            session_id, chunk_index, timestamp, chunk_risk_score, rolling_risk_score,
            model_score, lfcc_artifact_score, pitch_variance, pitch_mean, jitter,
            spectral_flatness, spectral_centroid, silence_ratio, noise_stripped
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            metric.get("chunk_index", 0),
            metric.get("timestamp", time.time()),
            metric.get("chunk_risk_score", 0.0),
            metric.get("rolling_risk_score", 0.0),
            metric.get("model_score", 0.0),
            metric.get("lfcc_artifact_score", 0.0),
            metric.get("pitch_variance", 0.0),
            metric.get("pitch_mean", 0.0),
            metric.get("jitter", 0.0),
            metric.get("spectral_flatness", 0.0),
            metric.get("spectral_centroid", 0.0),
            metric.get("silence_ratio", 0.0),
            1 if metric.get("noise_stripped", True) else 0
        ))
        
        cursor.execute("""
        UPDATE sessions 
        SET total_chunks = total_chunks + 1,
            peak_risk = MAX(peak_risk, ?),
            avg_risk = (SELECT AVG(rolling_risk_score) FROM chunk_metrics WHERE session_id = ?)
        WHERE session_id = ?
        """, (metric.get("rolling_risk_score", 0.0), session_id, session_id))
        
        conn.commit()
        conn.close()
    except Exception as e:
        log_crash(e, context=f"Record Chunk Metric ({session_id})", extra_details=metric)
        raise e


def record_alert(session_id: str, alert: Dict[str, Any]):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO alerts (session_id, chunk_index, timestamp, severity, risk_score, transaction_context, recommended_action)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            alert.get("chunk_index", 0),
            alert.get("timestamp", time.time()),
            alert.get("severity", "WARNING"),
            alert.get("risk_score", 0.0),
            alert.get("transaction_context", "general"),
            alert.get("recommended_action", "")
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        log_crash(e, context=f"Record Alert ({session_id})", extra_details=alert)
        raise e


def get_session_summary(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session = cursor.fetchone()
        if not session:
            conn.close()
            return None
            
        cursor.execute("SELECT * FROM alerts WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
        alerts = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM chunk_metrics WHERE session_id = ? ORDER BY chunk_index ASC", (session_id,))
        chunks = [dict(row) for row in cursor.fetchall()]
        
        conn.close()

        total_chunks = len(chunks)
        if total_chunks == 0:
            return {
                "session_id": session["session_id"],
                "mode": session["mode"],
                "transaction_context": session["transaction_context"],
                "created_at": session["created_at"],
                "status": session["status"],
                "total_chunks": 0,
                "peak_risk": 0.0,
                "avg_risk": 0.0,
                "peak_rolling_risk": 0.0,
                "avg_rolling_risk": 0.0,
                "peak_raw_risk": 0.0,
                "avg_raw_risk": 0.0,
                "human_ratio": 100.0,
                "suspicious_ratio": 0.0,
                "ai_ratio": 0.0,
                "human_chunks_cnt": 0,
                "suspicious_chunks_cnt": 0,
                "ai_chunks_cnt": 0,
                "verdict": "GENUINE_HUMAN",
                "verdict_label": "Authentic Human Call Verified",
                "alerts_count": 0,
                "alerts": []
            }

        rolling_scores = [c.get("rolling_risk_score") or 0.0 for c in chunks]
        raw_scores = [c.get("chunk_risk_score") or 0.0 for c in chunks]

        # Calculate Sustained Peak Risk (filters out single 1-frame mic startup glitches)
        if total_chunks == 1:
            sustained_peak = rolling_scores[0]
        else:
            # 2-chunk rolling window max
            sustained_scores = [0.5 * (rolling_scores[i] + rolling_scores[i+1]) for i in range(total_chunks - 1)]
            sustained_peak = max(sustained_scores)

        # Count chunk distributions
        human_chunks_cnt = sum(1 for s in rolling_scores if s < 40.0)
        suspicious_chunks_cnt = sum(1 for s in rolling_scores if 40.0 <= s < 60.0)
        ai_chunks_cnt = sum(1 for s in rolling_scores if s >= 60.0)

        human_ratio = round((human_chunks_cnt / total_chunks) * 100.0, 1)
        suspicious_ratio = round((suspicious_chunks_cnt / total_chunks) * 100.0, 1)
        ai_ratio = round((ai_chunks_cnt / total_chunks) * 100.0, 1)

        avg_rolling = round(float(sum(rolling_scores) / total_chunks), 2)
        avg_raw = round(float(sum(raw_scores) / total_chunks), 2)

        # Multi-chunk authenticity & verdict evaluation:
        # 1. Full AI Deepfake Call (>= 50% AI chunks):
        if ai_ratio >= 50.0:
            effective_peak = round(max(sustained_peak, max(rolling_scores)), 2)
            verdict = "FULL_AI_CALL"
            verdict_label = "Critical Voice Impersonation Detected"

        # 2. Targeted Voice Injection Attack (AI detected is >= 35% or sustained AI peak >= 60%):
        elif ai_ratio >= 35.0 or (ai_chunks_cnt >= 2 and sustained_peak >= 60.0):
            effective_peak = round(max(sustained_peak, max(rolling_scores)), 2)
            verdict = "TARGETED_AI_INJECTION"
            verdict_label = "Targeted Voice Injection Attack Detected"

        # 3. Dominant Genuine Human Call (human_ratio >= 65% and AI ratio < 35% and no sustained critical peak):
        elif human_ratio >= 65.0 and ai_ratio < 35.0 and sustained_peak < 60.0:
            effective_peak = round(min(sustained_peak, 35.0) if sustained_peak >= 55.0 else sustained_peak, 2)
            verdict = "GENUINE_HUMAN"
            verdict_label = "Authentic Human Call Verified"

        # 4. Borderline / Suspicious Audio:
        elif avg_rolling >= 45.0 or suspicious_ratio >= 40.0:
            effective_peak = round(sustained_peak, 2)
            verdict = "SUSPICIOUS_CALL"
            verdict_label = "Voice Impersonation Warning"

        # Default fallback
        else:
            effective_peak = round(sustained_peak, 2)
            verdict = "GENUINE_HUMAN" if human_ratio >= 60.0 else "SUSPICIOUS_CALL"
            verdict_label = "Authentic Human Call Verified" if human_ratio >= 60.0 else "Voice Impersonation Warning"

        filtered_alerts = alerts if verdict != "GENUINE_HUMAN" else []

        return {
            "session_id": session["session_id"],
            "mode": session["mode"],
            "transaction_context": session["transaction_context"],
            "created_at": session["created_at"],
            "status": session["status"],
            "total_chunks": total_chunks,
            "peak_risk": effective_peak,
            "avg_risk": avg_rolling,
            "peak_rolling_risk": effective_peak,
            "avg_rolling_risk": avg_rolling,
            "peak_raw_risk": round(max(raw_scores), 2),
            "avg_raw_risk": avg_raw,
            "human_ratio": human_ratio,
            "suspicious_ratio": suspicious_ratio,
            "ai_ratio": ai_ratio,
            "human_chunks_cnt": human_chunks_cnt,
            "suspicious_chunks_cnt": suspicious_chunks_cnt,
            "ai_chunks_cnt": ai_chunks_cnt,
            "verdict": verdict,
            "verdict_label": verdict_label,
            "alerts_count": len(filtered_alerts),
            "alerts": filtered_alerts
        }
    except Exception as e:
        log_crash(e, context=f"Get Session Summary ({session_id})")
        return None


def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunk_metrics WHERE session_id = ? ORDER BY chunk_index ASC", (session_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        log_crash(e, context=f"Get Session History ({session_id})")
        return []
