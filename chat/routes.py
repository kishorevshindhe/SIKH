import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Room, RoomMember, Message
from auth.auth import SECRET_KEY, ALGORITHM
from chat.chat_manager import manager
from jose import JWTError, jwt

router = APIRouter()


# ── Helper: authenticate WebSocket via token ──────────────────────────
async def get_ws_user(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user
    except JWTError:
        return None


# ── REST: Create a Room ───────────────────────────────────────────────
@router.post("/rooms/create")
def create_room(
    room_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(__import__('auth.dependencies', fromlist=['get_current_user']).get_current_user)
):
    existing = db.query(Room).filter(Room.name == room_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Room name already exists")
    room = Room(name=room_name, created_by=current_user.id)
    db.add(room)
    db.commit()
    db.refresh(room)
    # Auto-add creator as member
    member = RoomMember(room_id=room.id, user_id=current_user.id)
    db.add(member)
    db.commit()
    return {"room_id": room.id, "room_name": room.name, "created_by": current_user.username}


# ── REST: Invite a user to a Room ─────────────────────────────────────
@router.post("/rooms/{room_id}/invite")
def invite_to_room(
    room_id: int,
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(__import__('auth.dependencies', fromlist=['get_current_user']).get_current_user)
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room creator can invite users")
    invite_user = db.query(User).filter(User.username == username).first()
    if not invite_user:
        raise HTTPException(status_code=404, detail="User not found")
    already = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == invite_user.id
    ).first()
    if already:
        raise HTTPException(status_code=400, detail="User already in room")
    member = RoomMember(room_id=room_id, user_id=invite_user.id)
    db.add(member)
    db.commit()
    return {"message": f"{username} added to room {room.name}"}


# ── REST: Get Room chat history ───────────────────────────────────────
@router.get("/rooms/{room_id}/messages")
def get_room_messages(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(__import__('auth.dependencies', fromlist=['get_current_user']).get_current_user)
):
    member = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="You are not a member of this room")
    messages = db.query(Message).filter(
        Message.room_id == room_id
    ).order_by(Message.created_at).all()
    return [{"sender": m.sender.username, "content": m.content, "time": str(m.created_at)} for m in messages]


# ── REST: Get DM history ──────────────────────────────────────────────
@router.get("/dm/{username}/messages")
def get_dm_messages(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(__import__('auth.dependencies', fromlist=['get_current_user']).get_current_user)
):
    other = db.query(User).filter(User.username == username).first()
    if not other:
        raise HTTPException(status_code=404, detail="User not found")
    messages = db.query(Message).filter(
        Message.chat_type == "dm",
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other.id)) |
        ((Message.sender_id == other.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at).all()
    return [{"sender": m.sender.username, "content": m.content, "time": str(m.created_at)} for m in messages]


# ── WS: Public Chat ───────────────────────────────────────────────────
@router.websocket("/ws/public")
async def public_chat(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    user = await get_ws_user(token, db)
    if not user:
        await websocket.close(code=1008)
        return
    await manager.connect_public(websocket, user.username)
    try:
        while True:
            message = await websocket.receive_text()
            await manager.broadcast_public(message, sender=user.username)
    except WebSocketDisconnect:
        await manager.disconnect_public(user.username)


# ── WS: Room Chat ─────────────────────────────────────────────────────
@router.websocket("/ws/room/{room_id}")
async def room_chat(websocket: WebSocket, room_id: int, token: str, db: Session = Depends(get_db)):
    user = await get_ws_user(token, db)
    if not user:
        await websocket.close(code=1008)
        return
    # Check membership
    member = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user.id
    ).first()
    if not member:
        await websocket.close(code=1008)
        return
    await manager.connect_room(websocket, str(room_id), user.username)
    try:
        while True:
            message = await websocket.receive_text()
            await manager.broadcast_room(str(room_id), message, sender=user.username)
            await manager.save_room_message(db, message, user.id, room_id)
    except WebSocketDisconnect:
        await manager.disconnect_room(str(room_id), user.username)


# ── WS: Direct Message ────────────────────────────────────────────────
@router.websocket("/ws/dm")
async def direct_message(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    user = await get_ws_user(token, db)
    if not user:
        await websocket.close(code=1008)
        return
    await manager.connect_direct(websocket, user.username)
    try:
        while True:
            # Format: {"to": "username", "message": "hello"}
            data = await websocket.receive_text()
            payload = json.loads(data)
            to_username = payload.get("to")
            message = payload.get("message")
            if to_username and message:
                to_user = db.query(User).filter(User.username == to_username).first()
                if to_user:
                    await manager.save_dm_message(db, message, user.id, to_user.id)
                    sent = await manager.send_direct(to_username, message, from_username=user.username)
                    if not sent:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"{to_username} is offline. Message saved."
                        }))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "User not found"}))
    except WebSocketDisconnect:
        await manager.disconnect_direct(user.username)


# ── WS: Voice Lobby ───────────────────────────────────────────────────
@router.websocket("/ws/voice/{room_id}")
async def voice_lobby(websocket: WebSocket, room_id: int, token: str, db: Session = Depends(get_db)):
    user = await get_ws_user(token, db)
    if not user:
        await websocket.close(code=1008)
        return
    # Must be a room member
    member = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user.id
    ).first()
    if not member:
        await websocket.close(code=1008)
        return
    await manager.connect_voice(websocket, str(room_id), user.username)
    try:
        while True:
            # WebRTC signaling — offer, answer, ice candidates
            data = await websocket.receive_text()
            payload = json.loads(data)
            to_username = payload.get("to")
            if to_username:
                payload["from"] = user.username
                await manager.send_voice_signal(str(room_id), payload, to_username)
    except WebSocketDisconnect:
        await manager.disconnect_voice(str(room_id), user.username)