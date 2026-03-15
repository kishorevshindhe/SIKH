"""
Module: Question Paper Analysis

Description:
    Analyzes uploaded PDF question papers to:
    1. Extract and clean text from PDFs
    2. Identify important topics using TF-IDF
    3. Detect repeated topic patterns across multiple papers
    4. Estimate topic probability for future exams

Dependencies:
    pip install pymupdf scikit-learn nltk openai python-dotenv
"""

import os
import re
import json
from collections import Counter, defaultdict
from typing import Optional

import fitz  # PyMuPDF
import nltk
import numpy as np
from dotenv import load_dotenv
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize, sent_tokenize
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer

# ── Download required NLTK data (run once) ────────────────────────────────────
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)

load_dotenv()

# ── OpenAI client ──────────────────────────────────────────────────────────────
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 1. PDF TEXT EXTRACTIO
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract raw text from a PDF file using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text as a single string.
    """
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()


# 2. TEXT PREPROCESSING

def preprocess_text(text: str) -> list[str]:
    """
    Clean and tokenize text: lowercase, remove noise, lemmatize, remove stopwords.

    Args:
        text: Raw text string.

    Returns:
        List of cleaned tokens.
    """
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words("english"))

    # Lowercase and remove non-alphabetic characters
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    tokens = word_tokenize(text)

    # Remove stopwords, short tokens, and lemmatize
    tokens = [
        lemmatizer.lemmatize(t)
        for t in tokens
        if t not in stop_words and len(t) > 2
    ]
    return tokens


# 3. IMPORTANT TOPICS EXTRACTION (TF-IDF)

def extract_important_topics(texts: list[str], top_n: int = 15) -> list[dict]:
    """
    Use TF-IDF across multiple documents to find the most important topics.
    Each 'document' is one question paper.

    Args:
        texts: List of raw text strings, one per question paper.
        top_n: Number of top topics to return per paper.

    Returns:
        List of dicts: [{"paper_index": int, "topics": [{"term": str, "score": float}]}]
    """
    # Preprocess each paper into a clean string for TF-IDF
    cleaned_docs = [" ".join(preprocess_text(t)) for t in texts]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),   # single words + bigrams (e.g. "binary tree")
        max_df=0.95,          # ignore terms that appear in >95% of docs
        min_df=1,
        max_features=500,
    )
    tfidf_matrix = vectorizer.fit_transform(cleaned_docs)
    feature_names = vectorizer.get_feature_names_out()

    results = []
    for i, row in enumerate(tfidf_matrix):
        scores = row.toarray()[0]
        # Get indices of top N scores
        top_indices = np.argsort(scores)[::-1][:top_n]
        topics = [
            {"term": feature_names[idx], "score": round(float(scores[idx]), 4)}
            for idx in top_indices
            if scores[idx] > 0
        ]
        results.append({"paper_index": i, "topics": topics})

    return results


# 4. REPEATED PATTERN DETECTION


def detect_repeated_patterns(texts: list[str], top_n: int = 20) -> list[dict]:
    """
    Find topics/terms that repeatedly appear across multiple question papers.

    Args:
        texts: List of raw text strings, one per question paper.
        top_n: Number of top repeated patterns to return.

    Returns:
        List of dicts sorted by frequency: [{"term": str, "frequency": int, "papers": [int]}]
    """
    # Map each term to which paper indices it appeared in
    term_to_papers: dict[str, set] = defaultdict(set)

    for paper_idx, text in enumerate(texts):
        tokens = set(preprocess_text(text))   # unique tokens per paper
        # Also extract bigrams
        token_list = preprocess_text(text)
        bigrams = {f"{token_list[i]} {token_list[i+1]}" for i in range(len(token_list) - 1)}
        all_terms = tokens | bigrams

        for term in all_terms:
            term_to_papers[term].add(paper_idx)

    # Only keep terms that appear in more than one paper
    repeated = {
        term: papers
        for term, papers in term_to_papers.items()
        if len(papers) > 1
    }

    # Sort by frequency descending
    sorted_patterns = sorted(repeated.items(), key=lambda x: len(x[1]), reverse=True)[:top_n]

    return [
        {
            "term": term,
            "frequency": len(papers),   # number of papers it appeared in
            "papers": sorted(list(papers)),
        }
        for term, papers in sorted_patterns
    ]



# 5. TOPIC PROBABILITY ESTIMATION


def estimate_topic_probability(
    repeated_patterns: list[dict],
    total_papers: int,
    top_n: int = 10,
) -> list[dict]:
    """
    Estimate the probability of each repeated topic appearing in a future exam.
    Formula: probability = frequency / total_papers

    Args:
        repeated_patterns: Output from detect_repeated_patterns().
        total_papers: Total number of papers analyzed.
        top_n: Number of top probable topics to return.

    Returns:
        List of dicts: [{"topic": str, "probability": float, "likelihood": str}]
    """
    results = []
    for pattern in repeated_patterns[:top_n]:
        prob = round(pattern["frequency"] / total_papers, 2)

        # Human-readable likelihood label
        if prob >= 0.75:
            likelihood = "Very High"
        elif prob >= 0.50:
            likelihood = "High"
        elif prob >= 0.25:
            likelihood = "Moderate"
        else:
            likelihood = "Low"

        results.append({
            "topic": pattern["term"],
            "appeared_in": f"{pattern['frequency']}/{total_papers} papers",
            "probability": prob,
            "likelihood": likelihood,
        })

    # Sort by probability descending
    results.sort(key=lambda x: x["probability"], reverse=True)
    return results



# 6. AI-POWERED TOPIC SUMMARY (OpenAI)


def generate_ai_topic_summary(
    high_prob_topics: list[dict],
    subject_hint: Optional[str] = None,
) -> str:
    """
    Use OpenAI to generate a human-readable analysis summary based on
    the high-probability topics found.

    Args:
        high_prob_topics: Output from estimate_topic_probability().
        subject_hint: Optional subject name to guide the AI (e.g. "Data Structures").

    Returns:
        AI-generated summary string.
    """
    topic_lines = "\n".join(
        [
            f"- {t['topic']} ({t['likelihood']} likelihood, {t['appeared_in']})"
            for t in high_prob_topics
        ]
    )

    subject_context = f"Subject: {subject_hint}\n" if subject_hint else ""

    prompt = f"""You are an academic assistant helping students prepare for exams.
{subject_context}
Based on the analysis of multiple past question papers, the following topics have been identified as likely to appear in future exams:

