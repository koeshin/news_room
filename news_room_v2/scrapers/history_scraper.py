"""
History Scraper for Persona-based News Simulation
Period: 2025.06 ~ 2026.01 (1st - 7th of each month)
Target: 9 Media Outlets
Content: Title, Subtitle, First Sentence of each paragraph
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
    {"name": "전자신문", "code": "030"}, # 20s
    # {"name": "스포츠조선", "code": "076"}, # 20s (Failed: No paper view)
    {"name": "매일경제", "code": "009"}, # 30s
    {"name": "한국경제", "code": "015"}, # 30s
    {"name": "문화일보", "code": "021"}, # 50s
    {"name": "서울신문", "code": "081"}, # 50s
]

# Parallelism
SEM_LIMIT = 10
BLOCKED_RESOURCES = [
    "image", "media", "font", "stylesheet", "script",
    "fetch", "xhr", "websocket", "manifest", "other"
]

OUTPUT_DIR = "scraped_data_history"

def get_target_dates():
    """Generate target dates: 1st-7th of June 2025 to Jan 2026"""
    dates = []
    # 2025.06 - 2025.12
    for month in range(6, 13):
        for day in range(1, 8):
            dates.append(f"2025{month:02d}{day:02d}")
    
    # 2026.01
    for day in range(1, 8):
        dates.append(f"202601{day:02d}")
    
    return dates

def clean_text(text):
    if not text:
        return ""
    
    # 1. Remove specific tags completely (e.g., [단독], [알립니다])
    # Add more tags as needed
    text = re.sub(r'\[(단독|알립니다|속보|종합|기획|현장|포토|영상|인터뷰|부고|인사)\]', '', text)
    
    # 2. Remove brackets but keep content for others
    text = re.sub(r'[\[\]]', ' ', text)
    
    # 3. Remove special characters
    text = re.sub(r'[●▶〈〉]', '', text)
    
    # 4. Remove reporter credits/emails (lines starting with ▽ or containing email patterns at end)
    # This handles the User's example: ▽팀장 조은아...
    text = re.sub(r'▽.*?(?=\n|$)', '', text)
    
    # Remove email-like patterns if they are isolated or at end of sentence
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
    
    return re.sub(r'\s+', ' ', text).strip()

def extract_first_sentence(paragraph):
    """Extract the first sentence from a paragraph."""
    # Pre-filter paragraph for reporter lines
    if paragraph.strip().startswith("▽") or "@" in paragraph:
         # Aggressive check for reporter lines
         if "기자" in paragraph or "특파원" in paragraph:
             return ""

    paragraph = clean_text(paragraph)
    if not paragraph:
        return ""
    
    # Simple regex for sentence splitting (Korean/English)
    match = re.match(r'(.*?[.?!])(?=\s|$)', paragraph)
    if match:
        return match.group(1)
    return paragraph # Return whole if no terminator found

async def fetch_article_detail(page, url, sem):
    """Fetch article detail: subtitle and first sentences."""
    async with sem:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=5000)
            # Try to wait for body element
            try:
                await page.wait_for_selector('#dic_area, #newsct_article', timeout=3000)
            except:
                pass

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # 1. Subtitle
            subtitle = ""
            sub_elem = soup.select_one('.media_end_head_subheadline')
            if not sub_elem:
                sub_elem = soup.select_one('.media_end_summary')
            if sub_elem:
                subtitle = clean_text(sub_elem.get_text())

            # 2. Body & First Sentences
            body_elem = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
            summary_sentences = []
            
            if body_elem:
                # Remove unwanted elements
                for tag in body_elem.select('script, style, iframe, .img_desc, .end_photo_org'):
                    tag.decompose()
                
                # Split by <br> or block elements to get paragraphs
                # Using get_text with separator to preserve block structure
                text_content = body_elem.get_text('\n')
                paragraphs = text_content.split('\n')
                
                for p in paragraphs:
                    if len(p.strip()) > 10: # Filter short/empty lines
                        first_sent = extract_first_sentence(p)
                        if first_sent:
                            summary_sentences.append(first_sent)

            return {
                "subtitle": subtitle,
                "summary_sentences": summary_sentences
            }

        except Exception as e:
            # print(f"Error fetching detail {url}: {e}")
            return {"subtitle": "", "summary_sentences": []}

async def scrape_media_date(context, media, date, sem, test_mode=False):
    """Scrape one media for one date."""
    url = f"https://media.naver.com/press/{media['code']}/newspaper?date={date}"
    page = await context.new_page()
    
    # Block resources
    await page.route("**/*", lambda route: 
        route.abort() if route.request.resource_type in BLOCKED_RESOURCES 
        else route.continue_()
    )

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=10000)
        
        # Check if newspaper section exists
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
        
        # If test mode, limit articles
        if test_mode:
            articles_to_process = articles_to_process[:3] # 3 per date per media

        # Fetch details in parallel
        tasks = []
        # Reuse context? We can open new pages in the same context
        # But we need to be careful about too many pages.
        # SEM_LIMIT controls concurrency.
        
        # Create a pool of pages if needed, but simple way is opening/closing per task with semaphore
        # Be careful not to open too many pages at once. The semaphore should control the tasks.
        
        detail_results = []
        
        # Batch processing to avoid too many open pages
        batch_size = 5
        for i in range(0, len(articles_to_process), batch_size):
            batch = articles_to_process[i:i+batch_size]
            batch_tasks = []
            
            # Create a reusable page for the batch? No, simpler to create one per task
            # BUT creating pages is expensive.
            # Ideally we have a worker pool.
            # For simplicity here (and since we have SEM_LIMIT), let's just make tasks that open pages.
            
            async def task_wrapper(article):
                p = await context.new_page()
                await p.route("**/*", lambda route: 
                    route.abort() if route.request.resource_type in BLOCKED_RESOURCES 
                    else route.continue_()
                )
                detail = await fetch_article_detail(p, article['url'], sem)
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
    parser.add_argument("--test", action="store_true", help="Run in test mode (small batch)")
    parser.add_argument("--date", type=str, help="Specific date to scrape (YYYYMMDD)")
    args = parser.parse_args()

    if args.date:
        dates = [args.date]
    elif args.test:
        dates = ["20260105"] # Just one date for test
        print("🔧 Running in TEST MODE")
    else:
        dates = get_target_dates()

    # Create output directories
    for date in dates:
        ym = date[:6]
        os.makedirs(os.path.join(OUTPUT_DIR, ym), exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        sem = asyncio.Semaphore(SEM_LIMIT)
        
        for date in dates:
            print(f"📅 Scraping Date: {date}")
            ym = date[:6]
            
            for media in MEDIA_LIST:
                result_file = os.path.join(OUTPUT_DIR, ym, f"{media['code']}_{date}.json")
                if os.path.exists(result_file) and not args.test:
                    print(f"  Existing found: {media['name']}")
                    continue

                print(f"  > Scraping {media['name']}...")
                articles = await scrape_media_date(context, media, date, sem, args.test)
                
                if articles:
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(articles, f, ensure_ascii=False, indent=2)
                    print(f"    Saved {len(articles)} articles.")
                else:
                    print(f"    No articles found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
