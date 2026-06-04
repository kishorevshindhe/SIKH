# ─────────────────────────────────────────────────
# REPLACE CONTENTS OF: ai_module/assistant_routes.py
# ─────────────────────────────────────────────────

import re
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database.database import get_db
from database.models import LibraryFile
from auth.dependencies import get_current_user

router = APIRouter()

# ── Put your NEW HuggingFace token in .env file as:
#    HF_TOKEN=hf_your_new_token_here
# ── Then load it:
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"  # free, strong model
HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"


# ─────────────────────────────────────────
# HELPER: find relevant chunks from files
# ─────────────────────────────────────────

def find_relevant_chunks(content_text: str, question: str, max_chunks: int = 4, chunk_size: int = 80) -> List[str]:
    if not content_text:
        return []

    terms = [t.lower().strip() for t in question.split() if len(t.strip()) > 3]

    # Split into paragraphs, fallback to sentences
    parts = [p.strip() for p in re.split(r'\n{2,}', content_text) if p.strip()]
    if len(parts) <= 1:
        parts = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content_text) if s.strip()]

    # Break long parts into smaller chunks
    chunks = []
    for part in parts:
        words = part.split()
        if len(words) > chunk_size:
            for i in range(0, len(words), chunk_size):
                chunks.append(' '.join(words[i:i+chunk_size]))
        else:
            chunks.append(part)

    # Score chunks
    scored = []
    for chunk in chunks:
        cl = chunk.lower()
        score = sum(1 for t in terms if t in cl)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:max_chunks]]


# ─────────────────────────────────────────
# REQUEST SCHEMA
# ─────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    file_ids: Optional[List[str]] = None  # if None, search all user files


# ─────────────────────────────────────────
# ASK ENDPOINT
# ─────────────────────────────────────────

@router.post("/ask")
async def ask_ai(
    body: AskRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if not HF_TOKEN:
        raise HTTPException(status_code=500, detail="AI not configured — add HF_TOKEN to .env")

    # Get files to search
    query = db.query(LibraryFile).filter(LibraryFile.owner_id == current_user.id)
    if body.file_ids:
        query = query.filter(LibraryFile.id.in_(body.file_ids))
    files = query.all()

    if not files:
        raise HTTPException(status_code=404, detail="No files found to search")

    # Collect relevant chunks across all files
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
            "answer": "I couldn't find relevant content in your uploaded files for this question. Try uploading more documents or rephrasing your question.",
            "sources": [],
            "context_used": 0
        }

    # Build context (limit to ~1500 words to stay within model limits)
    context = "\n\n---\n\n".join(all_chunks[:6])
    if len(context) > 3000:
        context = context[:3000] + "..."

    # Build prompt
    prompt = f"""<s>[INST] You are SIKH, an intelligent study assistant. Answer the user's question using ONLY the provided context from their uploaded documents. Be clear, structured, and helpful. If the answer is not in the context, say so honestly.

CONTEXT FROM UPLOADED DOCUMENTS:
{context}

USER QUESTION: {body.question}

Provide a clear answer with key points. If relevant, mention which part of the content supports your answer. [/INST]"""

    # Call HuggingFace Inference API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                HF_URL,
                headers={
                    "Authorization": f"Bearer {HF_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 512,
                        "temperature": 0.4,
                        "top_p": 0.9,
                        "do_sample": True,
                        "return_full_text": False
                    }
                }
            )

        if response.status_code == 503:
            return {
                "answer": "The AI model is loading (cold start). Please try again in 20 seconds.",
                "sources": sources,
                "context_used": len(all_chunks)
            }

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"AI API error: {response.text}")

        result = response.json()

        # Extract text from response
        if isinstance(result, list) and result:
            answer = result[0].get("generated_text", "").strip()
        elif isinstance(result, dict):
            answer = result.get("generated_text", "").strip()
        else:
            answer = str(result)

        # Clean up any repeated prompt text
        if "[/INST]" in answer:
            answer = answer.split("[/INST]")[-1].strip()

        return {
            "answer": answer,
            "sources": sources,
            "context_used": len(all_chunks)
        }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI request timed out. Try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


# ─────────────────────────────────────────
# SUMMARIZE ENDPOINT
# ─────────────────────────────────────────

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

    # Take first ~2000 chars for summary
    content_preview = file.content_text[:2000]

    prompt = f"""<s>[INST] Summarize the following document content in a clear, structured way. Include: main topics covered, key concepts, and important points a student should know.

DOCUMENT: {file.filename}

CONTENT:
{content_preview}

Provide a concise summary with bullet points for key topics. [/INST]"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                HF_URL,
                headers={
                    "Authorization": f"Bearer {HF_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 400,
                        "temperature": 0.3,
                        "return_full_text": False
                    }
                }
            )

        result = response.json()
        if isinstance(result, list) and result:
            summary = result[0].get("generated_text", "").strip()
        else:
            summary = str(result)

        if "[/INST]" in summary:
            summary = summary.split("[/INST]")[-1].strip()

        return {
            "file_id": file_id,
            "filename": file.filename,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")