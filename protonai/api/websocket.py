"""WebSocket channels for real-time updates.
Designed & developed by: Ali Hussein Thajil

Channels:
- /ws/cases/{case_id} - live updates on a specific case
- /ws/metrics - real-time server metrics
- /ws/alerts - clinical alerts stream
"""
from __future__ import annotations
import asyncio
import json
from typing import Dict, List, Set

try:
    from fastapi import WebSocket, WebSocketDisconnect
    HAS_WS = True
except ImportError:
    HAS_WS = False


class ChannelHub:
    """In-memory pub/sub for WebSocket channels."""

    def __init__(self):
        self.channels: Dict[str, Set] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str, ws):
        async with self._lock:
            if channel not in self.channels:
                self.channels[channel] = set()
            self.channels[channel].add(ws)

    async def unsubscribe(self, channel: str, ws):
        async with self._lock:
            if channel in self.channels:
                self.channels[channel].discard(ws)
                if not self.channels[channel]:
                    del self.channels[channel]

    async def publish(self, channel: str, data: Dict):
        async with self._lock:
            subs = list(self.channels.get(channel, set()))
        dead = []
        for ws in subs:
            try:
                await ws.send_json({"channel": channel, "data": data})
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    if channel in self.channels:
                        self.channels[channel].discard(ws)

    def stats(self) -> Dict[str, int]:
        return {ch: len(subs) for ch, subs in self.channels.items()}


hub = ChannelHub() if HAS_WS else None
