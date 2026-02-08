"""
기존 Playwright 스크래퍼 벤치마크 (비교용)
"""

import asyncio
import time
import scraper

TEST_MEDIA = [
    {"name": "조선일보", "oid": "023"},
    {"name": "중앙일보", "oid": "025"},
    {"name": "동아일보", "oid": "020"},
    {"name": "한겨레", "oid": "028"},
    {"name": "경향신문", "oid": "032"},
]

test_date = "20260130"

async def main():
    print("="*60)
    print("🐢 기존 Playwright 스크래퍼 테스트")
    print(f"📅 날짜: {test_date}")
    print("="*60)
    
    start = time.time()
    
    # 기존 스크래퍼는 개별 실행
    tasks = [scraper.get_newspaper_data(m['oid'], test_date, force_refresh=True) for m in TEST_MEDIA]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    
    print("\n" + "="*60)
    print("📊 결과")
    print("="*60)
    
    total_articles = 0
    for i, data in enumerate(results):
        name = TEST_MEDIA[i]['name']
        article_count = sum(len(page['articles']) for page in data) if data else 0
        total_articles += article_count
        print(f"  {name}: {article_count}개 기사")
    
    print(f"\n⏱️ 총 소요 시간: {elapsed:.2f}초")
    print(f"📰 총 기사 수: {total_articles}개")
    if total_articles > 0:
        print(f"⚡ 기사당 평균: {elapsed/total_articles*1000:.1f}ms")

if __name__ == "__main__":
    asyncio.run(main())
