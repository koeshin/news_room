import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import storage # 캐싱 모듈 임포트

# 동시 실행 제한을 위한 세마포어 (한 번에 5개의 탭만 열기)
SEM_LIMIT = 5

async def fetch_article_subtitle(context, url, sem):
    """기사 상세 페이지에서 부제목을 가져옵니다. (Semaphore 적용)"""
    async with sem:
        try:
            page = await context.new_page()
            # 리소스 최적화
            await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] else route.continue_())
            
            # 타임아웃 3초로 복구 (세마포어로 부하가 줄었으므로)
            await page.goto(url, wait_until="domcontentloaded", timeout=3000)
            
            try:
               await page.wait_for_selector('div.media_end_head_subheadline, strong.media_end_summary', timeout=1500)
            except:
               pass
    
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # ... (이하 동일) ...
            
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
    
            # 라우팅 해제 및 페이지 닫기 (오류 방지)
            await page.unroute_all(behavior='ignoreErrors')
            await page.close()
            return subtitle
        except Exception:
            return ""

async def get_newspaper_data(oid, date, force_refresh=False):
    """특정 언론사와 날짜의 신문 데이터를 가져옵니다."""
    
    # 1. 캐시 확인
    if not force_refresh:
        cached_data = storage.load_news_cache(date, oid)
        if cached_data:
            print(f"[{oid}] Cache Hit! Skipping scrape.")
            return cached_data

    print(f"[{oid}] Scraping started...")
    url = f"https://media.naver.com/press/{oid}/newspaper?date={date}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 유저 에이전트 및 추가 헤더 설정은 이미 context에서 함
        await page.goto(url, wait_until="domcontentloaded")
        
        # 지면 데이터가 로드될 때까지 대기
        try:
            await page.wait_for_selector('div.newspaper_inner', timeout=15000)
        except Exception:
            # 타임아웃 발생 시 현재 스크린샷 저장 (디버깅용)
            await page.screenshot(path="debug_scraper_fail.png")
            await browser.close()
            return []
        
        # 페이지가 완전히 로딩되도록 잠시 대기
        await asyncio.sleep(1)
        
        # 지면 데이터 파싱
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # 면(Page) 섹션 찾기
        page_sections = soup.select('div.newspaper_inner')
        
        newspaper_data = []
        
        # 모든 기사 상세 페이지 방문을 위한 태스크 리스트
        subtitle_tasks = []
        article_infos = []

        # 동시 실행 제어용 세마포어 생성
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
                
                # 비동기로 부제목 가져오기 예약
                article_info = {
                    "page": page_name,
                    "title": title,
                    "url": article_url,
                    "subtitle": ""
                }
                articles.append(article_info)
                article_infos.append(article_info)
                # 세마포어 전달
                subtitle_tasks.append(fetch_article_subtitle(context, article_url, sem))
            
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
            
        await browser.close()
        
        # 2. 캐시 저장
        if newspaper_data:
            storage.save_news_cache(date, oid, newspaper_data)
            
        return newspaper_data

if __name__ == "__main__":
    # 테스트 코드
    async def test():
        data = await get_newspaper_data("023", "20260130") # 조선일보
        for page in data:
            print(f"[{page['page']}]")
            for art in page['articles']:
                print(f"  - {art['title']}")
                print(f"    Sub: {art['subtitle']}")
                print(f"    URL: {art['url']}")
    
    # asyncio.run(test())
