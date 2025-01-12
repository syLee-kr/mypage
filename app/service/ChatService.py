from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # key: chat_room_id

    async def connect(self, chat_room_id: str, websocket: WebSocket):
        if chat_room_id not in self.active_connections:
            self.active_connections[chat_room_id] = []
        self.active_connections[chat_room_id].append(websocket)
        print(f"WebSocket connected: {websocket.client}")

    def disconnect(self, chat_room_id: str, websocket: WebSocket):
        self.active_connections[chat_room_id].remove(websocket)
        if not self.active_connections[chat_room_id]:
            del self.active_connections[chat_room_id]
        print(f"WebSocket disconnected: {websocket.client}")

    async def broadcast(self, chat_room_id: str, message: dict):
        if chat_room_id not in self.active_connections:
            return
        for connection in self.active_connections[chat_room_id]:
            await connection.send_json(message)
        print(f"Broadcasted message to chat room {chat_room_id}")