{topic_lines}

Please provide:
1. A brief summary of the most important topics to focus on.
2. Any clusters or relationships you notice between the topics.
3. 3-5 specific study tips for a student preparing for this exam.

Keep the response concise and student-friendly."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()



# 7. MAIN ANALYSIS PIPELINE


def analyze_question_papers(
    pdf_paths: list[str],
    subject_hint: Optional[str] = None,
    top_topics: int = 15,
    top_patterns: int = 20,
    top_probabilities: int = 10,
) -> dict:
    """
    Full pipeline: extract → preprocess → topics → patterns → probabilities → AI summary.

    Args:
        pdf_paths: List of paths to PDF question papers.
        subject_hint: Optional subject name for AI summary context.
        top_topics: Number of top TF-IDF topics per paper.
        top_patterns: Number of top repeated patterns to detect.
        top_probabilities: Number of topics to include in probability report.

    Returns:
        Dictionary containing the full analysis report.
    """
    if not pdf_paths:
        raise ValueError("No PDF paths provided.")

    print(f"[SIKH] Analyzing {len(pdf_paths)} question paper(s)...")

    # Step 1: Extract text from all PDFs
    texts = []
    paper_names = []
    for path in pdf_paths:
        print(f"  → Extracting: {os.path.basename(path)}")
        text = extract_text_from_pdf(path)
        texts.append(text)
        paper_names.append(os.path.basename(path))

    # Step 2: Extract important topics per paper (TF-IDF)
    print("[SIKH] Extracting important topics (TF-IDF)...")
    topics_per_paper = extract_important_topics(texts, top_n=top_topics)

    # Step 3: Detect repeated patterns across papers
    print("[SIKH] Detecting repeated patterns...")
    repeated_patterns = detect_repeated_patterns(texts, top_n=top_patterns)

    # Step 4: Estimate topic probabilities
    print("[SIKH] Estimating topic probabilities...")
    topic_probabilities = estimate_topic_probability(
        repeated_patterns,
        total_papers=len(texts),
        top_n=top_probabilities,
    )

    # Step 5: Generate AI summary (only if OpenAI key is available)
    ai_summary = None
    if os.getenv("OPENAI_API_KEY"):
        print("[SIKH] Generating AI summary...")
        ai_summary = generate_ai_topic_summary(topic_probabilities, subject_hint)
    else:
        ai_summary = "OpenAI API key not set. Skipping AI summary."

    # Build final report
    report = {
        "total_papers_analyzed": len(pdf_paths),
        "paper_names": paper_names,
        "topics_per_paper": [
            {
                "paper": paper_names[r["paper_index"]],
                "top_topics": r["topics"],
            }
            for r in topics_per_paper
        ],
        "repeated_patterns": repeated_patterns,
        "topic_probabilities": topic_probabilities,
        "ai_summary": ai_summary,
    }

    print("[SIKH] Analysis complete.")
    return report


