"""
AI Assistant (Core)

 Core AI assistant that:
    1. Answers academic questions
    2. Summarizes uploaded PDF documents
    3. Explains concepts step-by-step
    4. Maintains multi-turn conversation history per session

"""

import os
import uuid
from typing import Optional

import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── System prompt that defines the assistant's academic personality ────────────
SYSTEM_PROMPT = """You are SIKH Assistant, an intelligent academic helper built into the 
Secure Intelligent Knowledge Hub (SIKH) platform.

Your responsibilities:
- Answer academic questions clearly and accurately
- Summarize study documents and notes when provided
- Explain concepts step-by-step when asked
- Help students understand difficult topics across any subject
- Be concise but thorough — students are studying, not reading essays

Tone: Friendly, patient, and encouraging. Always focused on helping the student learn.

Rules:
- If asked to explain a concept, always break it into numbered steps
- If given a document to summarize, extract the key points as a bullet list first, 
  then give a short paragraph summary
- If you don't know something, say so honestly
- Never make up facts, formulas, or citations
"""


# SESSION MANAGER — stores conversation history per user session

class SessionManager:
    """
    Manages per-session conversation histories in memory.
    Each session_id maps to a list of OpenAI message dicts.

    In production, replace this with Redis (already in SIKH's tech stack).
    """

    def __init__(self):
        self._sessions: dict[str, list[dict]] = {}

    def get_or_create(self, session_id: str) -> list[dict]:
        """Return existing history or create a new session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        return self._sessions[session_id]

    def append(self, session_id: str, role: str, content: str):
        """Add a message to a session's history."""
        history = self.get_or_create(session_id)
        history.append({"role": role, "content": content})

    def clear(self, session_id: str):
        """Clear a session's conversation history."""
        self._sessions[session_id] = []

    def delete(self, session_id: str):
        """Delete a session entirely."""
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        """Return all active session IDs."""
        return list(self._sessions.keys())


# Global session manager instance
session_manager = SessionManager()


# PDF TEXT EXTRACTION

def extract_text_from_pdf(pdf_path: str, max_chars: int = 12000) -> str:
    """
    Extract text from a PDF file.
    Truncates to max_chars to stay within OpenAI's context limits.

    Args:
        pdf_path: Path to the PDF file.
        max_chars: Maximum characters to extract (default 12000 ≈ ~3000 tokens).

    Returns:
        Extracted text string.
    """
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
            if len(text) >= max_chars:
                break
    return text.strip()[:max_chars]


# CORE CHAT FUNCTION

def chat(
    user_message: str,
    session_id: str,
    pdf_path: Optional[str] = None,
) -> dict:
    """
    Send a message to the AI assistant and get a response.
    Maintains full conversation history for the given session.

    Args:
        user_message: The student's message or question.
        session_id:   Unique session identifier (one per user/conversation).
        pdf_path:     Optional path to a PDF to include as context.

    Returns:
        dict with keys:
            - reply (str): The assistant's response
            - session_id (str): The session ID used
            - history_length (int): Number of turns in this session
    """
    # If a PDF is provided, prepend its content to the user message
    if pdf_path:
        pdf_text = extract_text_from_pdf(pdf_path)
        user_message = (
            f"I have uploaded a document. Here is its content:\n\n"
            f"---\n{pdf_text}\n---\n\n"
            f"My request: {user_message}"
        )

    # Add user message to session history
    session_manager.append(session_id, "user", user_message)
    history = session_manager.get_or_create(session_id)

    # Build the full messages payload: system prompt + full history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    # Call OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.4,      # lower = more focused/accurate for academics
        max_tokens=1000,
    )

    reply = response.choices[0].message.content.strip()

    # Store assistant reply in history
    session_manager.append(session_id, "assistant", reply)

    return {
        "reply": reply,
        "session_id": session_id,
        "history_length": len(history),
    }


# CONVENIENCE WRAPPERS

def summarize_pdf(pdf_path: str, session_id: str) -> dict:
    """
    Summarize a PDF document.

    Args:
        pdf_path:   Path to the PDF file.
        session_id: Session ID for conversation tracking.

    Returns:
        Same dict as chat().
    """
    return chat(
        user_message="Please summarize this document. First list the key points as bullets, then give a short paragraph summary.",
        session_id=session_id,
        pdf_path=pdf_path,
    )


def explain_concept(concept: str, session_id: str) -> dict:
    """
    Request a step-by-step explanation of a concept.

    Args:
        concept:    The concept or topic to explain.
        session_id: Session ID for conversation tracking.

    Returns:
        Same dict as chat().
    """
    return chat(
        user_message=f"Explain the following concept step-by-step: {concept}",
        session_id=session_id,
    )


def new_session() -> str:
    """
    Generate a new unique session ID.

    Returns:
        A UUID string to use as session_id.
    """
    return str(uuid.uuid4())


def clear_session(session_id: str):
    """Clear conversation history for a session (start fresh)."""
    session_manager.clear(session_id)


# ENTRY POINT — interactive terminal test

if __name__ == "__main__":
    print("=" * 55)
    print("  SIKH AI Assistant — Terminal Test")
    print("  Commands: 'quit', 'clear', 'summarize <path>'")
    print("=" * 55)

    session_id = new_session()
    print(f"  Session ID: {session_id[:8]}...\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        elif user_input.lower() == "quit":
            print("Goodbye!")
            break
        elif user_input.lower() == "clear":
            clear_session(session_id)
            print("[Session cleared. Starting fresh.]\n")
        elif user_input.lower().startswith("summarize "):
            path = user_input[10:].strip()
            if not os.path.exists(path):
                print(f"[File not found: {path}]\n")
                continue
            print("SIKH: Summarizing document...\n")
            result = summarize_pdf(path, session_id)
            print(f"SIKH: {result['reply']}\n")
        else:
            result = chat(user_input, session_id)
            print(f"SIKH: {result['reply']}\n")