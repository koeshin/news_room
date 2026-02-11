# News Room V2: Personalized AI News Curator

**News Room V2** is an advanced news recommendation system that delivers highly personalized content by combining vector-based semantic search with LLM-driven reranking. It is designed to understand nuanced user interests while strictly adhering to negative preferences.

![Architecture](project_docs/images/architecture.png)

## Key Features

- **Hybrid Recommendation Engine**:
    - **Stage 1 (Vector Search)**: Filters thousands of articles to find top candidates matching your "Interest Groups" (e.g., Tech, Economy).
    - **Stage 2 (LLM Reranking)**: Uses **Gemini-3-Flash** to reorder articles based on your specific sentence-level preferences (e.g., "I need career advice").
- **Strict Negative Filtering**:
    - Explicitly blocks articles containing specific keywords (e.g., "Coupang") or topics (e.g., "Political Gossip") to reduce information noise.
- **Auto-Tagging System**:
    - Automatically extracts tags using **KeyBERT** and **Kiwi** for precise classification.
- **Daily News Archive**:
    - Automatically scrapes and archives news from major media outlets (Chosun, JoongAng, etc.) via **Playwright**.
- **Continuous Persona Evolution**:
    - Users can evaluate recommendations, and the system automatically refines the persona's keywords and preferences based on this feedback interaction.

## Architecture Overview

The system operates in a **Scrape -> Tag -> Index -> Recommend -> Refine** pipeline:

1.  **Scraper**: Fetches raw news from target media sites (`scrapers/history_scraper.py`).
2.  **Tag Generator**: Extracts keywords/entities from articles (`core/tag_generator.py`).
3.  **Vector Store**: Embeds and indexes articles into **ChromaDB** (`core/vector_store.py`).
4.  **Recommendation Engine**: Generates the final personalized feed (`core/recommendation.py`).
5.  **Persona Agent**: Evaluates feedback and updates the persona definition (`core/agent_persona.py`).


## Getting Started

### Prerequisites
- Python 3.9+
- Chrome Browser (for Playwright)

### Installation
```bash
git clone <repo_url>
cd news_room_v2
pip install -r requirements.txt
playwright install
```

### Running the System
**1. Start the Web UI:**
```bash
bash run_web.sh
```
Access the dashboard at `http://localhost:8000`.

**2. Manual Scraping:**
```bash
python3 scrapers/history_scraper.py --start_date 20260211 --end_date 20260211
```

**3. Generate Recommendations :**
```bash
python3 core/recommendation.py --persona 20s
```



## Persona Configuration

You can customize the recommendation logic by editing the Markdown files in `personas/`. Define your **Interest Groups**, **Sentence Preferences**, and **Negative Constraints** to tailor the news feed to your exact needs.

## Persona Refinement (Feedback Loop)

The system includes a feedback loop to automatically refine the persona based on article evaluations.

**1. Evaluate Recommendations:**
Simulate user feedback (or use real feedback data) to score articles.
```bash
python3 core/agent_persona.py --persona 20s --action evaluate --input data/recommands.json --output data/feedback.json
```

**2. Update Persona:**
Use the feedback to refine the persona definition (e.g., adding new positive/negative keywords).
```bash
python3 core/agent_persona.py --persona 20s --action update --input data/feedback.json
```
