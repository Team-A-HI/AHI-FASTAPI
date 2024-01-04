from fastapi import WebSocket
from typing import Dict

class WebSocketConnection:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, email: str):
        await websocket.accept()
        self.active_connections[email] = websocket

    def disconnect(self, email: str):
        if email in self.active_connections:
            del self.active_connections[email]

    async def send_message(self, message: str, email: str):
        if email in self.active_connections:
            websocket = self.active_connections[email]
            await websocket.send_text(message)