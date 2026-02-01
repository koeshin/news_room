import json
import os
from datetime import datetime

SCRAPS_FILE = "scraps.json"
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "media_list": [
        {"name": "조선일보", "oid": "023"},
        {"name": "중앙일보", "oid": "025"},
        {"name": "동아일보", "oid": "020"}
    ]
}

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_settings():
    return load_json(SETTINGS_FILE, DEFAULT_SETTINGS)

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

def load_scraps():
    return load_json(SCRAPS_FILE, {})

def add_scrap(date_str, media_name, article):
    """
    article: {"title": "...", "subtitle": "...", "url": "..."}
    """
    scraps = load_scraps()
    if date_str not in scraps:
        scraps[date_str] = []
    
    # 중복 확인
    if any(s['url'] == article['url'] for s in scraps[date_str]):
        return False
    
    scrap_item = article.copy()
    scrap_item['media'] = media_name
    scrap_item['scrapped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    scraps[date_str].append(scrap_item)
    save_json(SCRAPS_FILE, scraps)
    return True

def remove_scrap(date_str, url):
    scraps = load_scraps()
    if date_str in scraps:
        scraps[date_str] = [s for s in scraps[date_str] if s['url'] != url]
        if not scraps[date_str]:
            del scraps[date_str]
        save_json(SCRAPS_FILE, scraps)
        return True
    return False
