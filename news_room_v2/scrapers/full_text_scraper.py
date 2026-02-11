"""
Full Text Scraper for Keyword Extraction Comparison
Usage: python scrapers/full_text_scraper.py --date 20260211
"""

import asyncio
import argparse
import json
import os
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# --- Configuration ---
MEDIA_LIST = [
    {"name": "조선일보", "code": "023"},
    {"name": "중앙일보", "code": "025"},
    {"name": "동아일보", "code": "020"},
    {"name": "전자신문", "code": "030"}, 
    {"name": "매일경제", "code": "009"}, 
    {"name": "한국경제", "code": "015"}, 
]

SEM_LIMIT = 5
BLOCKED_RESOURCES = [
    "image", "media", "font", "stylesheet", "script",
    "fetch", "xhr", "websocket", "manifest", "other"
]

OUTPUT_DIR = "scraped_data_full"

def clean_text(text):
    if not text:
        return ""
    
    # Basic cleaning but keep structure mostly intact
    text = re.sub(r'\[(단독|알립니다|속보|종합|기획|현장|포토|영상|인터뷰|부고|인사)\]', '', text)
    text = re.sub(r'(?<=\S)\([^)]*\)', '', text)
    text = re.sub(r'[\[\]]', ' ', text)
    text = re.sub(r'[●▶〈〉◇"“”△]', '', text)
    text = re.sub(r'(http|https)://[a-zA-Z0-9./?=_-]+', '', text)
    text = re.sub(r'www\.[a-zA-Z0-9./?=_-]+', '', text)
    text = re.sub(r'▽.*?(?=\n|$)', '', text)
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
    text = re.sub(r'\b[가-힣]{2,4}\s*기자', '', text)
    text = re.sub(r'\b[가-힣]{2,4}\s*특파원', '', text)
    text = re.sub(r'특별취재팀=.*?(?=\n|$)', '', text)
    text = re.sub(r'(\s*/\s*)+', ' ', text) 
    text = re.sub(r'[◆]', '', text)
    
    return re.sub(r'\s+', ' ', text).strip()

async def fetch_article_full(page, url, sem):
    """Fetch full article content."""
    async with sem:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=5000)
            try:
                await page.wait_for_selector('#dic_area, #newsct_article', timeout=3000)
            except:
                pass

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            subtitle = ""
            sub_elem = soup.select_one('.media_end_head_subheadline') or soup.select_one('.media_end_summary')
            if sub_elem:
                subtitle = clean_text(sub_elem.get_text())

            body_elem = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
            full_text = ""
            
            if body_elem:
                for tag in body_elem.select('script, style, iframe, .img_desc, .end_photo_org'):
                    tag.decompose()
                
                # Get full text with newlines
                raw_text = body_elem.get_text('\n')
                full_text = clean_text(raw_text)

            return {
                "subtitle": subtitle,
                "full_text": full_text
            }

        except Exception as e:
            return {"subtitle": "", "full_text": ""}

async def scrape_media_date(context, media, date, sem):
    """Scrape one media for one date."""
    url = f"https://media.naver.com/press/{media['code']}/newspaper?date={date}"
    page = await context.new_page()
    await page.route("**/*", lambda route: 
        route.abort() if route.request.resource_type in BLOCKED_RESOURCES 
        else route.continue_()
    )

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=10000)
        try:
            await page.wait_for_selector('div.newspaper_inner', timeout=5000)
        except:
            await page.close()
            return []

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        page_sections = soup.select('div.newspaper_inner')
        articles_to_process = []
        
        for section in page_sections:
            page_name = section.select_one('span.page_notation')
            page_txt = page_name.get_text(strip=True) if page_name else "Unknown"
            
            links = section.select('ul.newspaper_article_lst > li > a')
            for a in links:
                title_elem = a.select_one('strong')
                if not title_elem: continue
                title = title_elem.get_text(strip=True)
                link = a['href']
                
                articles_to_process.append({
                    "page": page_txt,
                    "title": title,
                    "url": link,
                    "media_code": media['code'],
                    "media_name": media['name'],
                    "date": date
                })
        
        await page.close()
        
        # Process ONLY first 5 articles per media for quick testing/comparison if not specified otherwise
        # But user asked for "similar to history scraper", so maybe all? 
        # "일단 오늘날짜로 해보자" implies a test run. I'll fetch ALL for today to be safe, filtering can happen later.
        
        detail_results = []
        batch_size = 5
        for i in range(0, len(articles_to_process), batch_size):
            batch = articles_to_process[i:i+batch_size]
            async def task_wrapper(article):
                p = await context.new_page()
                await p.route("**/*", lambda route: 
                    route.abort() if route.request.resource_type in BLOCKED_RESOURCES 
                    else route.continue_()
                )
                detail = await fetch_article_full(p, article['url'], sem)
                await p.close()
                article.update(detail)
                return article

            await asyncio.gather(*[task_wrapper(a) for a in batch])
            detail_results.extend(batch)

        return detail_results

    except Exception as e:
        print(f"Error scraping {media['name']} on {date}: {e}")
        try: await page.close()
        except: pass
        return []

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Specific date to scrape (YYYYMMDD)")
    args = parser.parse_args()

    date = args.date
    ym = date[:6]
    os.makedirs(os.path.join(OUTPUT_DIR, ym), exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        sem = asyncio.Semaphore(SEM_LIMIT)
        
        for media in MEDIA_LIST:
            result_file = os.path.join(OUTPUT_DIR, ym, f"{media['code']}_{date}.json")
            if os.path.exists(result_file):
                print(f"  Existing found: {result_file}, skipping.")
                continue

            print(f"  > Scraping {media['name']}...")
            articles = await scrape_media_date(context, media, date, sem)
            
            if articles:
                # Filter out empty content articles
                articles = [a for a in articles if a.get('full_text')]
                
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)
                print(f"    Saved {len(articles)} full articles.")
            else:
                print(f"    No articles found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
