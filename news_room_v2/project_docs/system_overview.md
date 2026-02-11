# System Overview (News Room V2)

This document provides a high-level overview of the personalized news recommendation system.

## 1. Goal
To provide a highly personalized news feed that aligns with a user's **specific interests** (e.g., Tech, Career) while strictly **filtering out negative preferences** (e.g., Politics, Coupang).

## 2. Core Architecture

The system follows a pipeline architecture: **Scrape -> Tag -> Index -> Recommend**.

```mermaid
graph TD
    A[Scraper (Playwright)] -->|JSON| B(Raw Data)
    B --> C[Tag Generator (KeyBERT)]
    C -->|JSON + Keywords| D(Tagged Data)
    D --> E[Vector Store (ChromaDB)]
    E --> F[Recommendation Engine]
    F -->|Candidates| G[LLM Reranker (Gemini)]
    G -->|Final List| H[Web UI (Flask)]
    I[Persona Definition (.md)] --> F
    I --> G
```

## 3. Key Components

### A. Data Collection (Scrapers)
- **Tool**: Playwright (Headless Browser)
- **Source**: Naver News (Media: Chosun Ilbo, JoongAng Ilbo, etc.)
- **Output**: JSON files partitioned by Date and Media ID (e.g., `023_20260211.json`).

### B. Natural Language Processing (NLP)
- **Tagging**: Uses `KeyBERT` with `Kiwi` (Korean Morpheme Analyzer) to extract high-quality keywords from article titles and summaries.
- **Why**: Keyword tags are crucial for the Vector Store to distinguish specific topics effectively.

### C. Vector Store (ChromaDB)
- **Embedding**: Uses `intfloat/multilingual-e5-small` for high-performance Korean text embeddings.
- **Function**: Stores all articles with metadata. Allows semantic search based on User Interest Groups.

### D. Recommendation Engine (Hybrid)
1.  **Stage 1: Vector Search (Broad Filtering)**
    - Retrieves top 50 candidates based on semantic similarity to user's "Interest Groups".
    - **Negative Filtering**: Applies a penalty score (`-0.3`) to articles containing restricted keywords defined in Schema.
2.  **Stage 2: LLM Reranking (Precision Ranking)**
    - Uses **Gemini-3-Flash** (Preview) to analyze the top candidates.
    - INPUT: Rank, Title, URL, Keywords (No Summary to save tokens).
    - LOGIC: Reorders based on "Sentence Preferences" (Context/Nuance).
    - OUTPUT: Final Top 10 list with reasoning.

### E. User Interface
- **Flask App**: Simple web server to display:
    - Daily News Grid (`/newsroom`)
    - Personalized Recommendations (`/recommendations`)
    - Scrapbook (`/scrapbook`)

## 4. Tech Stack
- **Language**: Python 3.9+
- **Web Framework**: Flask
- **Browser Automation**: Playwright
- **Vector DB**: ChromaDB
- **LLM**: Google Gemini API
- **NLP**: KeyBERT, Kiwi, SentenceTransformers
