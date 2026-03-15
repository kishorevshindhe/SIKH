"""
 AI Assistant — FastAPI Router


Description:
    FastAPI router exposing the AI Assistant as HTTP endpoints.
    Member 1 mounts this router onto the main backend server.

    Mount in main.py:
        from ai_module.assistant_router import router as assistant_router
        app.include_router(assistant_router, prefix="/api/assistant", tags=["AI Assistant"])

"""

import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ai_assistant import (
    chat,
    clear_session,
    explain_concept,
    new_session,
    summarize_pdf,
)

router = APIRouter()


# REQUEST / RESPONSE SCHEMAS

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None   # if None, a new session is auto-created


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    history_length: int


class ExplainRequest(BaseModel):
    concept: str
    session_id: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    message: str


# ENDPOINTS

@router.post("/session/new", response_model=SessionResponse)
def create_session():
    """
    Create a new conversation session.
    Call this when a user opens the AI Assistant for the first time.

    Returns:
        session_id: Use this in all subsequent /chat and /summarize calls.
    """
    sid = new_session()
    return {"session_id": sid, "message": "New session created."}


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(body: ChatRequest):
    """
    Send a message to the AI Assistant.
    Maintains full conversation history for the session.

    - If session_id is not provided, a new session is automatically created.
    - Supports follow-up questions (multi-turn) within the same session.
    """
    sid = body.session_id or new_session()

    try:
        result = chat(
            user_message=body.message,
            session_id=sid,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Assistant error: {str(e)}")


@router.post("/summarize", response_model=ChatResponse)
async def summarize_endpoint(
    session_id: str = Form(None),
    file: UploadFile = File(...),
):
    """
    Upload a PDF and get a summarization.
    Accepts multipart/form-data with:
        - file: the PDF file
        - session_id: (optional) existing session ID

    The summary is added to the session history so users can
    ask follow-up questions about the document.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    sid = session_id or new_session()

    # Save the uploaded file to a temp location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        result = summarize_pdf(pdf_path=tmp_path, session_id=sid)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization error: {str(e)}")

    finally:
        # Always clean up the temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/explain", response_model=ChatResponse)
def explain_endpoint(body: ExplainRequest):
    """
    Request a step-by-step explanation of any academic concept.
    Example: { "concept": "Dijkstra's algorithm", "session_id": "..." }
    """
    sid = body.session_id or new_session()

    try:
        result = explain_concept(concept=body.concept, session_id=sid)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation error: {str(e)}")


@router.delete("/session/{session_id}", response_model=SessionResponse)
def clear_session_endpoint(session_id: str):
    """
    Clear the conversation history for a session.
    Use this when the user clicks 'New Chat' in the UI.
    """
    clear_session(session_id)
    return {"session_id": session_id, "message": "Session cleared successfully."}


# HEALTH CHECK

@router.get("/health")
def health_check():
    """Quick check to confirm the AI Assistant module is running."""
    return {"status": "ok", "module": "AI Assistant", "project": "SIKH"}