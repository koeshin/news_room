import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_inner():
    url = "https://media.naver.com/press/023/newspaper?date=20260130"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(2)
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        inner = soup.select_one('div.newspaper_inner')
        if inner:
            print("--- Inner HTML ---")
            print(inner.prettify()[:2000])
        else:
            print("No inner found")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_inner())
