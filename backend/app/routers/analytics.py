"""
REST Endpoints for System-Wide Analytics, Historical Incident Logs, and Forensic Auditing.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
import csv
import io
import time

from app.logger import get_logger, log_crash
from app.db import (
    get_analytics_summary,
    get_all_sessions,
    delete_session,
    get_session_summary,
    get_session_history
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])
logger = get_logger("voice_defense.analytics")


@router.get("/overview")
async def get_overview():
    """
    Returns aggregated dashboard statistics:
    - Total calls processed
    - Threat interception rate
    - Critical alerts count
    - Context vulnerability distribution
    - Daily risk trends
    """
    try:
        summary = get_analytics_summary()
        return {
            "status": "success",
            "timestamp": time.time(),
            **summary
        }
    except Exception as e:
        log_crash(e, context="Analytics Overview Endpoint")
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics overview: {str(e)}")


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: Optional[str] = Query(None, description="Filter by context e.g. fund_transfer, otp_share"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: low, medium, high"),
    search: Optional[str] = Query(None, description="Search by session ID or context")
):
    """
    Returns paginated list of analyzed sessions with filter criteria.
    """
    try:
        res = get_all_sessions(
            limit=limit,
            offset=offset,
            context_filter=context,
            risk_filter=risk_level,
            search=search
        )
        return {
            "status": "success",
            **res
        }
    except Exception as e:
        log_crash(e, context="List Sessions Endpoint")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str):
    """
    Deletes a session and its associated metrics & alerts.
    """
    try:
        success = delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or failed to delete")
        logger.info("Session %s deleted successfully via API", session_id)
        return {
            "status": "success",
            "message": f"Session {session_id} successfully deleted",
            "session_id": session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        log_crash(e, context=f"Delete Session Endpoint ({session_id})")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


@router.get("/export")
async def export_audit_log(format: str = Query("json", pattern="^(json|csv)$")):
    """
    Exports all analyzed sessions and aggregate metrics as downloadable JSON or CSV.
    """
    try:
        all_data = get_all_sessions(limit=1000, offset=0)
        sessions = all_data.get("sessions", [])

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "session_id", "mode", "transaction_context", "created_at",
                "status", "peak_risk", "avg_risk", "total_chunks", "alert_count", "highest_severity"
            ])
            for s in sessions:
                writer.writerow([
                    s.get("session_id"),
                    s.get("mode"),
                    s.get("transaction_context"),
                    s.get("created_at"),
                    s.get("status"),
                    s.get("peak_risk"),
                    s.get("avg_risk"),
                    s.get("total_chunks"),
                    s.get("alert_count", 0),
                    s.get("highest_severity", "NONE")
                ])
            csv_content = output.getvalue()
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=voice_sentry_audit_{int(time.time())}.csv"}
            )
        else:
            return {
                "exported_at": time.time(),
                "total_records": len(sessions),
                "records": sessions
            }
    except Exception as e:
        log_crash(e, context="Export Audit Log Endpoint")
        raise HTTPException(status_code=500, detail=f"Failed to export audit logs: {str(e)}")
