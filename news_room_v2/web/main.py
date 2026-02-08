import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to sys.path to allow importing modules from parent directory
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from fastapi import FastAPI, Request, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import storage
import json

app = FastAPI(title="News Room v2")

# Mount Static Files
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# --- Models ---
class ScrapRequest(BaseModel):
    date: str
    media: str
    url: str
    title: str
    subtitle: str = ""
    # Add other fields as needed for toggle_scrap

# --- Helpers ---
def get_today_str():
    return datetime.now().strftime("%Y%m%d")

def format_date_display(date_str):
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
    except:
        return date_str

# --- Routes ---

@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/newsroom")

@app.get("/newsroom", response_class=HTMLResponse)
async def news_room(request: Request, 
                   date: str = Query(default=get_today_str()), 
                   media_oid: str = Query(default=None)):
    
    # Sanitize date (YYYY-MM-DD -> YYYYMMDD)
    date_param = date.replace("-", "")
    
    settings = storage.load_settings()
    media_list = settings.get("media_list", [])
    
    # Default media if not provided
    if not media_oid and media_list:
        media_oid = media_list[0]['oid']
        
    selected_media = next((m for m in media_list if m['oid'] == media_oid), None)
    
    news_data = []
    news_data = []
    if selected_media:
        print(f"--- DEBUG NEWSROOM ---")
        print(f"CWD: {os.getcwd()}")
        print(f"Storage DATA_DIR: {storage.DATA_DIR}")
        print(f"Loading data for: {date_param}, {media_oid}")
        news_data = storage.load_news_data(date_param, media_oid)
        print(f"Loaded {len(news_data)} articles")
        if news_data:
            print(f"Sample article: {news_data[0]}")
        if not news_data:
             # Check if file exists manually
             yyyymm = date_param[:6]
             expected = os.path.join(storage.DATA_DIR, yyyymm, f"{media_oid}_{date_param}.json")
             print(f"Expected file: {expected}")
             print(f"Exists? {os.path.exists(expected)}")

    # Group by Page
    grouped_news = {}
    chunks = []
    current_chunk_idx = int(request.query_params.get('chunk', 0))
    
    if news_data:
        from collections import defaultdict
        import re
        import math

        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower()
                    for text in re.split('([0-9]+)', str(s))]
        
        def extract_section(s):
            # Extract section letter (A, B, E, S, etc.)
            match = re.match(r'^([A-Z]+)', str(s))
            return match.group(1) if match else 'Z'
        
        def extract_page_num(s):
            # Extract first number found
            match = re.search(r'\d+', str(s))
            return int(match.group()) if match else 999

        groups = defaultdict(list)
        for article in news_data:
            page = article.get('page', 'Others')
            groups[page].append(article)
            
        # Sort pages
        sorted_pages = sorted(groups.keys(), key=natural_sort_key)
        
        # Group by section AND page range
        # Key: (section, range_idx) -> [page_names]
        section_range_map = defaultdict(list)
        
        for p in sorted_pages:
            section = extract_section(p)
            num = extract_page_num(p)
            if num == 999:
                key = ('Z', 99)  # Others
            else:
                range_idx = (num - 1) // 10
                key = (section, range_idx)
            section_range_map[key].append(p)
        
        # Sort by section first, then by range
        sorted_keys = sorted(section_range_map.keys(), key=lambda x: (x[0], x[1]))
        
        # Create chunk metadata with section-based labels
        for chunk_idx, key in enumerate(sorted_keys):
            section, range_idx = key
            if range_idx == 99:
                label = "기타"
            else:
                start = range_idx * 10 + 1
                end = (range_idx + 1) * 10
                label = f"{section}{start}-{end}면"
            chunks.append({'index': chunk_idx, 'label': label, 'key': key})
        
        # Build chunk_map for lookup
        chunk_map = {i: section_range_map[chunks[i]['key']] for i in range(len(chunks))}
            
        # Filter grouped_news for current chunk
        if current_chunk_idx >= len(chunks) and chunks:
            print(f"[DEBUG] Chunk {current_chunk_idx} not found. Fallback to 0")
            current_chunk_idx = 0
            
        target_pages = chunk_map.get(current_chunk_idx, [])
        grouped_news = {p: groups[p] for p in target_pages}
        
        print(f"[DEBUG] Grouped News Keys: {list(grouped_news.keys())}")
        print(f"[DEBUG] Chunks: {chunks}")
        print(f"[DEBUG] Current Chunk: {current_chunk_idx}")

    # Get Scrapped URLs for UI state
    scraps = storage.load_scraps()
    scrapped_urls = set()
    for d in scraps:
        for s in scraps[d]:
            scrapped_urls.add(s['url'])

    return templates.TemplateResponse("news_room.html", {
        "request": request,
        "media_list": media_list,
        "selected_media": selected_media,
        "selected_date": date_param, 
        "grouped_news": grouped_news,
        "chunks": chunks,
        "current_chunk": current_chunk_idx,
        "news_data": news_data, 
        "scrapped_urls": list(scrapped_urls)
    })

