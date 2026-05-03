# SIKH — Secure Intelligent Knowledge Hub

> Final Year Project | Version 1.0 | 2026

A web-based collaborative learning platform that integrates AI assistance, intelligent search, secure real-time communication, and community interaction into one unified system.

---

## Team

| Member | Name | Role | Branch |
|--------|------|------|--------|
| Member 1 | Kishore V | Backend + Chat + Security | `feature/backend` |
| Member 2 | Likhith D Girish | AI + Automation | `feature/ai` |
| Member 3 | Jash Ashish Ladani | Frontend + Search | `feature/frontend` |

---

## Repository Structure

```
SIKH/
├── backend/                   <- Member 1 (Python, FastAPI, Auth, Chat, WebSockets)
│   ├── auth/                  <- JWT authentication, bcrypt, RBAC
│   ├── chat/                  <- WebSocket chat, rooms, DMs, voice lobby
│   ├── database/              <- SQLAlchemy models, SQLite (dev) / PostgreSQL (prod)
│   ├── security/              <- AES-256 file encryption, intrusion detection
│   └── main.py                <- FastAPI app entry point
│
├── frontend/                  <- Member 3 (React, HTML, CSS, JS)
│   ├── src/                   <- React components
│   ├── components/            <- Reusable UI components
│   └── public/                <- Static assets
│
├── ai_module/                 <- Member 2 (OpenAI API, ML, Automation)
│   ├── assistant/             <- AI chatbot integration
│   ├── question_paper/        <- Question paper analysis, topic extraction
│   └── automation/            <- Selenium, web scraping
│
├── search_engine/             <- Member 3 (TF-IDF, Cosine Similarity)
│   ├── indexing/              <- Inverted index, tokenization
│   └── algorithms/            <- TF-IDF, cosine similarity
│
├── docs/                      <- Shared documentation
├── tests/                     <- All test files
│   ├── backend/
│   ├── frontend/
│   └── ai/
├── .gitignore
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI |
| Frontend | React, HTML, CSS, JavaScript |
| Database | SQLite (dev), PostgreSQL (prod) |
| AI | OpenAI API |
| Search | Scikit-learn, NLTK, TF-IDF, Cosine Similarity |
| Real-time Chat | WebSockets |
| Voice Chat | WebRTC |
| Authentication | JWT Tokens, bcrypt |
| File Security | AES-256 Encryption |
| Caching | Redis |

---

## Branching Strategy

```
main               <- Stable, production-ready code only. No direct pushes.
dev                <- Integration branch. All features merge here first.
feature/backend    <- Member 1
feature/ai         <- Member 2
feature/frontend   <- Member 3
```

### Daily Git Workflow

```bash
# 1. Always start by pulling the latest dev
git pull origin dev

# 2. Switch to your own branch
git checkout feature/your-branch

# 3. Work on your module

# 4. Stage and commit
git add .
git commit -m "feat: short description of what you did"

# 5. Push your branch
git push origin feature/your-branch

# 6. When feature is complete, open a Pull Request into dev
#    Do not merge yourself
```

### Commit Message Prefixes

| Prefix | Use |
|--------|-----|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation update |
| `style:` | UI or CSS changes only |
| `refactor:` | Code cleanup with no feature change |
| `test:` | Adding or updating tests |
| `security:` | Security-related changes |

---

## Getting Started

### Backend (Member 1)

```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --port 9000 --reload
```

API docs available at: http://localhost:9000/docs  
Chat tester available at: http://localhost:9000/test-chat

### Frontend (Member 3)

```bash
cd frontend
npm install
npm start
```

### AI Module (Member 2)

```bash
cd ai_module
pip install -r requirements.txt
# Add your API key to .env (never commit this)
```

---

## Environment Variables

Each member must create a `.env` file in their module directory. Never commit `.env` files.

```env
# backend/.env
DATABASE_URL=postgresql://user:password@localhost/sikh_db
JWT_SECRET=your_secret_key_here
REDIS_URL=redis://localhost:6379

# ai_module/.env
OPENAI_API_KEY=your_openai_key_here
```

---

## Backend API Reference

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register a new user | No |
| POST | `/auth/login` | Login and receive JWT token | No |
| GET | `/auth/me` | Get current user info | Yes |

### Chat — WebSocket Endpoints

| Type | Endpoint | Description | Auth Required |
|------|----------|-------------|---------------|
| WS | `/ws/public?token=` | Public chat room | Yes |
| WS | `/ws/room/{room_id}?token=` | Private study room | Yes |
| WS | `/ws/dm?token=` | Direct messaging | Yes |
| WS | `/ws/voice/{room_id}?token=` | Voice lobby (WebRTC) | Yes |

### Rooms

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/rooms/create` | Create a new room | Yes |
| POST | `/rooms/{room_id}/invite` | Invite a user to a room | Yes (creator only) |
| GET | `/rooms/{room_id}/messages` | Get room chat history | Yes (members only) |
| GET | `/dm/{username}/messages` | Get DM history | Yes |

### Files

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/files/dm/{to_username}` | Upload file via DM | Yes |
| POST | `/files/room/{room_id}` | Upload file to a room | Yes |
| GET | `/files/download/{file_id}` | Download a file | Yes |
| GET | `/files/pending` | List files pending download | Yes |

---

## Chat Features

| Feature | Description |
|---------|-------------|
| Public Chat | All logged-in users can talk. Messages are in-memory (not persisted). |
| Room Chat | Invite-only private rooms. Messages saved to database. |
| Direct Messages | One-to-one private messaging. Messages saved to database. Offline delivery supported. |
| Voice Lobby | WebRTC-based real-time voice chat inside a private room. |
| File Sharing | AES-256 encrypted file transfer via DM or room chat. Files stored temporarily and deleted after download. |

---

## Security Features

| Feature | Implementation |
|---------|----------------|
| Password hashing | bcrypt (version 4.0.1) |
| Authentication | JWT tokens with 30-minute expiry |
| WebSocket auth | JWT token passed as query parameter on connect |
| Role-based access | Admin and user roles enforced on all routes |
| File encryption | AES-256-GCM via Python cryptography library |
| File access control | Only sender and receiver (or room members) can download files |
| Auto file deletion | DM files deleted from server after both parties download |

---

## Development Phases

| Phase | Title | Owner | Status |
|-------|-------|-------|--------|
| 1 | Planning and Design | All | Done |
| 2 | Backend — Auth, DB, Security | Member 1 | Done |
| 3 | Backend — Chat System | Member 1 | Done |
| 4 | Backend — File Upload | Member 1 | Done |
| 5 | AI Integration | Member 2 | In Progress |
| 6 | Frontend Development | Member 3 | In Progress |
| 7 | Search Engine | Member 3 | Pending |
| 8 | Integration and Testing | All | Pending |
| 9 | Deployment | All | Pending |

---

## Deployment Plan

| Module | Platform |
|--------|----------|
| Frontend | Vercel |
| Backend | Railway or Render |
| Database | PostgreSQL on cloud |

---

## Rules

- Never push directly to `main`
- Never commit `.env` files, API keys, or encryption keys
- Never commit `__pycache__`, `.venv`, or database files
- Always pull from `dev` before starting work
- Use descriptive commit messages with the correct prefix
- Open a Pull Request when your feature is ready — do not merge yourself
- Always test your module before opening a Pull Request
