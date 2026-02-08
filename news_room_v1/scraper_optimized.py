"""
최적화된 Playwright 스크래퍼
- 브라우저 재사용
- 리소스 완전 차단
- 병렬 처리 강화
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import storage

# 동시 실행 제한 (증가)
SEM_LIMIT = 15

# 차단할 리소스 타입 (모든 불필요 리소스)
BLOCKED_RESOURCES = [
    "image", "media", "font", "stylesheet", "script",
    "fetch", "xhr", "websocket", "manifest", "other"
]

async def fetch_article_subtitle_fast(page, url, sem):
    """부제목을 빠르게 가져옵니다. (페이지 재사용)"""
    async with sem:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=3000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
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
                    
                if not subtitle:
                    summary_div = soup.select_one('div.media_end_summary')
                    if summary_div:
                        subtitle = summary_div.get_text(strip=True)
                    
            # 3. Guide
            if not subtitle:
                guide_elem = soup.select_one('div.media_end_head_guide')
                if guide_elem:
                    subtitle = guide_elem.get_text(strip=True)
            
            return subtitle
        except Exception:
            return ""

async def get_newspaper_data_optimized(browser, oid, date, force_refresh=False):
    """최적화된 스크래핑 (브라우저 재사용)"""
    
    # 1. 캐시 확인
    if not force_refresh:
        cached_data = storage.load_news_cache(date, oid)
        if cached_data:
            print(f"[{oid}] Cache Hit!")
            return cached_data

    print(f"[{oid}] Optimized Scraping started...")
    url = f"https://media.naver.com/press/{oid}/newspaper?date={date}"
    
    # 컨텍스트 생성 (리소스 차단)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    
    page = await context.new_page()
    
    # 리소스 차단 (이미지, 폰트, 스타일시트 등)
    await page.route("**/*", lambda route: 
        route.abort() if route.request.resource_type in BLOCKED_RESOURCES 
        else route.continue_()
    )
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=10000)
        
        # 지면 데이터 대기 (짧은 타임아웃)
        try:
            await page.wait_for_selector('div.newspaper_inner', timeout=5000)
        except:
            await context.close()
            return []
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        page_sections = soup.select('div.newspaper_inner')
        
        newspaper_data = []
        subtitle_tasks = []
        article_infos = []
        
        sem = asyncio.Semaphore(SEM_LIMIT)
        
        # 부제목용 페이지들 미리 생성
        subtitle_pages = []
        for _ in range(min(SEM_LIMIT, 10)):
            p = await context.new_page()
            await p.route("**/*", lambda route: 
                route.abort() if route.request.resource_type in BLOCKED_RESOURCES 
                else route.continue_()
            )
            subtitle_pages.append(p)
        
        page_idx = 0
        
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
                
                # 라운드 로빈으로 페이지 할당
                assigned_page = subtitle_pages[page_idx % len(subtitle_pages)]
                page_idx += 1
                subtitle_tasks.append(fetch_article_subtitle_fast(assigned_page, article_url, sem))
            
            if articles:
                newspaper_data.append({
                    "page": page_name,
                    "articles": articles
                })
        
        # 부제목 병렬 처리
        if subtitle_tasks:
            subtitles = await asyncio.gather(*subtitle_tasks)
            for info, subtitle in zip(article_infos, subtitles):
                info["subtitle"] = subtitle
        
        # 정리
        for p in subtitle_pages:
            await p.close()
        await context.close()
        
        # 캐시 저장
        if newspaper_data:
            storage.save_news_cache(date, oid, newspaper_data)
        
        return newspaper_data
        
    except Exception as e:
        print(f"[{oid}] Error: {e}")
        await context.close()
        return []

async def scrape_multiple_media(media_list, date, force_refresh=False):
    """여러 언론사를 한 번에 스크래핑 (브라우저 1개 재사용)"""
    async with async_playwright() as p:
        # 브라우저 한 번만 실행
        browser = await p.chromium.launch(headless=True)
        
        results = {}
        for media in media_list:
            data = await get_newspaper_data_optimized(browser, media['oid'], date, force_refresh)
            results[media['oid']] = data
        
        await browser.close()
        return results

if __name__ == "__main__":
    import time
    from datetime import datetime, timedelta
    
    # 테스트 날짜 (캐시가 있는 날짜 사용)
    test_date = "20260130"
    
    TEST_MEDIA = [
        {"name": "조선일보", "oid": "023"},
        {"name": "중앙일보", "oid": "025"},
        {"name": "동아일보", "oid": "020"},
        {"name": "한겨레", "oid": "028"},
        {"name": "경향신문", "oid": "032"},
    ]
    
    print("="*60)
    print("🚀 최적화된 Playwright 스크래퍼 테스트")
    print(f"📅 날짜: {test_date}")
    print("="*60)
    
    start = time.time()
    results = asyncio.run(scrape_multiple_media(TEST_MEDIA, test_date, force_refresh=True))
    elapsed = time.time() - start
    
    print("\n" + "="*60)
    print("📊 결과")
    print("="*60)
    
    total_articles = 0
    for oid, data in results.items():
        name = next(m['name'] for m in TEST_MEDIA if m['oid'] == oid)
        article_count = sum(len(page['articles']) for page in data) if data else 0
        total_articles += article_count
        print(f"  {name}: {article_count}개 기사")
    
    print(f"\n⏱️ 총 소요 시간: {elapsed:.2f}초")
    print(f"📰 총 기사 수: {total_articles}개")
    print(f"⚡ 기사당 평균: {elapsed/total_articles*1000:.1f}ms" if total_articles > 0 else "")
