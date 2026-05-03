from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.database import Base


# ── User ──────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String, unique=True, index=True, nullable=False)
    email      = Column(String, unique=True, index=True, nullable=False)
    password   = Column(String, nullable=False)
    role       = Column(String, default="user")
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    sent_messages    = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    room_memberships = relationship("RoomMember", back_populates="user")


# ── Room ──────────────────────────────────────────────────────────────
class Room(Base):
    __tablename__ = "rooms"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String, unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    members  = relationship("RoomMember", back_populates="room")
    messages = relationship("Message", back_populates="room")


# ── RoomMember ────────────────────────────────────────────────────────
class RoomMember(Base):
    __tablename__ = "room_members"

    id        = Column(Integer, primary_key=True, index=True)
    room_id   = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())

    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="room_memberships")


# ── Message ───────────────────────────────────────────────────────────
class Message(Base):
    __tablename__ = "messages"

    id          = Column(Integer, primary_key=True, index=True)
    content     = Column(Text, nullable=False)
    sender_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # DM only
    room_id     = Column(Integer, ForeignKey("rooms.id"), nullable=True)  # Room only
    chat_type   = Column(String, nullable=False)  # "room" or "dm"
    created_at  = Column(DateTime, server_default=func.now())

    sender   = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")
    room     = relationship("Room", back_populates="messages")
    # ── Temporary File Storage ─────────────────────────────────────────────
class PendingFile(Base):
    __tablename__ = "pending_files"

    id           = Column(Integer, primary_key=True, index=True)
    file_id      = Column(String, unique=True, nullable=False)  # unique token to fetch file
    filename     = Column(String, nullable=False)
    filesize     = Column(Integer, nullable=False)
    filetype     = Column(String, nullable=False)
    encrypted_data = Column(Text, nullable=False)              # base64 encrypted file
    sender_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id  = Column(Integer, ForeignKey("users.id"), nullable=True)   # DM
    room_id      = Column(Integer, ForeignKey("rooms.id"), nullable=True)   # Room
    chat_type    = Column(String, nullable=False)              # "dm" or "room"
    downloaded_by = Column(Text, default="[]")                 # JSON list of user ids who downloaded
    created_at   = Column(DateTime, server_default=func.now())

    sender   = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    room     = relationship("Room", foreign_keys=[room_id])