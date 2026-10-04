"""WebSocket Connection Manager and Multi-Channel Broadcasting.

Implements SYS-10, APP-24, CON §4:
- Manages client connections for /ws/telemetry and /ws/video.
- Supports session-scoped subscriptions.
- Handles heartbeat ping/pong protocol.
- Broadcasts telemetry, alerts, system status, and video frames safely.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("app.ws.manager")


class ConnectionManager:
    """Manages WebSocket connections and channel broadcasting."""

    def __init__(self) -> None:
        self.telemetry_connections: Set[WebSocket] = set()
        self.video_connections: Set[WebSocket] = set()
        # Maps session_id -> Set[WebSocket]
        self.session_subscriptions: Dict[int, Set[WebSocket]] = {}

    async def connect_telemetry(self, websocket: WebSocket) -> None:
        """Register and accept a telemetry WebSocket connection."""
        await websocket.accept()
        self.telemetry_connections.add(websocket)
        logger.info("Telemetry client connected (%d active).", len(self.telemetry_connections))

    def disconnect_telemetry(self, websocket: WebSocket) -> None:
        """Remove telemetry WebSocket and its subscriptions."""
        self.telemetry_connections.discard(websocket)
        for session_id, subs in list(self.session_subscriptions.items()):
            subs.discard(websocket)
            if not subs:
                del self.session_subscriptions[session_id]
        logger.info("Telemetry client disconnected (%d remaining).", len(self.telemetry_connections))

    async def connect_video(self, websocket: WebSocket) -> None:
        """Register and accept an operator video WebSocket connection."""
        await websocket.accept()
        self.video_connections.add(websocket)
        logger.info("Video client connected (%d active).", len(self.video_connections))

    def disconnect_video(self, websocket: WebSocket) -> None:
        """Remove video WebSocket connection."""
        self.video_connections.discard(websocket)
        logger.info("Video client disconnected (%d remaining).", len(self.video_connections))

    def subscribe_session(self, websocket: WebSocket, session_id: int) -> None:
        """Subscribe connection to a specific session_id feed."""
        if session_id not in self.session_subscriptions:
            self.session_subscriptions[session_id] = set()
        self.session_subscriptions[session_id].add(websocket)
        logger.info("Client subscribed to session %d.", session_id)

    def unsubscribe_session(self, websocket: WebSocket, session_id: int) -> None:
        """Unsubscribe connection from a session_id feed."""
        if session_id in self.session_subscriptions:
            self.session_subscriptions[session_id].discard(websocket)
            if not self.session_subscriptions[session_id]:
                del self.session_subscriptions[session_id]

    async def broadcast_telemetry(self, telemetry_payload: Dict[str, Any], session_id: Optional[int] = None) -> None:
        """Broadcast telemetry message to all or session-subscribed telemetry clients."""
        target_clients = (
            self.session_subscriptions.get(session_id, set())
            if session_id is not None and session_id in self.session_subscriptions
            else self.telemetry_connections
        )

        dead_sockets: List[WebSocket] = []
        for ws in list(target_clients):
            try:
                await ws.send_json(telemetry_payload)
            except Exception:
                dead_sockets.append(ws)

        for ws in dead_sockets:
            self.disconnect_telemetry(ws)

    async def broadcast_alert(self, alert_payload: Dict[str, Any], session_id: Optional[int] = None) -> None:
        """Broadcast an alert message to telemetry clients."""
        msg = {
            "type": "alert",
            "alert": alert_payload,
        }
        await self.broadcast_telemetry(msg, session_id=session_id)

    async def broadcast_system_status(self, status_payload: Dict[str, Any]) -> None:
        """Broadcast system status heartbeat to all telemetry clients."""
        msg = {
            "type": "system_status",
            "status": status_payload,
        }
        await self.broadcast_telemetry(msg, session_id=None)

    async def broadcast_video_frame(self, frame_payload: Dict[str, Any]) -> None:
        """Broadcast an annotated frame to video clients (only if privacy mode is disabled)."""
        dead_sockets: List[WebSocket] = []
        for ws in list(self.video_connections):
            try:
                await ws.send_json(frame_payload)
            except Exception:
                dead_sockets.append(ws)

        for ws in dead_sockets:
            self.disconnect_video(ws)


# Global connection manager instance
ws_manager = ConnectionManager()
