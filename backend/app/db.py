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
        
        # System Config Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL NOT NULL
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
        
        cursor.execute("""
        SELECT 
            COUNT(*) as cnt, 
            AVG(chunk_risk_score) as avg_raw,
            AVG(rolling_risk_score) as avg_rolling,
            MAX(chunk_risk_score) as peak_raw,
            MAX(rolling_risk_score) as peak_rolling
        FROM chunk_metrics 
        WHERE session_id = ?
        """, (session_id,))
        stats = cursor.fetchone()
        
        conn.close()
        return {
            "session_id": session["session_id"],
            "mode": session["mode"],
            "transaction_context": session["transaction_context"],
            "created_at": session["created_at"],
            "status": session["status"],
            "total_chunks": stats["cnt"] or 0,
            "peak_risk": round(stats["peak_rolling"] or 0.0, 2),
            "avg_risk": round(stats["avg_rolling"] or 0.0, 2),
            "peak_rolling_risk": round(stats["peak_rolling"] or 0.0, 2),
            "avg_rolling_risk": round(stats["avg_rolling"] or 0.0, 2),
            "peak_raw_risk": round(stats["peak_raw"] or 0.0, 2),
            "avg_raw_risk": round(stats["avg_raw"] or 0.0, 2),
            "alerts_count": len(alerts),
            "alerts": alerts
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


def get_all_sessions(
    limit: int = 50,
    offset: int = 0,
    context_filter: Optional[str] = None,
    risk_filter: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves paginated list of call sessions with associated alert counts."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            s.*,
            (SELECT COUNT(*) FROM alerts a WHERE a.session_id = s.session_id) as alert_count,
            (SELECT MAX(a.severity) FROM alerts a WHERE a.session_id = s.session_id) as highest_severity
        FROM sessions s
        WHERE 1=1
        """
        params = []

        if context_filter and context_filter != "all":
            query += " AND s.transaction_context = ?"
            params.append(context_filter)

        if risk_filter == "high":
            query += f" AND s.peak_risk >= {settings.SCORING.HIGH_RISK_MIN}"
        elif risk_filter == "medium":
            query += f" AND s.peak_risk >= {settings.SCORING.LOW_RISK_MAX} AND s.peak_risk < {settings.SCORING.HIGH_RISK_MIN}"
        elif risk_filter == "low":
            query += f" AND s.peak_risk < {settings.SCORING.LOW_RISK_MAX}"

        if search:
            query += " AND (s.session_id LIKE ? OR s.transaction_context LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Count total matching
        count_query = f"SELECT COUNT(*) as total FROM ({query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["total"]

        query += " ORDER BY s.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "sessions": sessions
        }
    except Exception as e:
        log_crash(e, context="Get All Sessions")
        return {"total": 0, "limit": limit, "offset": offset, "sessions": []}


def delete_session(session_id: str) -> bool:
    """Deletes a session and its associated metrics and alerts from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chunk_metrics WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM alerts WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_crash(e, context=f"Delete Session ({session_id})")
        return False


def get_analytics_summary() -> Dict[str, Any]:
    """Computes comprehensive dashboard analytics and risk aggregates across all sessions."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total Sessions & Overall Risk Stats
        cursor.execute("""
        SELECT 
            COUNT(*) as total_sessions,
            COALESCE(AVG(avg_risk), 0.0) as overall_avg_risk,
            COALESCE(MAX(peak_risk), 0.0) as overall_peak_risk,
            COALESCE(SUM(total_chunks), 0) as total_audio_chunks
        FROM sessions
        """)
        base_stats = dict(cursor.fetchone())

        # Total Alerts & High-Risk Interceptions
        cursor.execute("""
        SELECT 
            COUNT(*) as total_alerts,
            SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical_alerts,
            SUM(CASE WHEN severity = 'WARNING' THEN 1 ELSE 0 END) as warning_alerts
        FROM alerts
        """)
        alert_stats = dict(cursor.fetchone())

        # Threat breakdown by Transaction Context
        cursor.execute("""
        SELECT 
            s.transaction_context,
            COUNT(DISTINCT s.session_id) as session_count,
            COALESCE(AVG(s.peak_risk), 0.0) as avg_peak_risk,
            COALESCE(AVG(s.avg_risk), 0.0) as avg_mean_risk,
            COUNT(a.id) as alert_count,
            SUM(CASE WHEN a.severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count
        FROM sessions s
        LEFT JOIN alerts a ON s.session_id = a.session_id
        GROUP BY s.transaction_context
        """)
        context_breakdown = [dict(row) for row in cursor.fetchall()]

        # Mode Breakdown (Mode A Upload vs Mode B Live)
        cursor.execute("""
        SELECT mode, COUNT(*) as count, COALESCE(AVG(peak_risk), 0.0) as avg_peak_risk
        FROM sessions
        GROUP BY mode
        """)
        mode_breakdown = [dict(row) for row in cursor.fetchall()]

        # Recent 10 Sessions timeline
        cursor.execute("""
        SELECT session_id, mode, transaction_context, created_at, peak_risk, avg_risk, total_chunks
        FROM sessions
        ORDER BY created_at DESC
        LIMIT 10
        """)
        recent_sessions = [dict(row) for row in cursor.fetchall()]

        # Hourly / Daily Activity aggregation (last 7 days or sessions)
        cursor.execute("""
        SELECT 
            strftime('%Y-%m-%d', datetime(created_at, 'unixepoch')) as day,
            COUNT(*) as calls_count,
            COALESCE(AVG(peak_risk), 0.0) as avg_risk,
            COALESCE(MAX(peak_risk), 0.0) as max_risk
        FROM sessions
        GROUP BY day
        ORDER BY day ASC
        LIMIT 14
        """)
        daily_trends = [dict(row) for row in cursor.fetchall()]

        conn.close()

        high_risk_threshold = settings.SCORING.HIGH_RISK_MIN
        critical_count = alert_stats.get("critical_alerts") or 0
        total_sessions = base_stats.get("total_sessions") or 0

        threat_rate = round((critical_count / total_sessions * 100) if total_sessions > 0 else 0.0, 1)

        return {
            "total_sessions": total_sessions,
            "overall_avg_risk": round(base_stats.get("overall_avg_risk") or 0.0, 1),
            "overall_peak_risk": round(base_stats.get("overall_peak_risk") or 0.0, 1),
            "total_audio_chunks": base_stats.get("total_audio_chunks") or 0,
            "total_alerts": alert_stats.get("total_alerts") or 0,
            "critical_alerts": critical_count,
            "warning_alerts": alert_stats.get("warning_alerts") or 0,
            "threat_interception_rate": threat_rate,
            "context_breakdown": context_breakdown,
            "mode_breakdown": mode_breakdown,
            "recent_sessions": recent_sessions,
            "daily_trends": daily_trends,
            "high_risk_threshold": high_risk_threshold,
            "low_risk_threshold": settings.SCORING.LOW_RISK_MAX
        }
    except Exception as e:
        log_crash(e, context="Get Analytics Summary")
        return {
            "total_sessions": 0,
            "overall_avg_risk": 0.0,
            "overall_peak_risk": 0.0,
            "total_audio_chunks": 0,
            "total_alerts": 0,
            "critical_alerts": 0,
            "warning_alerts": 0,
            "threat_interception_rate": 0.0,
            "context_breakdown": [],
            "mode_breakdown": [],
            "recent_sessions": [],
            "daily_trends": []
        }


def get_persisted_config() -> Dict[str, Any]:
    """Loads custom saved configuration from system_config table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM system_config")
        rows = cursor.fetchall()
        conn.close()
        import json
        config = {}
        for row in rows:
            try:
                config[row["key"]] = json.loads(row["value"])
            except Exception:
                config[row["key"]] = row["value"]
        return config
    except Exception as e:
        logger.warning("Could not load persisted config: %s", e)
        return {}


def save_persisted_config(config_dict: Dict[str, Any]) -> bool:
    """Saves custom configuration key-value pairs into system_config table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = time.time()
        import json
        for k, v in config_dict.items():
            val_str = json.dumps(v)
            cursor.execute(
                "INSERT OR REPLACE INTO system_config (key, value, updated_at) VALUES (?, ?, ?)",
                (k, val_str, now)
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_crash(e, context="Save Persisted Config", extra_details=config_dict)
        return False

