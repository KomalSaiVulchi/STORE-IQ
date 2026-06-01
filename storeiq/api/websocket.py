"""WebSocket utilities for live updates."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger("storeiq-api")


class ConnectionManager:
    """Track and broadcast to active WebSocket clients."""

    def __init__(self) -> None:
        """Initialize connection state."""
        self._connections: List[WebSocket] = []
        self._max_connections: int = 100

    @property
    def active_count(self) -> int:
        """Return count of active connections."""
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new connection with connection limit."""
        if len(self._connections) >= self._max_connections:
            await websocket.close(code=1013, reason="Maximum connections reached")
            return
        await websocket.accept()
        self._connections.append(websocket)
        logger.info({"message": "WebSocket connected", "active_clients": len(self._connections)})

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection."""
        if websocket in self._connections:
            self._connections.remove(websocket)
            logger.info({"message": "WebSocket disconnected", "active_clients": len(self._connections)})

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        """Broadcast a payload to all connected clients."""
        dead_connections = []
        for connection in list(self._connections):
            try:
                await connection.send_json(payload)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn)


async def periodic_broadcast(
    manager: ConnectionManager,
    fetch_payload: callable,
    interval: float = 3.0,
) -> None:
    """Periodically broadcast live payloads."""
    while True:
        await asyncio.sleep(interval)
        if manager.active_count == 0:
            continue  # Skip if no clients connected
        try:
            payload = fetch_payload()
            await manager.broadcast(payload)
        except Exception as exc:
            logger.warning({"message": "Broadcast failed", "error": str(exc)})
