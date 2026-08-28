"""
REST Endpoints for Call Sessions, Upload (Mode A), Start-Live (Mode B), Summaries & Context.
"""

import uuid
import time
import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.config import settings
from app.db import (
    create_session,
    update_session_context,
    get_session_summary,
    get_session_history
)

router = APIRouter(prefix=settings.API_PREFIX, tags=["Calls"])

# Directory to temporarily store uploaded audio files for Mode A simulated replay
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class StartLiveRequest(BaseModel):
    transaction_context: Optional[str] = "general"


class UpdateContextRequest(BaseModel):
    transaction_context: str


@router.post("/upload")
async def upload_call_recording(
    file: UploadFile = File(...),
    transaction_context: str = Form("general")
):
    """
    Mode A Endpoint: Accepts an audio file (.wav, .mp3, .ogg, .m4a, .webm),
    creates a session, and saves the file for synchronized streaming replay.
    """
    valid_contexts = ["general", "credential_reset", "otp_share", "fund_transfer"]
    if transaction_context not in valid_contexts:
        transaction_context = "general"

    session_id = f"session_a_{uuid.uuid4().hex[:8]}"
    file_ext = os.path.splitext(file.filename or "sample.wav")[1].lower() or ".wav"
    save_filename = f"{session_id}{file_ext}"
    save_path = os.path.join(UPLOAD_DIR, save_filename)

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save audio file: {str(e)}")

    create_session(
        session_id=session_id,
        mode="mode_a_upload",
        transaction_context=transaction_context
    )

    return {
        "status": "success",
        "session_id": session_id,
        "mode": "mode_a_upload",
        "transaction_context": transaction_context,
        "filename": file.filename,
        "stream_url": f"/calls/{session_id}/stream",
        "ws_url": f"ws://localhost:8000/calls/{session_id}/stream"
    }


@router.post("/upload-preset")
async def upload_preset_clip(
    preset_name: str = Form(...),
    transaction_context: str = Form("general")
):
    """
    Mode A Endpoint for Demo Presets: Copies calibrated audio clip from samples/ to uploads/
    and initializes the session for immediate live streaming replay.
    """
    valid_contexts = ["general", "credential_reset", "otp_share", "fund_transfer"]
    if transaction_context not in valid_contexts:
        transaction_context = "general"

    samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "samples"))
    if not os.path.exists(samples_dir):
        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))

    src_path = os.path.join(samples_dir, preset_name)
    if not os.path.exists(src_path):
        # Fallback search
        src_path = os.path.join(os.path.dirname(__file__), "..", "samples", preset_name)
        if not os.path.exists(src_path):
            raise HTTPException(status_code=404, detail=f"Preset file '{preset_name}' not found")

    session_id = f"session_a_{uuid.uuid4().hex[:8]}"
    dst_path = os.path.join(UPLOAD_DIR, f"{session_id}.wav")
    shutil.copyfile(src_path, dst_path)

    create_session(
        session_id=session_id,
        mode="mode_a_upload",
        transaction_context=transaction_context
    )

    return {
        "status": "success",
        "session_id": session_id,
        "mode": "mode_a_upload",
        "transaction_context": transaction_context,
        "filename": preset_name,
        "stream_url": f"/calls/{session_id}/stream"
    }


@router.post("/start-live")
async def start_live_call(req: StartLiveRequest = StartLiveRequest()):
    """
    Mode B Endpoint: Initializes a live WebRTC browser-to-browser call session.
    Provides session_id, room_code, and public STUN servers for WebRTC signaling.
    """
    session_id = f"session_b_{uuid.uuid4().hex[:8]}"
    create_session(
        session_id=session_id,
        mode="mode_b_live",
        transaction_context=req.transaction_context or "general"
    )

    return {
        "status": "success",
        "session_id": session_id,
        "room_code": session_id,
        "mode": "mode_b_live",
        "transaction_context": req.transaction_context,
        "ice_servers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"},
            {"urls": "stun:stun2.l.google.com:19302"}
        ],
        "ws_stream_url": f"ws://localhost:8000/calls/{session_id}/stream",
        "ws_signaling_url": f"ws://localhost:8000/calls/{session_id}/signaling"
    }


@router.get("/{session_id}/summary")
async def get_summary(session_id: str):
    """
    Retrieves post-call aggregate metrics: peak risk, average risk, total chunks, and triggered alerts.
    """
    summary = get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary


@router.get("/{session_id}/history")
async def get_history(session_id: str):
    """
    Retrieves complete time-series chunk metrics for chart reconstruction.
    """
    history = get_session_history(session_id)
    return {"session_id": session_id, "history": history}


@router.post("/{session_id}/context")
async def update_context(session_id: str, req: UpdateContextRequest):
    """
    Dynamically adjusts session transaction context during an ongoing call.
    """
    valid_contexts = ["general", "credential_reset", "otp_share", "fund_transfer"]
    if req.transaction_context not in valid_contexts:
        raise HTTPException(status_code=400, detail=f"Invalid context. Choose from {valid_contexts}")

    success = update_session_context(session_id, req.transaction_context)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": "success",
        "session_id": session_id,
        "transaction_context": req.transaction_context
    }
