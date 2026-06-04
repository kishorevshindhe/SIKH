import io
import uuid
import base64
import PyPDF2
import re
from typing import List
from docx import Document

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import LibraryFile, User
from auth.dependencies import get_current_user
from chat.file_crypto import encrypt_file, decrypt_file

router = APIRouter(
    prefix="/library",
    tags=["Library"]
)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


# ── Text Extraction ───────────────────────────────────────────────────
def extract_text_from_file(filename: str, data: bytes) -> str:
    text = ""
    try:
        if filename.lower().endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(data))
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif filename.lower().endswith(".docx"):
            doc = Document(io.BytesIO(data))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif filename.lower().endswith(".txt"):
            text = data.decode("utf-8", errors="ignore")
    except Exception as e:
        print("TEXT EXTRACTION ERROR:", e)
    return text


# ── Upload File ───────────────────────────────────────────────────────
@router.post("/upload")
async def upload_library_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    data = await file.read()

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 25MB.")

    extracted_text = extract_text_from_file(file.filename, data)
    encrypted = encrypt_file(data)
    file_id = str(uuid.uuid4())

    new_file = LibraryFile(
        file_id=file_id,
        filename=file.filename,
        filesize=len(data),
        filetype=file.content_type or "application/octet-stream",
        encrypted_data=encrypted,
        content_text=extracted_text,
        owner_id=current_user.id
    )
    db.add(new_file)
    db.commit()

    return {
        "message": "File uploaded successfully",
        "file_id": file_id,
        "filename": file.filename
    }


# ── Get My Files ──────────────────────────────────────────────────────
@router.get("/files")
def get_library_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    files = db.query(LibraryFile).filter(
        LibraryFile.owner_id == current_user.id
    ).all()
    return [
        {
            "file_id": f.file_id,
            "filename": f.filename,
            "filesize": f.filesize,
            "filetype": f.filetype,
            "content_text": f.content_text or "",
            "uploaded_at": str(f.created_at)
        }
        for f in files
    ]


# ── Download File ─────────────────────────────────────────────────────
@router.get("/download/{file_id}")
def download_library_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file = db.query(LibraryFile).filter(
        LibraryFile.file_id == file_id,
        LibraryFile.owner_id == current_user.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    decrypted = decrypt_file(file.encrypted_data)

    return Response(
        content=decrypted,
        media_type=file.filetype,
        headers={
            "Content-Disposition": f'attachment; filename="{file.filename}"'
        }
    )


# ── Delete File ───────────────────────────────────────────────────────
@router.delete("/delete/{file_id}")
def delete_library_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file = db.query(LibraryFile).filter(
        LibraryFile.file_id == file_id,
        LibraryFile.owner_id == current_user.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    db.delete(file)
    db.commit()
    return {"message": "File deleted successfully"}
## ADD THIS TO: backend/routes/library_routes.py
## Place this after your existing routes

import re
from typing import List, Optional

# ─────────────────────────────────────────
# HELPER: Extract matching chunks from text
# ─────────────────────────────────────────

def extract_matching_chunks(content_text: str, query: str, context_words: int = 60, max_chunks: int = 5) -> List[dict]:
    """
    Splits content_text into paragraphs/sentences,
    finds all chunks matching the query,
    returns them with highlighted context.
    """
    if not content_text or not query:
        return []

    query_lower = query.lower()
    query_terms = [t.strip() for t in query_lower.split() if len(t.strip()) > 2]

    # Split into paragraphs first, then fallback to sentences
    paragraphs = [p.strip() for p in re.split(r'\n{2,}|\r\n{2,}', content_text) if p.strip()]
    
    # If no paragraph breaks, split into sentences
    if len(paragraphs) <= 1:
        paragraphs = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content_text) if s.strip()]

    # Further split very long paragraphs into ~60 word chunks
    final_chunks = []
    for para in paragraphs:
        words = para.split()
        if len(words) > context_words * 2:
            for i in range(0, len(words), context_words):
                chunk = ' '.join(words[i:i + context_words])
                if chunk:
                    final_chunks.append(chunk)
        else:
            final_chunks.append(para)

    # Score each chunk: how many query terms appear?
    scored_chunks = []
    for chunk in final_chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for term in query_terms if term in chunk_lower)
        if score > 0:
            scored_chunks.append((score, chunk))

    # Sort by score descending, take top N
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored_chunks[:max_chunks]

    results = []
    for score, chunk in top_chunks:
        # Build highlighted version — wrap matched terms in <mark> tags
        highlighted = chunk
        for term in sorted(query_terms, key=len, reverse=True):  # longest first to avoid double-wrapping
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            highlighted = pattern.sub(lambda m: f'<mark>{m.group()}</mark>', highlighted)
        
        results.append({
            "text": chunk,
            "highlighted": highlighted,
            "score": score,
            "word_count": len(chunk.split())
        })

    return results


# ─────────────────────────────────────────
# SEARCH ROUTE
# ─────────────────────────────────────────

@router.get("/library/search")
def search_library(
    q: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Search inside uploaded documents.
    Returns matching files with multiple content chunks per file,
    each chunk containing the relevant paragraph with highlighted terms.
    
    Example: GET /library/search?q=deadlock&limit=10
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")

    query_str = q.strip()

    # Find files whose content_text contains the query
    matching_files = db.query(LibraryFile).filter(
        LibraryFile.owner_id == current_user.id,
        LibraryFile.content_text.ilike(f"%{query_str}%")
    ).all()

    if not matching_files:
        return {
            "query": query_str,
            "total_files": 0,
            "results": []
        }

    results = []

    for file in matching_files:
        chunks = extract_matching_chunks(
            content_text=file.content_text,
            query=query_str,
            context_words=60,
            max_chunks=5  # max 5 chunks per file
        )

        if not chunks:
            continue

        results.append({
            "file_id": file.id,
            "filename": file.filename,
            "filetype": file.filetype,
            "uploaded_at": str(file.uploaded_at)[:10] if file.uploaded_at else None,
            "filesize": file.filesize,
            "total_chunks_found": len(chunks),
            "chunks": chunks  # list of {text, highlighted, score, word_count}
        })

    # Sort files by their best chunk score
    results.sort(key=lambda x: x["chunks"][0]["score"] if x["chunks"] else 0, reverse=True)

    return {
        "query": query_str,
        "total_files": len(results),
        "results": results
    }
