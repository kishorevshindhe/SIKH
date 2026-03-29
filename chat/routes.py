from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from chat.chat_manager import manager

router = APIRouter()

# ── Public Chat ───────────────────────────────────────────
@router.websocket("/ws/public/{username}")
async def public_chat(websocket: WebSocket, username: str):
    await manager.connect_public(websocket, username)
    try:
        while True:
            message = await websocket.receive_text()
            await manager.broadcast_public(message, sender=username)
    except WebSocketDisconnect:
        await manager.disconnect_public(websocket, username)

# ── Private Study Rooms ───────────────────────────────────
@router.websocket("/ws/room/{room_id}/{username}")
async def room_chat(websocket: WebSocket, room_id: str, username: str):
    await manager.connect_room(websocket, room_id, username)
    try:
        while True:
            message = await websocket.receive_text()
            await manager.broadcast_room(room_id, message, sender=username)
    except WebSocketDisconnect:
        await manager.disconnect_room(websocket, room_id, username)

# ── Direct Messaging ──────────────────────────────────────
@router.websocket("/ws/direct/{user_id}")
async def direct_message(websocket: WebSocket, user_id: str):
    await manager.connect_direct(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Format: "to_user_id:message"
            parts = data.split(":", 1)
            if len(parts) == 2:
                to_user_id, message = parts
                sent = await manager.send_direct(to_user_id, message, from_username=user_id)
                if not sent:
                    await websocket.send_text(f"User {to_user_id} is not online.")
    except WebSocketDisconnect:
        if user_id in manager.direct_connections:
            del manager.direct_connections[user_id]