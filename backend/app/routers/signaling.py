"""
Lightweight WebRTC Signaling Hub for Mode B Live Browser Calls.

Provides room-based signaling for two browser peers to exchange:
- SDP Offers & Answers
- ICE Candidates
- Call status notifications

Note on NAT/Firewall limitations:
In this hackathon architecture, WebRTC uses Google public STUN servers.
This works across the vast majority of consumer home/office Wi-Fi networks.
On strict corporate symmetric NATs/firewalls, a dedicated TURN relay server
would be required in production.
"""

from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter(tags=["Signaling"])

# In-memory mapping of session_id -> set of active WebSocket connections
active_rooms: Dict[str, Set[WebSocket]] = {}


@router.websocket("/calls/{session_id}/signaling")
async def webrtc_signaling_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    if session_id not in active_rooms:
        active_rooms[session_id] = set()

    room = active_rooms[session_id]
    room.add(websocket)
    peer_count = len(room)

    # Notify caller of room occupancy
    await websocket.send_json({
        "type": "room_status",
        "session_id": session_id,
        "peer_count": peer_count,
        "is_initiator": (peer_count == 1)
    })

    # If second peer joined, notify the first peer to start SDP offer
    if peer_count == 2:
        for peer in list(room):
            if peer != websocket:
                await peer.send_json({
                    "type": "peer_joined",
                    "session_id": session_id
                })

    try:
        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)

            # Relay signaling message (offer, answer, candidate, mute, etc.) to all other peers in the room
            for peer in list(room):
                if peer != websocket:
                    try:
                        await peer.send_json(data)
                    except Exception:
                        pass

    except WebSocketDisconnect:
        room.discard(websocket)
        if len(room) == 0:
            active_rooms.pop(session_id, None)
        else:
            for peer in list(room):
                try:
                    await peer.send_json({
                        "type": "peer_left",
                        "session_id": session_id
                    })
                except Exception:
                    pass
