import json
import os
from datetime import datetime

SCRAPS_FILE = "scraps.json"
SETTINGS_FILE = "settings.json"
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

def toggle_scrap(date_str, media_name, article):
    """
    스크랩을 추가하거나 이미 존재하면 제거합니다. (Toggle)
    Returns: True if added, False if removed
    """
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
        scrap_item['read'] = False  # 읽음 상태 기본값
        
        scraps[date_str].append(scrap_item)
        save_json(SCRAPS_FILE, scraps)
        return True

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