# ══════════════════════════════════════════════════════════════════════════════
# 8. ENTRY POINT (for quick testing)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # Usage: python question_paper_analysis.py paper1.pdf paper2.pdf ...
    # Example: python question_paper_analysis.py papers/ds_2022.pdf papers/ds_2023.pdf
    pdf_files = sys.argv[1:] if len(sys.argv) > 1 else []

    if not pdf_files:
        print("Usage: python question_paper_analysis.py <paper1.pdf> <paper2.pdf> ...")
        print("Example: python question_paper_analysis.py papers/ds_2022.pdf papers/ds_2023.pdf")
        sys.exit(1)

    # Run the analysis
    result = analyze_question_papers(
        pdf_paths=pdf_files,
        subject_hint="Data Structures",   # Change to your subject
        top_topics=15,
        top_patterns=20,
        top_probabilities=10,
    )

    # Print results
    print("\n" + "=" * 60)
    print("SIKH - QUESTION PAPER ANALYSIS REPORT")
    print("=" * 60)

    print(f"\nPapers analyzed: {result['total_papers_analyzed']}")
    for name in result["paper_names"]:
        print(f"  • {name}")

    print("\n── TOP TOPICS PER PAPER ──────────────────────────────────")
    for paper_data in result["topics_per_paper"]:
        print(f"\n{paper_data['paper']}:")
        for topic in paper_data["top_topics"][:8]:   # show top 8 for readability
            print(f"  {topic['term']:<30} score: {topic['score']}")

    print("\n── REPEATED PATTERNS ACROSS PAPERS ──────────────────────")
    for pattern in result["repeated_patterns"][:10]:
        print(f"  {pattern['term']:<30} in {pattern['frequency']} papers")

    print("\n── TOPIC PROBABILITY FORECAST ────────────────────────────")
    for t in result["topic_probabilities"]:
        bar = "█" * int(t["probability"] * 20)
        print(f"  {t['topic']:<30} {t['probability']*100:>5.0f}%  {bar}  [{t['likelihood']}]")

    print("\n── AI SUMMARY ────────────────────────────────────────────")
    print(result["ai_summary"])

    # Save report as JSON
    output_file = "analysis_report.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n[SIKH] Report saved to {output_file}")