import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scan_articles():
    url = "https://media.naver.com/press/023/newspaper?date=20260130"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Get first 10 article links
        links = [a['href'] for a in soup.select('ul.newspaper_article_lst > li > a')][:10]
        
        print(f"Scanning {len(links)} articles for subtitles...")
        
        for link in links:
            try:
                await page.goto(link, wait_until="domcontentloaded")
                # Wait briefly for JS to potentially render
                await asyncio.sleep(0.5)
                
                c = await page.content()
                s = BeautifulSoup(c, 'html.parser')
                
                title = s.select_one('h2.media_end_head_headline')
                t_text = title.get_text(strip=True) if title else "No Title"
                
                # Check various candidates
                sub_1 = s.select_one('div.media_end_head_subheadline') # Common
                sub_2 = s.select_one('strong.media_end_summary')       # Summary
                sub_3 = s.select_one('div.news_headline')              # Old style?
                sub_4 = s.select_one('.media_end_head_infos')          # Maybe in info area?
                
                print(f"\n[Title]: {t_text}")
                if sub_1: print(f"  FOUND (subheadline): {sub_1.get_text(strip=True)}")
                if sub_2: print(f"  FOUND (summary): {sub_2.get_text(strip=True)}")
                
                # If nothing found, check header siblings
                if not sub_1 and not sub_2:
                    print("  - No subtitle found with standard selectors.")
            
            except Exception as e:
                print(f"Error fetching {link}: {e}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scan_articles())
