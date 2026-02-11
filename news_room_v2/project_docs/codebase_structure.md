# Codebase Structure (News Room V2)

This document provides a detailed breakdown of the file structure and the role of each component.

## Root Directory (`news_room_v2/`)

- **`app.py`**: The main Flask application entry point.
    - Routes:
        - `/`: Redirects to `/newsroom`.
        - `/newsroom`: Displays daily news grid.
        - `/recommendations`: Triggers `core/recommendation.py` logic.
        - `/scrapbook`: Manages saved articles.
- **`run_web.sh`**: Bash script to start the Flask server (`python3 app.py`).
- **`requirements.txt`**: Python dependencies.

## `scrapers/` Directory

Responsible for data collection from external sources.

- **`history_scraper.py`**: The primary scraper for fetching news from external sources.
    - Supports batch processing for past dates and daily updates.
    - Output: JSON files in `scraped_data_history/YYYYMM/`.
- **`full_text_scraper.py`**: Fetches the **entire article content** (not just summary) for deep analysis. Used for tagging comparison.

## `core/` Directory

Contains the core business logic, AI models, and data processing utilities.

- **`recommendation.py`**: **The Heart of the Recommendation System**.
    - **`recommend_articles(persona_name)`**: Main function. Orchestrates vector search and LLM reranking.
    - **`llm_rerank(candidates, persona_data)`**: Sends candidates to Gemini API for reordering based on persona nuances.
    - **`parse_persona_markdown(persona_name)`**: Reads `.md` files from `personas/` to extract preferences.
- **`vector_store.py`**: Manages the Vector Database (ChromaDB).
    - **`init_chromadb()`**: Initializes or loads the database.
    - **`add_articles(articles)`**: Embeds article text using `sentence-transformers` and adds to index.
    - **`query_articles(query_text)`**: Performs semantic search.
- **`tag_generator.py`**: Extracts keywords from text.
    - Uses **KeyBERT** model.
    - Uses **Kiwi** for Korean morphological analysis (noun extraction).
    - Essential for enriching raw scraped data before indexing.
- **`compare_tags_full.py`**: Utility script to compare keyword extraction performance between KeyBERT and GLiNER on full text.

## `personas/` Directory

Defines the "User Profiles" for personalized recommendations.

- **`persona_20s.md`**: Example persona for a user in their 20s.
    - **Structure**:
        - `## Interest Groups`: Key topics (Tech, Career, Economy).
        - `## Sentence Preferences`: Natural language description of interests.
        - `## Negative Keywords`: Forbidden words (e.g., "Coupang").
        - `## Negative Sentences`: Topics to avoid entirely (e.g., Politics).

## `templates/` Directory

HTML files for the Flask web interface.

- **`newsroom.html`**: The main dashboard grid view.
- **`recommendations.html`**: Displays the specialized recommendation list with AI reasoning.
- **`scrapbook.html`**: Saved articles view.

## `project_docs/` Directory

Contains documentation for developers (this file).
