import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_article():
    # A specific article URL that effectively has a subtitle
    url = "https://n.news.naver.com/article/newspaper/023/0003956132?date=20260130" 
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a realistic User-Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print(f"Fetching {url}...")
        await page.goto(url, wait_until="domcontentloaded")
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Try to find common subtitle classes
        candidates = [
            'div.media_end_head_title',
            'div.media_end_head_subheadline',
            'h2.media_end_head_headline', 
            'strong.media_end_summary',
            'div.news_headline'
        ]
        
        print("\n--- Selectors Check ---")
        for sel in candidates:
            elems = soup.select(sel)
            print(f"Selector '{sel}': found {len(elems)}")
            for e in elems:
                print(f"  -> Text: {e.get_text(strip=True)[:50]}...")

        # Print a chunk of the header area to manually inspect if needed
        header_area = soup.select_one('div.media_end_head_inner')
        if header_area:
            print("\n--- Header Area HTML ---")
            print(header_area.prettify()[:1000])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_article())