@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations(request: Request):
    # Load Recommendations
    rec_file = os.path.join(PROJECT_ROOT, "data", "loop_output.json")
    all_recs = []
    if os.path.exists(rec_file):
        with open(rec_file, 'r') as f:
            all_recs = json.load(f)
            
    # Filter for 20s
    recs_20s = [r for r in all_recs if r.get("persona") == "20s"]
    
    # Load keywords from settings
    settings = storage.load_settings()
    keywords = settings.get("keywords", [])
    
    return templates.TemplateResponse("recommendations.html", {
        "request": request,
        "recommendations": recs_20s,
        "keywords": keywords
    })

@app.get("/scrapbook", response_class=HTMLResponse)
async def scrapbook(request: Request):
    scraps = storage.load_scraps()
    # Flatten or pass as is? Template can handle dict
    return templates.TemplateResponse("scrapbook.html", {
        "request": request,
        "scraps": scraps
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    settings = storage.load_settings()
    media_list = settings.get("media_list", [])
    
    # Load naver_media_codes for selector
    codes_file = os.path.join(storage.SCRIPT_DIR, "naver_media_codes.json")
    media_codes = {}
    if os.path.exists(codes_file):
        with open(codes_file, 'r', encoding='utf-8') as f:
            media_codes = json.load(f)
    
    # Get subscribed OIDs for easy lookup
    subscribed_oids = [m.get('oid') for m in media_list]
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "media_list": media_list,
        "media_codes": media_codes,
        "subscribed_oids": subscribed_oids
    })

@app.post("/api/settings/update_media")
async def update_media_settings(item: dict):
    # item: { media_list: [ {oid, name, enabled}, ... ] }
    new_list = item.get("media_list")
    if new_list is None:
         return JSONResponse({"status": "error", "message": "No data"}, status_code=400)
    
    # Load current, update list, save
    current_settings = storage.load_settings()
    current_settings['media_list'] = new_list
    
    storage.save_settings(current_settings) # Need to ensure storage has save_settings
    return {"status": "success"}

@app.post("/api/settings/add_media")
async def add_media_settings(item: dict):
    # item: { name: str }
    name = item.get("name")
    
    if not name:
        return JSONResponse({"status": "error", "message": "Missing name"}, status_code=400)
    
    # Load Media Codes to find OID
    codes_path = os.path.join(PROJECT_ROOT, "naver_media_codes.json")
    # If not in v2, check v1? script says v2/naver_media_codes.json is found by find tool.
    # storage.py says: NAVER_CODES_FILE = ... "news_room_v1/naver_media_codes.json"
    # Let's use storage.py's path if available, or just load from known location.
    # storage.py isn't exposing it directly, let's load it here.
    
    # Try loading from v2 first, then v1
    oid = None
    
    target_path = os.path.join(PROJECT_ROOT, "naver_media_codes.json") # v2 root
    if not os.path.exists(target_path):
         target_path = os.path.join(PROJECT_ROOT, "..", "news_room_v1", "naver_media_codes.json")

    if os.path.exists(target_path):
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Check flat_list
            for media in data.get("flat_list", []):
                if media['name'] == name:
                    oid = media['oid']
                    break
    
    if not oid:
         return JSONResponse({"status": "error", "message": "Media not found"}, status_code=404)

    current_settings = storage.load_settings()
    media_list = current_settings.get("media_list", [])
    
    # Check duplicate OID
    if any(m['oid'] == oid for m in media_list):
        return JSONResponse({"status": "error", "message": "Duplicate OID"}, status_code=400)
        
    media_list.append({"name": name, "oid": oid})
    current_settings['media_list'] = media_list
    
    storage.save_settings(current_settings)
    return {"status": "success", "oid": oid}

@app.post("/api/log")
async def log_event(item: dict):
    # item: { event: str, target_id: str, type: str }
    log_entry = {
         "timestamp": datetime.now().isoformat(),
         "event": item.get("event"),
         "target_id": item.get("target_id"),
         "type": item.get("type"),
         "user": "default"
    }
    # Append to log file
    log_file = os.path.join(PROJECT_ROOT, "data", "user_behavior_logs.jsonl")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return {"status": "logged"}

@app.post("/api/scrap")
async def toggle_scrap(item: dict):
    # item comes as a dict from JSON body
    # Expected: { date: "YYYY-MM-DD", media_name: "...", article: {...} }
    
    # We need to map the frontend request to storage.toggle_scrap format
    # storage.toggle_scrap(date_str, media_name, article_dict)
    
    date_display = item.get('date') # Should be YYYY-MM-DD
    media_name = item.get('media_name')
    article = item.get('article')
    
    if not date_display or not article:
        return JSONResponse({"status": "error", "message": "Invalid data"}, status_code=400)
        
    result = storage.toggle_scrap(date_display, media_name, article)
    return JSONResponse({"status": "success", "action": result})

if __name__ == "__main__":
    uvicorn.run("web.main:app", host="0.0.0.0", port=8000, reload=True)
