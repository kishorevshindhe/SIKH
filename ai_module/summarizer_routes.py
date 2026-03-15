"""
Module: AI Summarization — FastAPI Router
"""
import os
import shutil
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional

from ai_summarizer import (
    summarize_pdf,
    summarize_multiple_pdfs,
    summarize_text,
    summarize_scraped_content,
    summarize_chat_history,
    generate_study_guide,
)

router = APIRouter()

VALID_STYLES = {"academic", "bullet", "brief", "detailed"}


# REQUEST / RESPONSE SCHEMAS

class TextSummarizeRequest(BaseModel):
    text:  str
    style: str = "academic"
    focus: Optional[str] = None


class ChatSummarizeRequest(BaseModel):
    messages: list[dict]   # [{"role": "user"/"assistant", "content": str}]
    topic:    Optional[str] = None


class ScrapeSummarizeRequest(BaseModel):
    scrape_output: dict          # output from web_scraper.scrape_study_materials()
    style:         str = "bullet"
    focus:         Optional[str] = None


class StudyGuideRequest(BaseModel):
    topic:         str
    pdf_summaries: Optional[list[str]] = None
    web_summaries: Optional[list[str]] = None
    qp_analysis:   Optional[dict]      = None  # from question_paper_analysis


# ENDPOINTS

@router.post("/text")
def summarize_text_endpoint(body: TextSummarizeRequest):
    """
    Summarize a plain text string.

    Styles: academic | bullet | brief | detailed
    """
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    if body.style not in VALID_STYLES:
        raise HTTPException(status_code=400, detail=f"Style must be one of: {VALID_STYLES}")

    summary = summarize_text(body.text, style=body.style, focus=body.focus)
    return {"style": body.style, "focus": body.focus, "summary": summary}


@router.post("/pdf")
async def summarize_pdf_endpoint(
    style: str           = Form("academic"),
    focus: Optional[str] = Form(None),
    file:  UploadFile    = File(...),
):
    """
    Upload a single PDF and receive a structured summary.

    Form fields:
        style — academic | bullet | brief | detailed
        focus — optional topic focus (e.g. "sorting algorithms")
        file  — the PDF file
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    if style not in VALID_STYLES:
        raise HTTPException(status_code=400, detail=f"Style must be one of: {VALID_STYLES}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = summarize_pdf(tmp_path, style=style, focus=focus)
    finally:
        os.unlink(tmp_path)

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@router.post("/pdf/batch")
async def summarize_pdfs_batch_endpoint(
    style:    str           = Form("academic"),
    focus:    Optional[str] = Form(None),
    combined: bool          = Form(False),
    files:    list[UploadFile] = File(...),
):
    """
    Upload multiple PDFs and receive individual + optional combined summary.

    Form fields:
        style    — academic | bullet | brief | detailed
        focus    — optional topic focus
        combined — if true, also generates one unified summary
        files    — multiple PDF uploads
    """
    if style not in VALID_STYLES:
        raise HTTPException(status_code=400, detail=f"Style must be one of: {VALID_STYLES}")

    tmp_paths = []
    for f in files:
        if not f.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{f.filename} is not a PDF.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(f.file, tmp)
            tmp_paths.append(tmp.name)

    try:
        result = summarize_multiple_pdfs(
            tmp_paths, style=style, focus=focus, combined=combined
        )
    finally:
        for p in tmp_paths:
            os.unlink(p)

    return result


@router.post("/web-content")
def summarize_web_content_endpoint(body: ScrapeSummarizeRequest):
    """
    Summarize the output from the web scraper's scrape_study_materials().

    Pass the full scrape_output dict from POST /api/scraper/study-materials.
    """
    if not body.scrape_output:
        raise HTTPException(status_code=400, detail="scrape_output cannot be empty.")

    result = summarize_scraped_content(
        body.scrape_output, style=body.style, focus=body.focus
    )
    return result


@router.post("/chat")
def summarize_chat_endpoint(body: ChatSummarizeRequest):
    """
    Summarize a chat discussion history.

    Pass a list of {"role": "user"/"assistant", "content": str} message dicts.
    """
    if not body.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

    summary = summarize_chat_history(body.messages, topic=body.topic)
    return {"topic": body.topic, "summary": summary}


@router.post("/study-guide")
def study_guide_endpoint(body: StudyGuideRequest):
    """
    Generate a full study guide combining PDF summaries, web summaries,
    and question paper analysis results.

    This endpoint ties together all of Member 2's modules:
    - PDF summaries  → from /api/summarizer/pdf or /pdf/batch
    - Web summaries  → from /api/summarizer/web-content
    - qp_analysis    → from /api/question-paper/analyze

    Example request body:
    {
        "topic": "Data Structures",
        "pdf_summaries": ["Binary trees are...", "Graphs are used..."],
        "web_summaries": ["According to GFG, ..."],
        "qp_analysis": { "topic_probabilities": [...] }
    }
    """
    if not body.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    guide = generate_study_guide(
        topic=body.topic,
        pdf_summaries=body.pdf_summaries,
        web_summaries=body.web_summaries,
        qp_analysis=body.qp_analysis,
    )
    return {"topic": body.topic, "study_guide": guide}


# STANDALONE SERVER

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(title="SIKH AI Summarizer API", version="1.0")
    app.include_router(router, prefix="/api/summarizer", tags=["AI Summarizer"])

    print("Starting SIKH AI Summarizer server...")
    print("Docs at: http://localhost:8002/docs")
    uvicorn.run(app, host="0.0.0.0", port=8002)
