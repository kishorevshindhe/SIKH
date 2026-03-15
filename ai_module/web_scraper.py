"""
Module: Web Scraper


    Scrapes study materials from the web based on user queries.
    1. Search the web for study material links (via DuckDuckGo)
    2. Scrape content from academic sites (Wikipedia, GeeksForGeeks, etc.)
    3. Download PDFs found in search results
    4. BeautifulSoup for static pages, Selenium as fallback for JS-heavy pages

"""

import os
import re
import time
import logging
import requests

from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, quote_plus

from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Selenium (used only as fallback)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

load_dotenv()

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="[SIKH Scraper] %(message)s")
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 10      # seconds
SELENIUM_WAIT   = 8       # seconds to wait for JS content
MAX_RESULTS     = 10      # max search results to return

# Academic sites that are well-structured for scraping
ACADEMIC_SITES = {
    "wikipedia":      "en.wikipedia.org",
    "geeksforgeeks":  "www.geeksforgeeks.org",
    "tutorialspoint": "www.tutorialspoint.com",
    "javatpoint":     "www.javatpoint.com",
    "w3schools":      "www.w3schools.com",
}


# 1. HELPERS

def _get(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
    """Safe GET request. Returns None on failure."""
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        log.warning(f"GET failed for {url}: {e}")
        return None


def _is_pdf_url(url: str) -> bool:
    """Check if a URL points to a PDF file."""
    return url.lower().endswith(".pdf") or "filetype=pdf" in url.lower()


def _clean_text(text: str) -> str:
    """Remove excess whitespace from scraped text."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _sanitize_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    return re.sub(r"[^\w\-_.]", "_", name)[:100]


# 2. DUCKDUCKGO SEARCH  (no API key needed)

def search_web(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """
    Search DuckDuckGo for study material links related to a query.
    Uses DuckDuckGo HTML search (no API key required).

    Args:
        query:       Search query string (e.g. "binary search tree tutorial").
        max_results: Maximum number of results to return.

    Returns:
        List of dicts: [{"title": str, "url": str, "snippet": str, "is_pdf": bool}]
    """
    log.info(f"Searching web for: '{query}'")
    encoded = quote_plus(query)
    search_url = f"https://html.duckduckgo.com/html/?q={encoded}"

    resp = _get(search_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for result in soup.select(".result"):
        title_tag = result.select_one(".result__title a")
        snippet_tag = result.select_one(".result__snippet")

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href  = title_tag.get("href", "")

        # DuckDuckGo wraps URLs — extract the actual URL
        if "uddg=" in href:
            from urllib.parse import parse_qs, urlparse as _up
            qs = parse_qs(_up(href).query)
            href = qs.get("uddg", [href])[0]

        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

        if href and href.startswith("http"):
            results.append({
                "title":   title,
                "url":     href,
                "snippet": snippet,
                "is_pdf":  _is_pdf_url(href),
            })

        if len(results) >= max_results:
            break

    log.info(f"Found {len(results)} results for '{query}'")
    return results


def search_academic_sites(
    query: str,
    sites: Optional[list[str]] = None,
    max_results: int = MAX_RESULTS,
) -> list[dict]:
    """
    Search specifically within academic sites using site: operator.

    Args:
        query:       Search query string.
        sites:       List of site keys from ACADEMIC_SITES dict.
                     Defaults to all academic sites.
        max_results: Max results per site.

    Returns:
        Combined list of search results from all specified sites.
    """
    target_sites = sites or list(ACADEMIC_SITES.keys())
    all_results = []

    for site_key in target_sites:
        domain = ACADEMIC_SITES.get(site_key)
        if not domain:
            log.warning(f"Unknown site key: {site_key}")
            continue

        site_query = f"{query} site:{domain}"
        results = search_web(site_query, max_results=max_results // len(target_sites) or 2)
        for r in results:
            r["source"] = site_key
        all_results.extend(results)
        time.sleep(0.5)  # polite delay between requests

    return all_results


# 3. BEAUTIFULSOUP SCRAPER  (static pages)

def scrape_with_bs4(url: str) -> Optional[dict]:
    """
    Scrape a webpage using BeautifulSoup (for static HTML pages).

    Args:
        url: The URL to scrape.

    Returns:
        Dict with title, url, content, and word_count — or None on failure.
    """
    log.info(f"Scraping (BS4): {url}")
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise: scripts, styles, nav, footer, ads
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "iframe", "noscript"]):
        tag.decompose()

    # Title
    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)

    # Main content — try common content containers first
    content_tag = (
        soup.find("article") or
        soup.find("main") or
        soup.find(id=re.compile(r"content|main|article", re.I)) or
        soup.find(class_=re.compile(r"content|article|post|entry", re.I)) or
        soup.body
    )

    content = _clean_text(content_tag.get_text(separator="\n")) if content_tag else ""

    # Headings for structure
    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]

    return {
        "title":      title,
        "url":        url,
        "content":    content,
        "headings":   headings,
        "word_count": len(content.split()),
        "method":     "beautifulsoup",
    }


# 4. SELENIUM SCRAPER  (JS-heavy pages — fallback)

def _build_selenium_driver() -> Optional["webdriver.Chrome"]:
    """Build a headless Chrome driver."""
    if not SELENIUM_AVAILABLE:
        log.error("Selenium not installed. Run: pip install selenium webdriver-manager")
        return None

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={DEFAULT_HEADERS['User-Agent']}")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        log.error(f"Failed to start Chrome driver: {e}")
        return None


def scrape_with_selenium(url: str) -> Optional[dict]:
    """
    Scrape a webpage using Selenium (for JS-rendered pages).
    Use this as a fallback when BS4 returns empty content.

    Args:
        url: The URL to scrape.

    Returns:
        Dict with title, url, content, and word_count — or None on failure.
    """
    log.info(f"Scraping (Selenium): {url}")
    driver = _build_selenium_driver()
    if not driver:
        return None

    try:
        driver.get(url)
        WebDriverWait(driver, SELENIUM_WAIT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(1.5)  # extra wait for lazy-loaded content

        title = driver.title

        # Extract text from body
        body = driver.find_element(By.TAG_NAME, "body")
        content = _clean_text(body.text)

        # Headings
        headings = [
            el.text.strip()
            for el in driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3")
            if el.text.strip()
        ]

        return {
            "title":      title,
            "url":        url,
            "content":    content,
            "headings":   headings,
            "word_count": len(content.split()),
            "method":     "selenium",
        }
    except Exception as e:
        log.error(f"Selenium scrape failed for {url}: {e}")
        return None
    finally:
        driver.quit()


# 5. SMART SCRAPER  (BS4 first, Selenium fallback)

def scrape_page(url: str, min_words: int = 100) -> Optional[dict]:
    """
    Smart scraper: tries BeautifulSoup first.
    Falls back to Selenium if content is too short (JS-rendered page).

    Args:
        url:       The URL to scrape.
        min_words: Minimum word count to consider BS4 scrape successful.

    Returns:
        Scraped content dict, or None on failure.
    """
    result = scrape_with_bs4(url)

    if result and result["word_count"] >= min_words:
        return result

    # BS4 got too little content — try Selenium
    log.info(f"BS4 returned low content ({result['word_count'] if result else 0} words). "
             f"Falling back to Selenium for: {url}")
    return scrape_with_selenium(url)


# 6. SITE-SPECIFIC SCRAPERS

def scrape_wikipedia(query: str) -> Optional[dict]:
    """
    Fetch a Wikipedia article directly by search term.

    Args:
        query: Topic to search on Wikipedia.

    Returns:
        Scraped Wikipedia article dict.
    """
    formatted = query.strip().replace(" ", "_")
    url = f"https://en.wikipedia.org/wiki/{quote_plus(formatted)}"
    log.info(f"Fetching Wikipedia: {url}")

    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Wikipedia's main content div
    content_div = soup.find(id="mw-content-text")
    if not content_div:
        return scrape_page(url)

    # Remove references, tables of contents, edit buttons
    for tag in content_div.find_all(["sup", "table", "div"], class_=re.compile(r"toc|reflist|navbox")):
        tag.decompose()

    title = soup.find(id="firstHeading")
    title_text = title.get_text(strip=True) if title else query

    content = _clean_text(content_div.get_text(separator="\n"))
    headings = [h.get_text(strip=True) for h in content_div.find_all(["h2", "h3"])]

    return {
        "title":      title_text,
        "url":        url,
        "content":    content,
        "headings":   headings,
        "word_count": len(content.split()),
        "source":     "wikipedia",
        "method":     "beautifulsoup",
    }


def scrape_geeksforgeeks(query: str) -> Optional[dict]:
    """
    Search GeeksForGeeks and scrape the top result.

    Args:
        query: Topic to search on GeeksForGeeks.

    Returns:
        Scraped article dict or None.
    """
    results = search_web(f"{query} site:geeksforgeeks.org", max_results=3)
    if not results:
        return None

    top_url = results[0]["url"]
    log.info(f"Scraping GeeksForGeeks: {top_url}")

    resp = _get(top_url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # GFG article content
    article = soup.find("article") or soup.find(class_=re.compile(r"article-content|entry-content"))

    if article:
        for tag in article(["script", "style", "ins"]):
            tag.decompose()
        content = _clean_text(article.get_text(separator="\n"))
        headings = [h.get_text(strip=True) for h in article.find_all(["h2", "h3"])]
    else:
        # Fallback to smart scraper
        return scrape_page(top_url)

    title = soup.title.get_text(strip=True) if soup.title else query

    return {
        "title":      title,
        "url":        top_url,
        "content":    content,
        "headings":   headings,
        "word_count": len(content.split()),
        "source":     "geeksforgeeks",
        "method":     "beautifulsoup",
    }


# 7. PDF DOWNLOADER

def find_pdf_links(search_results: list[dict]) -> list[dict]:
    """
    Filter search results to return only PDF links.

    Args:
        search_results: Output from search_web().

    Returns:
        List of PDF result dicts.
    """
    return [r for r in search_results if r.get("is_pdf")]


def download_pdf(url: str, save_dir: str = "downloads") -> Optional[str]:
    """
    Download a PDF from a URL and save it locally.

    Args:
        url:      URL of the PDF file.
        save_dir: Directory to save the PDF (created if it doesn't exist).

    Returns:
        Local file path of the downloaded PDF, or None on failure.
    """
    os.makedirs(save_dir, exist_ok=True)

    # Derive filename from URL
    raw_name = urlparse(url).path.split("/")[-1] or "document.pdf"
    filename = _sanitize_filename(raw_name)
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    save_path = os.path.join(save_dir, filename)

    # Skip if already downloaded
    if os.path.exists(save_path):
        log.info(f"PDF already exists: {save_path}")
        return save_path

    log.info(f"Downloading PDF: {url}")
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=30, stream=True)
        resp.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size_kb = os.path.getsize(save_path) / 1024
        log.info(f"Saved: {save_path} ({size_kb:.1f} KB)")
        return save_path

    except Exception as e:
        log.error(f"PDF download failed for {url}: {e}")
        return None


def search_and_download_pdfs(
    query: str,
    save_dir: str = "downloads",
    max_downloads: int = 3,
) -> list[str]:
    """
    Search for PDFs related to a query and download them.

    Args:
        query:         Search query (e.g. "data structures notes pdf").
        save_dir:      Directory to save downloaded PDFs.
        max_downloads: Maximum number of PDFs to download.

    Returns:
        List of local file paths of downloaded PDFs.
    """
    pdf_query = f"{query} filetype:pdf"
    results = search_web(pdf_query, max_results=MAX_RESULTS)
    pdf_results = find_pdf_links(results)

    if not pdf_results:
        log.info("No direct PDF links found. Checking all results for embedded PDFs...")
        pdf_results = results  # try all URLs anyway

    downloaded = []
    for result in pdf_results[:max_downloads]:
        path = download_pdf(result["url"], save_dir)
        if path:
            downloaded.append(path)

    log.info(f"Downloaded {len(downloaded)} PDF(s) for query: '{query}'")
    return downloaded


# 8. MAIN PIPELINE — query → search → scrape → results

def scrape_study_materials(
    query: str,
    include_wikipedia:     bool = True,
    include_geeksforgeeks: bool = True,
    download_pdfs:         bool = False,
    pdf_save_dir:          str  = "downloads",
    max_web_results:       int  = 5,
) -> dict:
    """
    Full pipeline: search + scrape study materials for a given query.

    Args:
        query:                 The user's search query.
        include_wikipedia:     Whether to scrape Wikipedia directly.
        include_geeksforgeeks: Whether to scrape GeeksForGeeks.
        download_pdfs:         Whether to download PDF files found.
        pdf_save_dir:          Directory for downloaded PDFs.
        max_web_results:       Max general web results to scrape.

    Returns:
        Dict containing search results, scraped content, and PDF paths.
    """
    log.info(f"Starting study material scrape for: '{query}'")
    output = {
        "query":           query,
        "search_results":  [],
        "scraped_pages":   [],
        "wikipedia":       None,
        "geeksforgeeks":   None,
        "downloaded_pdfs": [],
    }

    # Step 1: General web search
    log.info("Step 1: General web search...")
    results = search_web(query, max_results=max_web_results)
    output["search_results"] = results

    # Step 2: Scrape top web results (skip PDFs for content scraping)
    log.info("Step 2: Scraping top web pages...")
    for result in results:
        if result["is_pdf"]:
            continue
        scraped = scrape_page(result["url"])
        if scraped:
            # Keep only a preview (first 1500 words) to save memory
            words = scraped["content"].split()
            scraped["content_preview"] = " ".join(words[:1500])
            scraped["content"] = scraped["content_preview"]
            output["scraped_pages"].append(scraped)
        time.sleep(0.5)  # polite crawl delay

    # Step 3: Wikipedia
    if include_wikipedia:
        log.info("Step 3: Fetching Wikipedia article...")
        wiki = scrape_wikipedia(query)
        if wiki:
            words = wiki["content"].split()
            wiki["content"] = " ".join(words[:2000])  # limit to 2000 words
            output["wikipedia"] = wiki

    # Step 4: GeeksForGeeks
    if include_geeksforgeeks:
        log.info("Step 4: Scraping GeeksForGeeks...")
        gfg = scrape_geeksforgeeks(query)
        if gfg:
            words = gfg["content"].split()
            gfg["content"] = " ".join(words[:2000])
            output["geeksforgeeks"] = gfg

    # Step 5: Download PDFs if requested
    if download_pdfs:
        log.info("Step 5: Downloading PDFs...")
        output["downloaded_pdfs"] = search_and_download_pdfs(
            query, save_dir=pdf_save_dir
        )

    total_pages = len(output["scraped_pages"])
    has_wiki    = output["wikipedia"] is not None
    has_gfg     = output["geeksforgeeks"] is not None
    total_pdfs  = len(output["downloaded_pdfs"])

    log.info(
        f"Scrape complete — {total_pages} pages | "
        f"Wikipedia: {'✓' if has_wiki else '✗'} | "
        f"GFG: {'✓' if has_gfg else '✗'} | "
        f"PDFs: {total_pdfs}"
    )
    return output


# 9. ENTRY POINT — quick CLI test

if __name__ == "__main__":
    import sys
    import json

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "binary search tree"

    print(f"\n{'='*60}")
    print(f"  SIKH Web Scraper — Query: '{query}'")
    print(f"{'='*60}\n")

    result = scrape_study_materials(
        query=query,
        include_wikipedia=True,
        include_geeksforgeeks=True,
        download_pdfs="--pdf" in sys.argv,
    )

    # ── Print summary ──────────────────────────────────────────────────────────
    print(f"\n── SEARCH RESULTS ({len(result['search_results'])}) ──────────────────────────")
    for r in result["search_results"]:
        pdf_tag = "[PDF]" if r["is_pdf"] else ""
        print(f"  {pdf_tag} {r['title'][:60]}")
        print(f"       {r['url'][:80]}")

    print(f"\n── SCRAPED PAGES ({len(result['scraped_pages'])}) ────────────────────────────")
    for page in result["scraped_pages"]:
        print(f"  [{page['method'].upper()}] {page['title'][:55]} ({page['word_count']} words)")
        if page["headings"]:
            print(f"    Headings: {', '.join(page['headings'][:4])}")

    if result["wikipedia"]:
        w = result["wikipedia"]
        print(f"\n── WIKIPEDIA: {w['title']} ({w['word_count']} words) ──────────────")
        print(f"  Sections: {', '.join(w['headings'][:5])}")
        print(f"  Preview:  {' '.join(w['content'].split()[:40])}...")

    if result["geeksforgeeks"]:
        g = result["geeksforgeeks"]
        print(f"\n── GEEKSFORGEEKS: {g['title'][:50]} ({g['word_count']} words) ────")
        print(f"  Preview: {' '.join(g['content'].split()[:40])}...")

    if result["downloaded_pdfs"]:
        print(f"\n── DOWNLOADED PDFs ──────────────────────────────────────────")
        for p in result["downloaded_pdfs"]:
            print(f"  {p}")

    # Save full output as JSON
    out_file = "scrape_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n[SIKH] Full results saved to {out_file}")
