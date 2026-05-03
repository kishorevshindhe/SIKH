import json
import uuid
import base64
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Room, RoomMember, PendingFile
from auth.dependencies import get_current_user
from chat.file_crypto import encrypt_file, decrypt_file
from chat.chat_manager import manager

router = APIRouter()

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit


# ── Upload file for DM ─────────────────────────────────────────────────
@router.post("/files/dm/{to_username}")
async def upload_dm_file(
    to_username: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check receiver exists
    receiver = db.query(User).filter(User.username == to_username).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    # Read and check file size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 100MB.")

    # Encrypt file
    encrypted = encrypt_file(data)

    # Generate unique file ID
    file_id = str(uuid.uuid4())

    # Save to DB
    pending = PendingFile(
        file_id=file_id,
        filename=file.filename,
        filesize=len(data),
        filetype=file.content_type or "application/octet-stream",
        encrypted_data=encrypted,
        sender_id=current_user.id,
        receiver_id=receiver.id,
        chat_type="dm"
    )
    db.add(pending)
    db.commit()

    # Notify receiver via WebSocket if online
    file_msg = json.dumps({
        "type": "file",
        "file_id": file_id,
        "filename": file.filename,
        "filesize": len(data),
        "filetype": file.content_type,
        "from": current_user.username,
        "download_url": f"/files/download/{file_id}"
    })

    await manager.send_direct(to_username, file_msg, from_username=current_user.username)

    return {
        "message": "File uploaded successfully",
        "file_id": file_id,
        "filename": file.filename,
        "download_url": f"/files/download/{file_id}"
    }


# ── Upload file for Room ───────────────────────────────────────────────
@router.post("/files/room/{room_id}")
async def upload_room_file(
    room_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check room exists and user is a member
    member = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="You are not a member of this room")

    # Read and check file size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 100MB.")

    # Encrypt file
    encrypted = encrypt_file(data)

    # Generate unique file ID
    file_id = str(uuid.uuid4())

    # Save to DB
    pending = PendingFile(
        file_id=file_id,
        filename=file.filename,
        filesize=len(data),
        filetype=file.content_type or "application/octet-stream",
        encrypted_data=encrypted,
        sender_id=current_user.id,
        room_id=room_id,
        chat_type="room"
    )
    db.add(pending)
    db.commit()

    # Notify all room members via WebSocket
    file_msg = json.dumps({
        "type": "file",
        "file_id": file_id,
        "filename": file.filename,
        "filesize": len(data),
        "filetype": file.content_type,
        "from": current_user.username,
        "download_url": f"/files/download/{file_id}"
    })
    await manager.broadcast_room(str(room_id), file_msg, sender=current_user.username)

    return {
        "message": "File uploaded to room successfully",
        "file_id": file_id,
        "filename": file.filename,
        "download_url": f"/files/download/{file_id}"
    }


# ── Download file ──────────────────────────────────────────────────────
@router.get("/files/download/{file_id}")
async def download_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the file
    pending = db.query(PendingFile).filter(PendingFile.file_id == file_id).first()
    if not pending:
        raise HTTPException(status_code=404, detail="File not found or already deleted")

    # Check access rights
    if pending.chat_type == "dm":
        if current_user.id != pending.sender_id and current_user.id != pending.receiver_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif pending.chat_type == "room":
        member = db.query(RoomMember).filter(
            RoomMember.room_id == pending.room_id,
            RoomMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Decrypt file
    decrypted = decrypt_file(pending.encrypted_data)

    # Track who downloaded
    downloaded_by = json.loads(pending.downloaded_by or "[]")
    if current_user.id not in downloaded_by:
        downloaded_by.append(current_user.id)
        pending.downloaded_by = json.dumps(downloaded_by)
        db.commit()

    # For DM — delete after both sender and receiver have downloaded
    if pending.chat_type == "dm":
        both_downloaded = (
            pending.sender_id in downloaded_by and
            pending.receiver_id in downloaded_by
        )
        if both_downloaded:
            db.delete(pending)
            db.commit()

    # Return file as download
    return Response(
        content=decrypted,
        media_type=pending.filetype,
        headers={
            "Content-Disposition": f'attachment; filename="{pending.filename}"',
            "Content-Length": str(pending.filesize)
        }
    )


# ── List pending files for current user ───────────────────────────────
@router.get("/files/pending")
def get_pending_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    files = db.query(PendingFile).filter(
        PendingFile.receiver_id == current_user.id
    ).all()
    return [
        {
            "file_id": f.file_id,
            "filename": f.filename,
            "filesize": f.filesize,
            "filetype": f.filetype,
            "from": f.sender.username,
            "download_url": f"/files/download/{f.file_id}",
            "uploaded_at": str(f.created_at)
        }
        for f in files
    ]