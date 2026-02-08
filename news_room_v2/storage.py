import json
import os
from datetime import datetime, timedelta

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # news_room folder
DATA_DIR = os.path.join(PROJECT_ROOT, "scraped_data_history")

# Local storage files
SCRAPS_FILE = os.path.join(SCRIPT_DIR, "scraps.json")
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "settings.json")
FOLDERS_FILE = os.path.join(SCRIPT_DIR, "folders.json")
NAVER_CODES_FILE = os.path.join(SCRIPT_DIR, "news_room_v1", "naver_media_codes.json") # Reusing v1 codes

# Ensure v2 directory exists for these files
if not os.path.exists(SCRIPT_DIR):
    os.makedirs(SCRIPT_DIR)

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

def load_folders():
    return load_json(FOLDERS_FILE, {"folders": ["기본"], "default": "기본"})

def save_folders(folders_data):
    save_json(FOLDERS_FILE, folders_data)

def add_folder(folder_name):
    folders_data = load_folders()
    if folder_name not in folders_data["folders"]:
        folders_data["folders"].append(folder_name)
        save_folders(folders_data)
        return True
    return False

def get_folder_list():
    return load_folders().get("folders", ["기본"])

def toggle_scrap(date_str, media_name, article, folder="기본", tags=None):
    if tags is None: tags = []
    scraps = load_scraps()
    if date_str not in scraps: scraps[date_str] = []
    
    # Check for duplicate
    existing_index = -1
    for idx, s in enumerate(scraps[date_str]):
        if s['url'] == article['url']:
            existing_index = idx
            break
            
    if existing_index != -1:
        # Unscrap
        scraps[date_str].pop(existing_index)
        if not scraps[date_str]: del scraps[date_str]
        save_json(SCRAPS_FILE, scraps)
        return False
    else:
        # Scrap
        scrap_item = article.copy()
        scrap_item['media'] = media_name
        scrap_item['scrapped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scrap_item['read'] = False
        scrap_item['folder'] = folder
        scrap_item['tags'] = tags
        scraps[date_str].append(scrap_item)
        save_json(SCRAPS_FILE, scraps)
        return True

def remove_scrap(date_str, url):
    scraps = load_scraps()
    if date_str in scraps:
        original_len = len(scraps[date_str])
        scraps[date_str] = [s for s in scraps[date_str] if s['url'] != url]
        if len(scraps[date_str]) != original_len:
            if not scraps[date_str]: del scraps[date_str]
            save_json(SCRAPS_FILE, scraps)
            return True
    return False

def mark_as_read(date_str, url, status=True):
    scraps = load_scraps()
    if date_str in scraps:
        for s in scraps[date_str]:
            if s['url'] == url:
                s['read'] = status
                save_json(SCRAPS_FILE, scraps)
                return True
    return False

def get_scraps_by_folder(folder_name):
    scraps = load_scraps()
    result = {}
    for date_str, items in scraps.items():
        filtered = [s for s in items if s.get('folder', '기본') == folder_name]
        if filtered: result[date_str] = filtered
    return result

def export_scraps_to_markdown(scraps_data, filename="export.md"):
    lines = ["# 스크랩 내보내기\n", f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"]
    for date_str in sorted(scraps_data.keys(), reverse=True):
        lines.append(f"## 📅 {date_str}\n\n")
        for item in scraps_data[date_str]:
            folder = item.get('folder', '기본')
            lines.append(f"### [{item.get('media', '')}] {item['title']}\n")
            if item.get('subtitle'): lines.append(f"> {item['subtitle']}\n")
            lines.append(f"- 📁 폴더: {folder}\n")
            lines.append(f"- 🔗 [기사 링크]({item['url']})\n\n")
            
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return filename

# --- V2 Specific Data Loading ---
def load_news_data(date_str, oid):
    """
    Load scraped data from news_room_v2 history structure.
    Path: scraped_data_history/YYYYMM/{OID}_{YYYYMMDD}.json  <-- WRONG PATTERN CHECKED
    Wait, let me check the file listing again.
    List output: 009_20250602.json -> {OID}_{YYYYMMDD}.json
    """
    yyyymm = date_str[:6]
    month_dir = os.path.join(DATA_DIR, yyyymm)
    filename = f"{oid}_{date_str}.json"
    filepath = os.path.join(month_dir, filename)
    
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []
