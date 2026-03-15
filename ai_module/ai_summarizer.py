"""

Module: AI Summarization
Description:

    Summarizes content from multiple sources:
    1. Single PDF document
    2. Multiple PDFs (batch summarization)
    3. Scraped web content (from web_scraper.py output)
    4. Chat discussion history
    5. Combined study guide from multiple sources


"""

import os
import json
import tiktoken
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
import fitz  # PyMuPDF

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL        = "gpt-4o-mini"
MAX_TOKENS   = 1000          # max tokens in each summary response
CHUNK_SIZE   = 10000         # chars per chunk for long documents
OVERLAP      = 200           # chars of overlap between chunks


# 1. TOKEN / LENGTH UTILITIES

def count_tokens(text: str, model: str = MODEL) -> int:
    """Count the number of tokens in a text string."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """
    Split long text into overlapping chunks so nothing important is cut off.

    Args:
        text:       Input text.
        chunk_size: Max characters per chunk.
        overlap:    Overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


# 2. CORE SUMMARIZER

def _call_openai(prompt: str, system: str) -> str:
    """Internal helper — calls OpenAI and returns the response text."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content.strip()


def summarize_text(
    text: str,
    style: str = "academic",
    focus: Optional[str] = None,
) -> str:
    """
    Summarize a block of text.

    Args:
        text:  The text to summarize.
        style: One of 'academic', 'bullet', 'brief', 'detailed'.
        focus: Optional focus area (e.g. "sorting algorithms").

    Returns:
        Summary string.
    """
    system = (
        "You are an expert academic summarizer for the SIKH learning platform. "
        "Produce clear, student-friendly summaries that highlight the most important "
        "concepts, definitions, and takeaways."
    )

    focus_line = f"\nFocus especially on content related to: {focus}" if focus else ""

    style_instructions = {
        "academic": (
            "Structure your summary as:\n"
            "1. **Overview** (2-3 sentences)\n"
            "2. **Key Concepts** (bullet list)\n"
            "3. **Important Details**\n"
            "4. **Takeaway** (one sentence)"
        ),
        "bullet": (
            "Provide a concise bullet-point summary. "
            "Each bullet should be one clear, complete idea. "
            "Aim for 6-10 bullets."
        ),
        "brief": (
            "Write a very short summary in 3-5 sentences. "
            "Capture only the most essential information."
        ),
        "detailed": (
            "Write a comprehensive summary covering all major points. "
            "Include definitions, examples mentioned, and relationships between concepts. "
            "Use headers to organize sections."
        ),
    }.get(style, style_instructions := "Summarize the following text clearly.")

    prompt = (
        f"{style_instructions}{focus_line}\n\n"
        f"Text to summarize:\n{text}"
    )

    # If text is too long, use map-reduce chunking
    chunks = chunk_text(text)
    if len(chunks) == 1:
        return _call_openai(prompt, system)

    # Map: summarize each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        chunk_prompt = (
            f"Summarize this section (part {i+1} of {len(chunks)}):\n{chunk}"
        )
        chunk_summaries.append(_call_openai(chunk_prompt, system))

    # Reduce: combine chunk summaries into one final summary
    combined = "\n\n".join(chunk_summaries)
    final_prompt = (
        f"{style_instructions}{focus_line}\n\n"
        f"Combine these section summaries into one cohesive summary:\n{combined}"
    )
    return _call_openai(final_prompt, system)


# 3. PDF SUMMARIZATION

def extract_pdf_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()


def summarize_pdf(
    pdf_path: str,
    style: str = "academic",
    focus: Optional[str] = None,
) -> dict:
    """
    Summarize a single PDF document.

    Args:
        pdf_path: Path to the PDF file.
        style:    Summary style — 'academic', 'bullet', 'brief', 'detailed'.
        focus:    Optional topic focus.

    Returns:
        Dict with filename, word_count, summary, and style.
    """
    print(f"[SIKH Summarizer] Summarizing PDF: {os.path.basename(pdf_path)}")
    text = extract_pdf_text(pdf_path)

    if not text.strip():
        return {
            "filename": os.path.basename(pdf_path),
            "error":    "Could not extract text from PDF.",
            "summary":  None,
        }

    summary = summarize_text(text, style=style, focus=focus)

    return {
        "filename":   os.path.basename(pdf_path),
        "word_count": len(text.split()),
        "style":      style,
        "focus":      focus,
        "summary":    summary,
    }


def summarize_multiple_pdfs(
    pdf_paths: list[str],
    style: str = "academic",
    focus: Optional[str] = None,
    combined: bool = False,
) -> dict:
    """
    Summarize multiple PDFs individually, and optionally produce a combined summary.

    Args:
        pdf_paths: List of PDF file paths.
        style:     Summary style.
        focus:     Optional topic focus.
        combined:  If True, also generates one unified summary across all PDFs.

    Returns:
        Dict with per-document summaries and optional combined summary.
    """
    print(f"[SIKH Summarizer] Summarizing {len(pdf_paths)} PDF(s)...")
    individual = [summarize_pdf(p, style=style, focus=focus) for p in pdf_paths]

    result = {
        "total_documents": len(pdf_paths),
        "style":           style,
        "individual":      individual,
        "combined":        None,
    }

    if combined and len(individual) > 1:
        print("[SIKH Summarizer] Generating combined summary...")
        all_summaries = "\n\n---\n\n".join(
            [f"Document: {s['filename']}\n{s['summary']}"
             for s in individual if s.get("summary")]
        )
        focus_line = f"Focus on: {focus}\n\n" if focus else ""
        combine_prompt = (
            f"{focus_line}"
            "The following are summaries from multiple related documents. "
            "Produce one unified, comprehensive summary that synthesizes all key information, "
            "highlights common themes, and notes any important differences:\n\n"
            f"{all_summaries}"
        )
        system = (
            "You are an expert academic summarizer. Synthesize multiple document summaries "
            "into one clear, well-structured overview for a student."
        )
        result["combined"] = _call_openai(combine_prompt, system)

    return result


# 4. WEB CONTENT SUMMARIZATION

def summarize_scraped_content(
    scrape_output: dict,
    style: str = "bullet",
    focus: Optional[str] = None,
) -> dict:
    """
    Summarize content from web_scraper.scrape_study_materials() output.

    Args:
        scrape_output: Dict returned by scrape_study_materials().
        style:         Summary style.
        focus:         Optional topic focus.

    Returns:
        Dict with summaries of each scraped source.
    """
    query   = scrape_output.get("query", "")
    results = {}

    print(f"[SIKH Summarizer] Summarizing web content for: '{query}'")

    # Summarize Wikipedia
    wiki = scrape_output.get("wikipedia")
    if wiki and wiki.get("content"):
        print("  → Summarizing Wikipedia...")
        results["wikipedia"] = {
            "title":   wiki["title"],
            "url":     wiki["url"],
            "summary": summarize_text(wiki["content"], style=style, focus=focus),
        }

    # Summarize GeeksForGeeks
    gfg = scrape_output.get("geeksforgeeks")
    if gfg and gfg.get("content"):
        print("  → Summarizing GeeksForGeeks...")
        results["geeksforgeeks"] = {
            "title":   gfg["title"],
            "url":     gfg["url"],
            "summary": summarize_text(gfg["content"], style=style, focus=focus),
        }

    # Summarize other scraped pages
    pages = scrape_output.get("scraped_pages", [])
    page_summaries = []
    for page in pages:
        if page.get("content") and page.get("word_count", 0) > 150:
            print(f"  → Summarizing: {page['title'][:50]}...")
            page_summaries.append({
                "title":   page["title"],
                "url":     page["url"],
                "summary": summarize_text(page["content"], style=style, focus=focus),
            })
    results["web_pages"] = page_summaries

    return {
        "query":   query,
        "style":   style,
        "sources": results,
    }


# 5. CHAT DISCUSSION SUMMARIZATION

def summarize_chat_history(
    messages: list[dict],
    topic: Optional[str] = None,
) -> str:
    """
    Summarize a chat conversation history.
    Useful for AI summarization of study room discussions (future feature).

    Args:
        messages: List of {"role": "user"/"assistant", "content": str} dicts.
        topic:    Optional topic hint.

    Returns:
        A summary of the discussion.
    """
    if not messages:
        return "No messages to summarize."

    # Format conversation as readable text
    chat_text = "\n".join(
        [f"{m['role'].upper()}: {m['content']}" for m in messages]
    )

    topic_line = f"This discussion is about: {topic}\n\n" if topic else ""

    prompt = (
        f"{topic_line}"
        "Summarize the following study discussion. Include:\n"
        "1. **Main Topics Discussed**\n"
        "2. **Key Questions Asked**\n"
        "3. **Answers and Explanations Given**\n"
        "4. **Unresolved Questions** (if any)\n\n"
        f"Discussion:\n{chat_text}"
    )

    system = (
        "You are summarizing a student study discussion. "
        "Be concise and highlight the most educationally valuable parts."
    )

    return _call_openai(prompt, system)


# 6. COMBINED STUDY GUIDE GENERATOR

def generate_study_guide(
    topic: str,
    pdf_summaries: Optional[list[str]] = None,
    web_summaries: Optional[list[str]] = None,
    qp_analysis:   Optional[dict]      = None,
) -> str:
    """
    Generate a unified study guide combining all available sources.
    This is the crown jewel — ties together all of Member 2's modules.

    Args:
        topic:         The subject/topic for the study guide.
        pdf_summaries: List of PDF summary strings.
        web_summaries: List of web content summary strings.
        qp_analysis:   Output from question_paper_analysis.analyze_question_papers().

    Returns:
        A comprehensive, formatted study guide as a string.
    """
    print(f"[SIKH Summarizer] Generating study guide for: '{topic}'")

    sections = []

    if pdf_summaries:
        sections.append("PDF NOTES SUMMARIES:\n" + "\n---\n".join(pdf_summaries))

    if web_summaries:
        sections.append("WEB CONTENT SUMMARIES:\n" + "\n---\n".join(web_summaries))

    if qp_analysis:
        top_topics = qp_analysis.get("topic_probabilities", [])
        if top_topics:
            topic_lines = "\n".join(
                [f"- {t['topic']} ({t['likelihood']} likelihood)"
                 for t in top_topics[:8]]
            )
            sections.append(f"HIGH-PROBABILITY EXAM TOPICS:\n{topic_lines}")

    if not sections:
        return "Not enough source material to generate a study guide."

    combined_input = "\n\n".join(sections)

    prompt = (
        f"Generate a comprehensive study guide for the topic: **{topic}**\n\n"
        "Using the following source material, create a well-structured guide with:\n\n"
        "1. **Topic Overview** — what this subject is about\n"
        "2. **Core Concepts** — key definitions and ideas to master\n"
        "3. **Important Topics to Study** — prioritized list\n"
        "4. **Likely Exam Topics** — based on question paper analysis (if available)\n"
        "5. **Study Tips** — 3-5 actionable tips for this subject\n"
        "6. **Quick Revision Checklist** — bullet list of must-know items\n\n"
        f"Source material:\n{combined_input}"
    )

    system = (
        "You are an expert academic tutor creating a study guide for university students. "
        "Be clear, structured, and prioritize the most exam-relevant content."
    )

    return _call_openai(prompt, system)


# 7. ENTRY POINT — CLI test

if __name__ == "__main__":
    import sys

    print("=" * 55)
    print("  SIKH AI Summarizer — Test Mode")
    print("=" * 55)
    print("Options:")
    print("  1. Summarize a PDF")
    print("  2. Summarize multiple PDFs + combined")
    print("  3. Generate a study guide (text input)")
    print("-" * 55)

    choice = input("Choose (1/2/3): ").strip()

    if choice == "1":
        path = input("PDF path: ").strip()
        style = input("Style (academic/bullet/brief/detailed) [academic]: ").strip() or "academic"
        focus = input("Focus topic (optional): ").strip() or None
        result = summarize_pdf(path, style=style, focus=focus)
        print(f"\n── SUMMARY: {result['filename']} ──────────────────────")
        print(result["summary"])

    elif choice == "2":
        paths = input("PDF paths (comma-separated): ").strip().split(",")
        paths = [p.strip() for p in paths]
        style = input("Style (academic/bullet/brief/detailed) [academic]: ").strip() or "academic"
        focus = input("Focus topic (optional): ").strip() or None
        result = summarize_multiple_pdfs(paths, style=style, focus=focus, combined=True)

        for doc in result["individual"]:
            print(f"\n── {doc['filename']} ──────────────────────────────────")
            print(doc["summary"])

        if result["combined"]:
            print("\n── COMBINED SUMMARY ──────────────────────────────────")
            print(result["combined"])

    elif choice == "3":
        topic  = input("Topic: ").strip()
        text   = input("Paste text to summarize (or press Enter to skip): ").strip()
        summaries = [summarize_text(text)] if text else None
        guide = generate_study_guide(topic, pdf_summaries=summaries)
        print(f"\n── STUDY GUIDE: {topic} ──────────────────────────────")
        print(guide)

    else:
        print("Invalid choice.")

    # Save output
    out = {
        "choice": choice,
        "output": result if choice in ("1", "2") else guide if choice == "3" else None
    }
    with open("summarization_output.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\n[SIKH] Output saved to summarization_output.json")
