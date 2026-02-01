import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scan_list_page():
    # Try JoongAng Ilbo (025) as they often have summaries
    url = "https://media.naver.com/press/025/newspaper?date=20260130"
    print(f"Scanning list page: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        items = soup.select('div.newspaper_txt_box')
        print(f"Found {len(items)} text boxes.")
        
        found_count = 0
        for item in items:
            title = item.select_one('strong')
            summary = item.select_one('p')
            
            t_text = title.get_text(strip=True) if title else "No Title"
            s_text = summary.get_text(strip=True) if summary else ""
            
            if s_text:
                found_count += 1
                print(f"[FOUND] Title: {t_text}")
                print(f"  -> Subtitle (List View): {s_text}")
        
        if found_count == 0:
            print("No subtitles found in the list view for this date/media.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scan_list_page())
