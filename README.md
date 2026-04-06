# SIKH — Secure Intelligent Knowledge Hub

> **Final Year Project** | Version 1.0 | March 2026

SIKH is a web-based collaborative learning platform that integrates artificial intelligence, intelligent search, secure real-time communication, and community interaction into a single unified system. Designed as an intelligent academic ecosystem, SIKH brings together multiple disciplines of computer science — including AI, Information Retrieval, Networking, Cybersecurity, and Distributed Systems — to deliver a seamless learning experience.

---

## Table of Contents

- [Overview](#overview)
- [Core Features](#core-features)
- [Tech Stack](#tech-stack)
- [Team](#team)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Branching Strategy](#branching-strategy)
- [Development Phases](#development-phases)
- [Environment Variables](#environment-variables)
- [Commit Convention](#commit-convention)

---

## Overview

Traditional learning platforms lack real-time collaboration, intelligent document analysis, and secure communication in one place. SIKH solves this by combining:

- An **AI-powered assistant** for academic help and document summarization
- An **intelligent search engine** built on TF-IDF and Cosine Similarity
- A **real-time chat system** with public rooms, private study lobbies, and direct messaging
- **Voice communication** inside private study rooms via WebRTC
- **Secure file management** with PDF and document analysis
- A **question paper analysis system** that predicts high-probability exam topics

---

## Core Features

| Feature | Description |
|---------|-------------|
| AI Assistant | Academic Q&A, document summarization, concept explanations |
| Intelligent Search | TF-IDF ranked search across uploaded documents and web sources |
| Public Chat | Open text-based discussion for all users |
| Private Study Rooms | Invite-only rooms with text and voice chat (max 2 rooms per user) |
| Direct Messaging | Private messaging between users via user ID |
| Voice Chat | Real-time voice communication inside private rooms via WebRTC |
| File Uploads | Upload PDFs, notes, and question papers with text extraction |
| Question Paper Analysis | Topic extraction and exam probability estimation using ML |
| Secure Authentication | JWT-based login with bcrypt password hashing |
| Role-Based Access Control | Admin and user role management |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python — FastAPI |
| Frontend | HTML, CSS, JavaScript — React |
| Database | PostgreSQL (production), SQLite (development) |
| AI Integration | OpenAI API |
| Search Engine | Scikit-learn, NLTK |
| Web Automation | Selenium, BeautifulSoup |
| Real-time Chat | WebSockets |
| Voice Chat | WebRTC |
| Authentication | JWT Tokens |
| Caching | Redis |

---

## Team

| Member | Role | Branch |
|--------|------|--------|
| Kishore V | Backend + Chat + Security | `feature/backend` |
| Likhith D Girish | AI + Automation | `feature/ai` |
| Jash Ashish Ladani | Frontend + Search | `feature/frontend` |

---

## Repository Structure

```
SIKH/
├── backend/                  ← Kishore V (FastAPI, Auth, Chat, WebSockets)
│   ├── auth/                 ← JWT authentication, RBAC, protected routes
│   ├── chat/                 ← WebSocket chat, private rooms, direct messaging
│   ├── security/             ← Encryption, intrusion detection
│   └── api/                  ← REST API routes
│
├── frontend/                 ← Jash Ashish Ladani (HTML/CSS/JS, React)
│   ├── src/                  ← React components and JavaScript
│   ├── components/           ← Reusable UI components
│   └── public/               ← Static assets
│
├── ai_module/                ← Likhith D Girish (AI API, ML, Automation)
│   ├── assistant/            ← AI chatbot integration (OpenAI API)
│   ├── question_paper/       ← Question paper analysis, topic extraction
│   └── automation/           ← Selenium, web scraping
│
├── search_engine/            ← Jash Ashish Ladani (TF-IDF, Cosine Similarity)
│   ├── indexing/             ← Inverted index, tokenization, stop-word removal
│   └── algorithms/           ← TF-IDF, cosine similarity ranking
│
├── security/                 ← Kishore V (shared security utilities)
├── docs/                     ← Shared project documentation
├── tests/                    ← All test files
│   ├── backend/
│   ├── frontend/
│   └── ai/
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API will be available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm start
```

### AI Module

```bash
cd ai_module
pip install -r requirements.txt
# Add your OpenAI API key to .env before running
```

---

## Branching Strategy

```
main              ← Stable, production-ready code only. No direct pushes.
dev               ← Integration branch. All features merge here first.
feature/backend   ← Kishore V
feature/ai        ← Likhith D Girish
feature/frontend  ← Jash Ashish Ladani
```

### Daily Git Workflow

```bash
# 1. Pull the latest changes from dev before starting
git pull origin dev

# 2. Switch to your own feature branch
git checkout feature/your-branch

# 3. Work on your assigned module

# 4. Stage and commit your changes
git add .
git commit -m "feat: describe what you built"

# 5. Push to your branch
git push origin feature/your-branch

# 6. When your feature is complete, open a Pull Request into dev
```

> **Rules:**
> - Never push directly to `main`
> - Never commit `.env` files or API keys
> - Always pull from `dev` before starting work

---

## Development Phases

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Planning & Design | ✅ Complete |
| 2 | Backend Development | 🔄 In Progress |
| 3 | Search Engine | 🔄 In Progress |
| 4 | AI Integration | 🔄 In Progress |
| 5 | Community System | ⏳ Pending |
| 6 | Security | ⏳ Pending |
| 7 | Integration & Testing | ⏳ Pending |
| 8 | Deployment | ⏳ Pending |

---

## Environment Variables

Each member must create a `.env` file inside their module directory. **Never commit `.env` files.**

```env
# backend/.env
DATABASE_URL=postgresql://user:password@localhost/sikh_db
JWT_SECRET=your_secret_key_here
REDIS_URL=redis://localhost:6379

# ai_module/.env
OPENAI_API_KEY=your_openai_key_here
```

---

## Commit Convention

All commits must follow this prefix format for consistency:

| Prefix | Purpose |
|--------|---------|
| `feat:` | New feature added |
| `fix:` | Bug fix |
| `docs:` | Documentation update |
| `style:` | UI or CSS changes only |
| `refactor:` | Code restructure without feature change |
| `test:` | Adding or updating tests |

---

*SIKH — Built as a Final Year Project, March 2026.*
