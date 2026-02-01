import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_article_structure():
    url = "https://n.news.naver.com/article/newspaper/023/0003956132?date=20260130"
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
        
        # Find the main title and print siblings/parent
        title = soup.select_one('h2.media_end_head_headline')
        if title:
            print("Found Title:", title.get_text(strip=True))
            parent = title.find_parent('div')
            if parent:
                print("\n--- Parent of Title HTML ---")
                print(parent.prettify())
        else:
            print("Title not found with h2.media_end_head_headline")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_article_structure())
