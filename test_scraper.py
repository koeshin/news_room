import asyncio
from scraper import get_newspaper_data

async def main():
    print("Testing scraper for Chosun Ilbo (023) on 2026-01-30...")
    data = await get_newspaper_data("023", "20260130")
    
    if not data:
        print("No data found.")
        return
        
    for page in data[:2]: # Show first 2 pages
        print(f"\n[{page['page']}]")
        for art in page['articles'][:3]: # Show first 3 articles
            print(f"- {art['title']}")
            print(f"  Sub: {art['subtitle'][:50]}...")
            print(f"  URL: {art['url']}")

if __name__ == "__main__":
    asyncio.run(main())
