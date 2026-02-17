import asyncio
from collections import defaultdict
from collections.abc import Hashable
from typing import Any, DefaultDict, Set

from fastapi import WebSocket


class KeyedWebSocketManager:
    """Generic websocket connection manager keyed by arbitrary room/user key."""

    def __init__(self) -> None:
        self._connections: DefaultDict[Hashable, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, key: Hashable, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[key].add(websocket)

    async def disconnect(self, key: Hashable, websocket: WebSocket) -> None:
        async with self._lock:
            key_connections = self._connections.get(key)
            if not key_connections:
                return
            key_connections.discard(websocket)
            if not key_connections:
                self._connections.pop(key, None)

    async def broadcast(self, key: Hashable, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._connections.get(key, set()))

        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)

        if not stale:
            return

        async with self._lock:
            key_connections = self._connections.get(key)
            if not key_connections:
                return
            for websocket in stale:
                key_connections.discard(websocket)
            if not key_connections:
                self._connections.pop(key, None)
