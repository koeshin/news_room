# Developer Guide (News Room V2)

This guide provides instructions on how to set up, run, and extend the News Room project.

## 1. Setup

### Prerequisites
- Python 3.9+
- Chrome/Chromium Browser (for Playwright)

### Installation

1.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd news_room_v2
    ```

2.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv_newsroom
    source venv_newsroom/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    playwright install
    ```

4.  **Set Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    GOOGLE_API_KEY=your_gemini_api_key_here
    OPENAI_API_KEY=your_openai_api_key_here (Optional)
    ```

## 2. Running the Application

### Start the Web Server
Execute the provided bash script:
```bash
bash run_web.sh
```
- Access the web UI at `http://localhost:8000`.

### Manual Scraper Execution
To run the scraper independently (without the web UI):
```bash
python3 scrapers/history_scraper.py --start_date YYYYMMDD --end_date YYYYMMDD
```
- Check `scraped_data_history/` for the output JSON files.

### Update Vector Index
To manually index new articles into ChromaDB:
```bash
python3 core/vector_store.py --start_date YYYYMMDD --end_date YYYYMMDD
```

## 3. Extending Functionality

### Adding a New Persona
1.  Create a new Markdown file in `personas/` (e.g., `persona_30s.md`).
2.  Follow this template:
    ```markdown
    # Persona Name
    ## Characteristics
    - Description of user...

    ## Interest Groups
    - GroupName1: keyword1, keyword2
    - GroupName2: keyword3, keyword4

    ## Sentence Preferences
    - I prefer detailed analysis on...
    - I like articles about...

    ## Negative Keywords
    - keyword_to_avoid1, keyword_to_avoid2

    ## Negative Sentences
    - I dislike articles about...
    ```
3.  Restart the application or rerun the recommendation script.

### Adding a New Scraper (Media Source)
1.  Modify `scrapers/history_scraper.py`.
2.  Add a new configuration dictionary to the `MEDIA_CONFIGS` list (or equivalent structure).
3.  Ensure the scraper logic handles the HTML structure of the new site.

## 4. Key Configurations
- **Batch Size for LLM**: Controlled in `core/recommendation.py` (line ~318: `candidates[:20]`). Reduce if hitting `429` errors.
- **Negative Penalty Score**: Controlled in `core/recommendation.py` (line ~280: `penalty += 0.3`). Adjust sensitivity as needed.
