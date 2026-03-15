# SIKH - Architecture Overview

## System Architecture

```
[ Browser Client ]
       |
       | HTTP / WebSocket / WebRTC
       v
[ FastAPI Backend ]
   |         |         |
   v         v         v
[Auth]    [Chat]    [File Upload]
   |         |
   v         v
[PostgreSQL] [Redis Cache]
       |
       v
[AI Module] ←→ [OpenAI API]
[Search Engine] ←→ [NLTK / Scikit-learn]
```

## Communication Protocols

| Feature | Protocol |
|---------|----------|
| REST API calls | HTTP/HTTPS |
| Real-time chat | WebSocket |
| Voice chat | WebRTC |
| Authentication | JWT over HTTPS |

## Database Schema (Planned)

- **users** — id, username, email, password_hash, role, created_at
- **rooms** — id, name, owner_id, created_at, max_users
- **room_members** — room_id, user_id, joined_at
- **messages** — id, room_id, sender_id, content, timestamp, type
- **direct_messages** — id, sender_id, receiver_id, content, timestamp
- **files** — id, uploader_id, filename, path, type, created_at
- **friends** — user_id, friend_id, status
