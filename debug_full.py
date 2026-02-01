import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_full():
    url = "https://media.naver.com/press/023/newspaper?date=20260130"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a more realistic context
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        
        # Wait for potential dynamic content
        await asyncio.sleep(3)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        inner = soup.select('div.newspaper_inner')
        print(f"Found {len(inner)} newspaper_inner elements.")
        
        if len(inner) == 0:
            print("No inner elements found. Saving full HTML to debug.html")
            with open("debug.html", "w") as f:
                f.write(content)
            await page.screenshot(path="debug_full.png")
        else:
            for i, section in enumerate(inner[:3]):
                tit = section.select_one('strong.newspaper_tit')
                print(f"Section {i} title: {tit.get_text(strip=True) if tit else 'NONE'}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_full())
