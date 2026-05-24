import io
import uuid
import base64
import PyPDF2
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