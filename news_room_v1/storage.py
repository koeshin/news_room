import json
import os
from datetime import datetime

SCRAPS_FILE = "scraps.json"
SETTINGS_FILE = "settings.json"
FOLDERS_FILE = "folders.json"
CACHE_DIR = "scraped_data"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


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
    """폴더 목록 로드"""
    return load_json(FOLDERS_FILE, {"folders": ["기본"], "default": "기본"})

def save_folders(folders_data):
    """폴더 목록 저장"""
    save_json(FOLDERS_FILE, folders_data)

def add_folder(folder_name):
    """새 폴더 추가"""
    folders_data = load_folders()
    if folder_name not in folders_data["folders"]:
        folders_data["folders"].append(folder_name)
        save_folders(folders_data)
        return True
    return False

def get_folder_list():
    """폴더 목록 반환"""
    return load_folders().get("folders", ["기본"])

def toggle_scrap(date_str, media_name, article, folder="기본", tags=None):
    """
    스크랩을 추가하거나 이미 존재하면 제거합니다. (Toggle)
    Returns: True if added, False if removed
    """
    if tags is None:
        tags = []
        
    scraps = load_scraps()
    if date_str not in scraps:
        scraps[date_str] = []
    
    # 중복 확인 (URL 기준)
    existing_index = -1
    for idx, s in enumerate(scraps[date_str]):
        if s['url'] == article['url']:
            existing_index = idx
            break
    
    if existing_index != -1:
        # 이미 존재하면 삭제 (Unscrap)
        scraps[date_str].pop(existing_index)
        if not scraps[date_str]:
            del scraps[date_str]
        save_json(SCRAPS_FILE, scraps)
        return False
    else:
        # 없으면 추가 (Scrap)
        scrap_item = article.copy()
        scrap_item['media'] = media_name
        scrap_item['scrapped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scrap_item['read'] = False
        scrap_item['folder'] = folder  # 폴더 추가
        scrap_item['tags'] = tags  # 태그 추가
        
        scraps[date_str].append(scrap_item)
        save_json(SCRAPS_FILE, scraps)
        return True

def update_scrap_folder(date_str, url, folder):
    """스크랩의 폴더 변경"""
    scraps = load_scraps()
    if date_str in scraps:
        for s in scraps[date_str]:
            if s['url'] == url:
                s['folder'] = folder
                save_json(SCRAPS_FILE, scraps)
                return True
    return False

def update_scrap_tags(date_str, url, tags):
    """스크랩의 태그 변경"""
    scraps = load_scraps()
    if date_str in scraps:
        for s in scraps[date_str]:
            if s['url'] == url:
                s['tags'] = tags
                save_json(SCRAPS_FILE, scraps)
                return True
    return False

def get_scraps_by_folder(folder_name):
    """특정 폴더의 스크랩만 반환"""
    scraps = load_scraps()
    result = {}
    for date_str, items in scraps.items():
        filtered = [s for s in items if s.get('folder', '기본') == folder_name]
        if filtered:
            result[date_str] = filtered
    return result

def export_scraps_to_markdown(scraps_data, filename="export.md"):
    """스크랩을 마크다운 파일로 내보내기"""
    lines = ["# 스크랩 내보내기\n"]
    lines.append(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    for date_str in sorted(scraps_data.keys(), reverse=True):
        lines.append(f"## 📅 {date_str}\n\n")
        for item in scraps_data[date_str]:
            folder = item.get('folder', '기본')
            tags = item.get('tags', [])
            tag_str = " ".join([f"#{t}" for t in tags]) if tags else ""
            
            lines.append(f"### [{item.get('media', '')}] {item['title']}\n")
            if item.get('subtitle'):
                lines.append(f"> {item['subtitle']}\n")
            lines.append(f"- 📁 폴더: {folder}\n")
            if tag_str:
                lines.append(f"- 🏷️ 태그: {tag_str}\n")
            lines.append(f"- 🔗 [기사 링크]({item['url']})\n")
            lines.append(f"- ⏰ 스크랩: {item.get('scrapped_at', '')}\n\n")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    return filename

def remove_scrap(date_str, url):
    """특정 스크랩 삭제 (명시적)"""
    scraps = load_scraps()
    if date_str in scraps:
        original_len = len(scraps[date_str])
        scraps[date_str] = [s for s in scraps[date_str] if s['url'] != url]
        
        if len(scraps[date_str]) != original_len:
            if not scraps[date_str]:
                del scraps[date_str]
            save_json(SCRAPS_FILE, scraps)
            return True
    return False

def mark_as_read(date_str, url, status=True):
    """읽음 상태 업데이트"""
    scraps = load_scraps()
    if date_str in scraps:
        for s in scraps[date_str]:
            if s['url'] == url:
                s['read'] = status
                save_json(SCRAPS_FILE, scraps)
                return True
    return False

def get_weekly_scraps():
    """
    이번 주 월요일 ~ 현재까지의 스크랩 데이터를 모두 가져옵니다.
    1. 오늘이 일요일(6)이면: 지난 월(0) ~ 토(5) 데이터 수집
    2. 그 외 요일이면: 이번 주 월(0) ~ 오늘까지 데이터 수집
    """
    scraps = load_scraps()
    today = datetime.now()
    weekday = today.weekday() # 월=0, 일=6
    
    target_dates = []
    
    # 리포트 기준일 설정
    # 만약 일요일(6)이라면 '지난주 월~토'를 대상으로 함 (요청사항 반영)
    if weekday == 6:
        days_from_mon = 6 # 일(6) - 월(0) = 6일 전부터
        start_date = today - timedelta(days=6)
        end_date = today - timedelta(days=1) # 어제(토)까지
    else:
        # 월~토요일인 경우: 이번주 월요일 ~ 오늘
        start_date = today - timedelta(days=weekday)
        end_date = today

    # 날짜 리스트 생성
    curr = start_date
    while curr <= end_date:
        d_str = curr.strftime("%Y-%m-%d")
        if d_str in scraps:
           for item in scraps[d_str]:
               # 리포트용 포맷으로 변환 없이 원본 반환
               # 필요한 경우 날짜 정보도 포함하여 리스트로 만듦
               item_with_date = item.copy()
               item_with_date['date'] = d_str
               target_dates.append(item_with_date)
        curr += timedelta(days=1)
        
    return target_dates

def get_cache_path(date, oid):
    # 폴더 구조: scraped_data/{date}/{oid}.json
    date_dir = os.path.join(CACHE_DIR, date)
    if not os.path.exists(date_dir):
        os.makedirs(date_dir)
    return os.path.join(date_dir, f"{oid}.json")

def save_news_cache(date, oid, data):
    """스크랩 결과(지면 데이터)를 파일로 캐싱"""
    path = get_cache_path(date, oid)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_news_cache(date, oid):
    """캐시된 데이터가 있으면 반환, 없으면 None"""
    path = get_cache_path(date, oid)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

def clear_news_cache(date, oid):
    """특정 캐시 삭제 (강제 새로고침용)"""
    path = get_cache_path(date, oid)
    if os.path.exists(path):
        os.remove(path)

