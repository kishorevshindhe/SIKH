from fastapi import WebSocket
from typing import Dict, List

class ChatManager:
    def __init__(self):
        # Public chat — list of connected users
        self.public_connections: List[WebSocket] = []
        
        # Private rooms — dict of room_id: list of connected users
        self.room_connections: Dict[str, List[WebSocket]] = {}
        
        # Direct messages — dict of user_id: websocket
        self.direct_connections: Dict[str, WebSocket] = {}

    # ── Public Chat ──────────────────────────────────────
    async def connect_public(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.public_connections.append(websocket)
        await self.broadcast_public(f"{username} joined the chat!", sender="System")

    async def disconnect_public(self, websocket: WebSocket, username: str):
        self.public_connections.remove(websocket)
        await self.broadcast_public(f"{username} left the chat.", sender="System")

    async def broadcast_public(self, message: str, sender: str):
        for connection in self.public_connections:
            await connection.send_text(f"[{sender}]: {message}")

    # ── Private Rooms ─────────────────────────────────────
    async def connect_room(self, websocket: WebSocket, room_id: str, username: str):
        await websocket.accept()
        if room_id not in self.room_connections:
            self.room_connections[room_id] = []
        self.room_connections[room_id].append(websocket)
        await self.broadcast_room(room_id, f"{username} joined the room!", sender="System")

    async def disconnect_room(self, websocket: WebSocket, room_id: str, username: str):
        self.room_connections[room_id].remove(websocket)
        await self.broadcast_room(room_id, f"{username} left the room.", sender="System")

    async def broadcast_room(self, room_id: str, message: str, sender: str):
        if room_id in self.room_connections:
            for connection in self.room_connections[room_id]:
                await connection.send_text(f"[{sender}]: {message}")

    # ── Direct Messaging ──────────────────────────────────
    async def connect_direct(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.direct_connections[user_id] = websocket

    async def send_direct(self, to_user_id: str, message: str, from_username: str):
        if to_user_id in self.direct_connections:
            await self.direct_connections[to_user_id].send_text(
                f"[DM from {from_username}]: {message}"
            )
            return True
        return False

# Single instance used across the whole app
manager = ChatManager()