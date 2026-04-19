from fastapi import WebSocket
from typing import Dict, List
from sqlalchemy.orm import Session
from database.models import Message, Room, RoomMember, User


class ChatManager:
    def __init__(self):
        # Public chat — no persistence needed
        self.public_connections: Dict[str, WebSocket] = {}  # username: websocket

        # Room chat — room_id: {username: websocket}
        self.room_connections: Dict[str, Dict[str, WebSocket]] = {}

        # Direct messages — username: websocket
        self.direct_connections: Dict[str, WebSocket] = {}

        # Voice lobby — room_id: {username: websocket}
        self.voice_connections: Dict[str, Dict[str, WebSocket]] = {}

    # ── Public Chat (in-memory only) ──────────────────────────────────
    async def connect_public(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.public_connections[username] = websocket
        await self.broadcast_public(f"{username} joined the chat!", sender="System")

    async def disconnect_public(self, username: str):
        if username in self.public_connections:
            del self.public_connections[username]
        await self.broadcast_public(f"{username} left the chat.", sender="System")

    async def broadcast_public(self, message: str, sender: str):
        for connection in self.public_connections.values():
            await connection.send_text(f"[{sender}]: {message}")

    # ── Room Chat (persisted) ─────────────────────────────────────────
    async def connect_room(self, websocket: WebSocket, room_id: str, username: str):
        await websocket.accept()
        if room_id not in self.room_connections:
            self.room_connections[room_id] = {}
        self.room_connections[room_id][username] = websocket
        await self.broadcast_room(room_id, f"{username} joined the room!", sender="System")

    async def disconnect_room(self, room_id: str, username: str):
        if room_id in self.room_connections:
            if username in self.room_connections[room_id]:
                del self.room_connections[room_id][username]
        await self.broadcast_room(room_id, f"{username} left the room.", sender="System")

    async def broadcast_room(self, room_id: str, message: str, sender: str):
        if room_id in self.room_connections:
            for connection in self.room_connections[room_id].values():
                await connection.send_text(f"[{sender}]: {message}")

    async def save_room_message(self, db: Session, content: str, sender_id: int, room_id: int):
        msg = Message(
            content=content,
            sender_id=sender_id,
            room_id=room_id,
            chat_type="room"
        )
        db.add(msg)
        db.commit()

    # ── Direct Messages (persisted) ───────────────────────────────────
    async def connect_direct(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.direct_connections[username] = websocket

    async def disconnect_direct(self, username: str):
        if username in self.direct_connections:
            del self.direct_connections[username]

    async def send_direct(self, to_username: str, message: str, from_username: str):
        if to_username in self.direct_connections:
            await self.direct_connections[to_username].send_text(
                f"[DM from {from_username}]: {message}"
            )
            return True
        return False

    async def save_dm_message(self, db: Session, content: str, sender_id: int, receiver_id: int):
        msg = Message(
            content=content,
            sender_id=sender_id,
            receiver_id=receiver_id,
            chat_type="dm"
        )
        db.add(msg)
        db.commit()

    # ── Voice Lobby (WebRTC signaling, no persistence) ────────────────
    async def connect_voice(self, websocket: WebSocket, room_id: str, username: str):
        await websocket.accept()
        if room_id not in self.voice_connections:
            self.voice_connections[room_id] = {}
        self.voice_connections[room_id][username] = websocket
        # Tell everyone else in the room that a new user joined voice
        await self.broadcast_voice(room_id, {
            "type": "user_joined_voice",
            "username": username
        }, exclude=username)

    async def disconnect_voice(self, room_id: str, username: str):
        if room_id in self.voice_connections:
            if username in self.voice_connections[room_id]:
                del self.voice_connections[room_id][username]
        await self.broadcast_voice(room_id, {
            "type": "user_left_voice",
            "username": username
        })

    async def broadcast_voice(self, room_id: str, data: dict, exclude: str = None):
        import json
        if room_id in self.voice_connections:
            for username, connection in self.voice_connections[room_id].items():
                if username != exclude:
                    await connection.send_text(json.dumps(data))

    async def send_voice_signal(self, room_id: str, data: dict, to_username: str):
        import json
        if room_id in self.voice_connections:
            if to_username in self.voice_connections[room_id]:
                await self.voice_connections[room_id][to_username].send_text(json.dumps(data))


manager = ChatManager()