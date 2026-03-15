# SIKH — Secure Intelligent Knowledge Hub

> Final Year Project | Version 1.0 | March 2026

A web-based collaborative learning platform that integrates AI assistance, intelligent search, secure communication, and community interaction into one unified system.

---

## Team

| Member | Role | Branch |
|--------|------|--------|
| Member 1 | Backend + Chat + Security | `feature/backend` |
| Member 2 | AI + Automation | `feature/ai` |
| Member 3 | Frontend + Search | `feature/frontend` |
| Member 4 (Claude) | AI Coding Assistant | — |

---

## Repository Structure

```
SIKH/
├── backend/          ← Member 1 (Python, FastAPI, Auth, Chat, WebSockets)
│   ├── auth/         ← JWT authentication, RBAC
│   ├── chat/         ← WebSocket chat, rooms, DMs
│   ├── security/     ← Encryption, intrusion detection
│   └── api/          ← REST API routes
│
├── frontend/         ← Member 3 (HTML/CSS/JS, React)
│   ├── src/          ← React components / JS
│   ├── components/   ← Reusable UI components
│   └── public/       ← Static assets
│
├── ai_module/        ← Member 2 (AI API, ML, Automation)
│   ├── assistant/    ← AI chatbot integration (OpenAI API)
│   ├── question_paper/ ← QP analysis, topic extraction
│   └── automation/   ← Selenium, web scraping
│
├── search_engine/    ← Member 3 (TF-IDF, Cosine Similarity)
│   ├── indexing/     ← Inverted index, tokenization
│   └── algorithms/   ← TF-IDF, cosine similarity
│
├── security/         ← Member 1 (shared security utils)
├── docs/             ← Shared documentation
├── tests/            ← All test files
│   ├── backend/
│   ├── frontend/
│   └── ai/
├── .gitignore
└── README.md
```

---

## Branching Strategy

```
main        ← Stable, production-ready code only. No direct pushes.
dev         ← Integration branch. All features merge here first.
feature/backend   ← Member 1
feature/ai        ← Member 2
feature/frontend  ← Member 3
```

### Daily Git Workflow

```bash
# 1. Always start by pulling the latest dev
git pull origin dev

# 2. Switch to your own branch
git checkout feature/your-branch

# 3. Work on your module...

# 4. Stage and commit
git add .
git commit -m "feat: short description of what you did"

# 5. Push your branch
git push origin feature/your-branch

# 6. When feature is complete → open a Pull Request into dev
```

### Commit Message Prefixes

| Prefix | Use |
|--------|-----|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation |
| `style:` | UI/CSS only |
| `refactor:` | Code cleanup (no feature change) |
| `test:` | Adding/updating tests |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python — FastAPI |
| Frontend | HTML, CSS, JS — React |
| Database | PostgreSQL (prod), SQLite (dev) |
| AI | OpenAI API |
| Search | Scikit-learn, NLTK |
| Real-time Chat | WebSockets |
| Voice Chat | WebRTC |
| Auth | JWT Tokens |
| Caching | Redis |

---

## Getting Started

### Backend (Member 1)
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

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
# Add your API key to .env (never commit this!)
```

---

## Environment Variables

Each member should create a `.env` file in their module directory. **Never commit `.env` files.**

```env
# backend/.env
DATABASE_URL=postgresql://user:password@localhost/sikh_db
JWT_SECRET=your_secret_key_here
REDIS_URL=redis://localhost:6379

# ai_module/.env
OPENAI_API_KEY=your_openai_key_here
```

---

## Development Phases

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Planning & Design | ✅ Done |
| 2 | Backend Development | 🔄 In Progress |
| 3 | Search Engine | ⏳ Pending |
| 4 | AI Integration | ⏳ Pending |
| 5 | Community System | ⏳ Pending |
| 6 | Security | ⏳ Pending |
| 7 | Integration & Testing | ⏳ Pending |
| 8 | Deployment | ⏳ Pending |

---

## Rules

- ❌ **Never push directly to `main`**
- ❌ **Never commit `.env` files or API keys**
- ✅ Always pull from `dev` before starting work
- ✅ Use descriptive commit messages with the correct prefix
- ✅ Open a Pull Request when your feature is ready — don't merge yourself
