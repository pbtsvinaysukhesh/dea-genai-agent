"""WebSocket connection manager"""
import json
from typing import List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def send(self, ws: WebSocket, data: dict):
        await ws.send_text(json.dumps(data))

    async def broadcast(self, data: dict):
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass