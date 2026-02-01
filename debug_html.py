import asyncio
from playwright.async_api import async_playwright

async def debug_html():
    url = "https://media.naver.com/press/023/newspaper?date=20260130"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        content = await page.content()
        print(content[:1000])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_html())
