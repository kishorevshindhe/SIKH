"""
Module: Web Scraper — FastAPI RouterM
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import os

from web_scraper import (
    search_web,
    search_academic_sites,
    scrape_page,
    scrape_wikipedia,
    scrape_geeksforgeeks,
    scrape_study_materials,
    search_and_download_pdfs,
    ACADEMIC_SITES,
)

router = APIRouter()


# REQUEST / RESPONSE SCHEMAS

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10


class AcademicSearchRequest(BaseModel):
    query: str
    sites: Optional[list[str]] = None   # e.g. ["wikipedia", "geeksforgeeks"]
    max_results: int = 10


class ScrapeRequest(BaseModel):
    url: str


class StudyMaterialRequest(BaseModel):
    query: str
    include_wikipedia: bool = True
    include_geeksforgeeks: bool = True
    download_pdfs: bool = False
    max_web_results: int = 5


class PDFDownloadRequest(BaseModel):
    query: str
    max_downloads: int = 3
    save_dir: str = "downloads"


# ENDPOINTS

@router.get("/sites")
def list_academic_sites():
    """
    List all supported academic sites for targeted searching.
    """
    return {"sites": list(ACADEMIC_SITES.keys())}


@router.post("/search")
def search_endpoint(body: SearchRequest):
    """
    Search DuckDuckGo for study material links.

    Returns a list of search results with title, URL, snippet, and is_pdf flag.
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    results = search_web(body.query, max_results=body.max_results)
    return {
        "query":   body.query,
        "count":   len(results),
        "results": results,
    }


@router.post("/search/academic")
def search_academic_endpoint(body: AcademicSearchRequest):
    """
    Search within specific academic sites (Wikipedia, GFG, etc.).

    Optionally pass a list of site keys to target specific sites.
    If sites is omitted, searches all supported academic sites.
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    results = search_academic_sites(
        body.query,
        sites=body.sites,
        max_results=body.max_results,
    )
    return {
        "query":   body.query,
        "sites":   body.sites or list(ACADEMIC_SITES.keys()),
        "count":   len(results),
        "results": results,
    }


@router.post("/scrape")
def scrape_endpoint(body: ScrapeRequest):
    """
    Scrape content from a specific URL.
    Tries BeautifulSoup first, falls back to Selenium for JS-heavy pages.
    """
    if not body.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL. Must start with http.")

    result = scrape_page(body.url)
    if not result:
        raise HTTPException(status_code=422, detail=f"Could not scrape content from: {body.url}")

    return result


@router.post("/scrape/wikipedia")
def scrape_wikipedia_endpoint(body: SearchRequest):
    """
    Fetch and scrape a Wikipedia article for a given topic.
    """
    result = scrape_wikipedia(body.query)
    if not result:
        raise HTTPException(status_code=404, detail=f"No Wikipedia article found for: {body.query}")
    return result


@router.post("/scrape/geeksforgeeks")
def scrape_gfg_endpoint(body: SearchRequest):
    """
    Search and scrape the top GeeksForGeeks article for a given topic.
    """
    result = scrape_geeksforgeeks(body.query)
    if not result:
        raise HTTPException(status_code=404, detail=f"No GFG article found for: {body.query}")
    return result


@router.post("/study-materials")
def study_materials_endpoint(body: StudyMaterialRequest):
    """
    Full pipeline: search + scrape study materials for a query.

    Returns:
    - General web search results
    - Scraped page content
    - Wikipedia article (if enabled)
    - GeeksForGeeks article (if enabled)
    - Downloaded PDF paths (if enabled)
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    result = scrape_study_materials(
        query=body.query,
        include_wikipedia=body.include_wikipedia,
        include_geeksforgeeks=body.include_geeksforgeeks,
        download_pdfs=body.download_pdfs,
        max_web_results=body.max_web_results,
    )
    return result


@router.post("/download-pdfs")
def download_pdfs_endpoint(body: PDFDownloadRequest):
    """
    Search for PDFs related to a query and download them.

    Returns a list of local file paths where PDFs were saved.
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    paths = search_and_download_pdfs(
        query=body.query,
        save_dir=body.save_dir,
        max_downloads=body.max_downloads,
    )
    return {
        "query":            body.query,
        "downloaded_count": len(paths),
        "file_paths":       paths,
    }


# STANDALONE SERVER — for independent testing

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(title="SIKH Web Scraper API", version="1.0")
    app.include_router(router, prefix="/api/scraper", tags=["Web Scraper"])

    print("Starting SIKH Web Scraper server...")
    print("Docs at: http://localhost:8001/docs")
    uvicorn.run(app, host="0.0.0.0", port=8001)
