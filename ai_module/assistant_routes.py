import re
import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from groq import Groq

from database.database import get_db
from database.models import LibraryFile
from auth.dependencies import get_current_user

load_dotenv()

router = APIRouter()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def find_relevant_chunks(content_text: str, question: str, max_chunks: int = 4, chunk_size: int = 80) -> List[str]:
    if not content_text:
        return []
    terms = [t.lower().strip() for t in question.split() if len(t.strip()) > 3]
    parts = [p.strip() for p in re.split(r'\n{2,}', content_text) if p.strip()]
    if len(parts) <= 1:
        parts = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content_text) if s.strip()]
    chunks = []
    for part in parts:
        words = part.split()
        if len(words) > chunk_size:
            for i in range(0, len(words), chunk_size):
                chunks.append(' '.join(words[i:i+chunk_size]))
        else:
            chunks.append(part)
    scored = []
    for chunk in chunks:
        cl = chunk.lower()
        score = sum(1 for t in terms if t in cl)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:max_chunks]]


class AskRequest(BaseModel):
    question: str
    file_ids: Optional[List[str]] = None


@router.post("/ask")
async def ask_ai(
    body: AskRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    query = db.query(LibraryFile).filter(LibraryFile.owner_id == current_user.id)
    if body.file_ids:
        query = query.filter(LibraryFile.id.in_(body.file_ids))
    files = query.all()

    if not files:
        raise HTTPException(status_code=404, detail="No files found to search")

    all_chunks = []
    sources = []

    for file in files:
        chunks = find_relevant_chunks(file.content_text, body.question)
        if chunks:
            all_chunks.extend(chunks)
            sources.append({
                "file_id": file.id,
                "filename": file.filename,
                "filetype": file.filetype
            })

    if not all_chunks:
        return {
            "answer": "I couldn't find relevant content in your uploaded files. Try uploading more documents or rephrasing your question.",
            "sources": [],
            "context_used": 0
        }

    context = "\n\n---\n\n".join(all_chunks[:6])
    if len(context) > 3000:
        context = context[:3000] + "..."

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are SIKH, an intelligent study assistant. Answer only from the provided context from the user's uploaded documents. Be clear and helpful."
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {body.question}"
                }
            ],
            max_tokens=512,
            temperature=0.4
        )
        answer = response.choices[0].message.content.strip()

        return {
            "answer": answer,
            "sources": sources,
            "context_used": len(all_chunks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


@router.post("/summarize/{file_id}")
async def summarize_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    file = db.query(LibraryFile).filter(
        LibraryFile.id == file_id,
        LibraryFile.owner_id == current_user.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if not file.content_text:
        raise HTTPException(status_code=400, detail="No content extracted from this file")

    content_preview = file.content_text[:2000]

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are SIKH, an intelligent study assistant. Summarize documents clearly for students."
                },
                {
                    "role": "user",
                    "content": f"Summarize this document called '{file.filename}':\n\n{content_preview}\n\nUse bullet points for key topics."
                }
            ],
            max_tokens=400,
            temperature=0.3
        )
        summary = response.choices[0].message.content.strip()

        return {
            "file_id": file_id,
            "filename": file.filename,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")