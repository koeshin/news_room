import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_donga():
    # Dong-A Ilbo article that is likely to have a summary/subtitle
    # Using a recent date or the one from previous context if valid
    # Let's try to find a list page first to get a valid URL, or use a known structure if possible.
    # Since I don't have a specific failing URL provided by the user, I'll fetch the list first then checking an article.
    
    date_str = "20260130"
    oid = "020" # Dong-A
    list_url = f"https://media.naver.com/press/{oid}/newspaper?date={date_str}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Fetching list: {list_url}")
        await page.goto(list_url, wait_until="domcontentloaded")
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Get first article link
        article_link = soup.select_one('ul.newspaper_article_lst > li > a')
        if not article_link:
            print("No articles found in list.")
            await browser.close()
            return

        url = article_link['href']
        print(f"Checking Article: {url}")
        
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1) # wait for render
        
        c = await page.content()
        s = BeautifulSoup(c, 'html.parser')
        
        print(f"Title: {s.select_one('h2.media_end_head_headline').get_text(strip=True) if s.select_one('h2.media_end_head_headline') else 'No Title'}")
        
        # Check candidates
        sub_1 = s.select_one('div.media_end_head_subheadline')
        sub_2 = s.select_one('strong.media_end_summary')
        sub_3 = s.select_one('div.media_end_head_guide')
        sub_4 = s.select_one('div.article_info') # Mentioned in plan
        
        print(f"Selector 'div.media_end_head_subheadline': {sub_1.get_text(strip=True) if sub_1 else 'NONE'}")
        print(f"Selector 'strong.media_end_summary': {sub_2.get_text(strip=True) if sub_2 else 'NONE'}")
        print(f"Selector 'div.media_end_head_guide': {sub_3.get_text(strip=True) if sub_3 else 'NONE'}")
        
        # Dump summary area if found but not matched or just to see
        summary_area = s.select_one('div.media_end_summary') # generic container?
        if summary_area:
             print("Found div.media_end_summary container.")
        
        # Check if there is any other potential summary
        # Sometimes it's direct child of content?
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_donga())
