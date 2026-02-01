import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_target():
    url = "https://n.news.naver.com/article/newspaper/020/0003693904?date=20260131"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Current scraper logic simulation
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] else route.continue_())
        
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=5000)
        
        # Replicating the wait logic
        try:
           await page.wait_for_selector('div.media_end_head_subheadline, strong.media_end_summary, div.media_end_summary', timeout=2000)
        except:
           pass

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        print(f"Title: {soup.select_one('h2.media_end_head_headline').get_text(strip=True) if soup.select_one('h2.media_end_head_headline') else 'No Title'}")
        
        subtitle = ""
        # 1. Standard
        sub_elem = soup.select_one('div.media_end_head_subheadline')
        if sub_elem:
            print("[Match] div.media_end_head_subheadline")
            subtitle = sub_elem.get_text(strip=True)
            
        # 2. Summary
        if not subtitle:
            summary_elem = soup.select_one('strong.media_end_summary')
            if summary_elem:
                print("[Match] strong.media_end_summary")
                subtitle = summary_elem.get_text(strip=True)
        
        # 3. Summary Div (fallback)
        if not subtitle:
            summary_div = soup.select_one('div.media_end_summary')
            if summary_div:
                print("[Match] div.media_end_summary")
                subtitle = summary_div.get_text(strip=True)
                
        print(f"Extracted Subtitle: {subtitle}")
        
        # Dump HTML of interest if empty
        if not subtitle:
            print("\n--- HTML Dump (Body) ---")
            print(soup.body.prettify()[:1000])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_target())
