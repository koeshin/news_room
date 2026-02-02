"""
httpx 기반 고속 스크래퍼
Playwright 대신 httpx를 사용하여 정적 HTML을 직접 가져옵니다.
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
import storage

# 동시 요청 제한
SEM_LIMIT = 20

# 공통 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

async def fetch_article_subtitle(client, url, sem):
    """기사 상세 페이지에서 부제목을 가져옵니다."""
    async with sem:
        try:
            response = await client.get(url, headers=HEADERS, timeout=5.0)
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            subtitle = ""
            # 1. Standard Subtitle
            sub_elem = soup.select_one('div.media_end_head_subheadline')
            if sub_elem:
                subtitle = sub_elem.get_text(strip=True)
                
            # 2. Summary
            if not subtitle:
                summary_elem = soup.select_one('strong.media_end_summary')
                if summary_elem:
                    subtitle = summary_elem.get_text(strip=True)
                    
                # Div Fallback
                if not subtitle:
                    summary_div = soup.select_one('div.media_end_summary')
                    if summary_div:
                        subtitle = summary_div.get_text(strip=True)
                    
            # 3. Old style / Guide
            if not subtitle:
                guide_elem = soup.select_one('div.media_end_head_guide')
                if guide_elem:
                    subtitle = guide_elem.get_text(strip=True)
            
            return subtitle
        except Exception:
            return ""

async def get_newspaper_data(oid, date, force_refresh=False):
    """특정 언론사와 날짜의 신문 데이터를 가져옵니다. (httpx 버전)"""
    
    # 1. 캐시 확인
    if not force_refresh:
        cached_data = storage.load_news_cache(date, oid)
        if cached_data:
            print(f"[{oid}] Cache Hit! Skipping scrape.")
            return cached_data

    print(f"[{oid}] httpx Scraping started...")
    url = f"https://media.naver.com/press/{oid}/newspaper?date={date}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=HEADERS, timeout=10.0)
            if response.status_code != 200:
                print(f"[{oid}] Failed to fetch main page: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 면(Page) 섹션 찾기
            page_sections = soup.select('div.newspaper_inner')
            
            if not page_sections:
                print(f"[{oid}] No newspaper sections found")
                return []
            
            newspaper_data = []
            subtitle_tasks = []
            article_infos = []
            
            # 동시 실행 제어용 세마포어
            sem = asyncio.Semaphore(SEM_LIMIT)
            
            for section in page_sections:
                page_name_elem = section.select_one('span.page_notation')
                if not page_name_elem:
                    continue
                
                page_name = page_name_elem.get_text(strip=True)
                
                articles = []
                article_elems = section.select('ul.newspaper_article_lst > li > a')
                
                for a in article_elems:
                    title_elem = a.select_one('strong')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    article_url = a['href']
                    
                    article_info = {
                        "page": page_name,
                        "title": title,
                        "url": article_url,
                        "subtitle": ""
                    }
                    articles.append(article_info)
                    article_infos.append(article_info)
                    subtitle_tasks.append(fetch_article_subtitle(client, article_url, sem))
                
                if articles:
                    newspaper_data.append({
                        "page": page_name,
                        "articles": articles
                    })
            
            # 부제목들을 한꺼번에 가져옴 (병렬 처리)
            subtitles = await asyncio.gather(*subtitle_tasks)
            
            # 가져온 부제목을 결과 데이터에 삽입
            for info, subtitle in zip(article_infos, subtitles):
                info["subtitle"] = subtitle
            
            # 2. 캐시 저장
            if newspaper_data:
                storage.save_news_cache(date, oid, newspaper_data)
            
            return newspaper_data
            
        except Exception as e:
            print(f"[{oid}] Error: {e}")
            return []

if __name__ == "__main__":
    async def test():
        data = await get_newspaper_data("023", "20260201", force_refresh=True)
        for page in data:
            print(f"[{page['page']}]")
            for art in page['articles'][:3]:
                print(f"  - {art['title']}")
                print(f"    Sub: {art['subtitle'][:50]}..." if art['subtitle'] else "    Sub: (없음)")
    
    asyncio.run(test())
