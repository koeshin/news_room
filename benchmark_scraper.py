"""
News Room Scraper Benchmark
Playwright vs httpx 성능 비교 스크립트

사용법: python benchmark_scraper.py
"""

import asyncio
import time
from datetime import datetime, timedelta

# 테스트 대상 언론사 (5개)
TEST_MEDIA = [
    {"name": "조선일보", "oid": "023"},
    {"name": "중앙일보", "oid": "025"},
    {"name": "동아일보", "oid": "020"},
    {"name": "한겨레", "oid": "028"},
    {"name": "경향신문", "oid": "032"},
]

# 어제 날짜
TEST_DATE = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

async def benchmark_playwright():
    """기존 Playwright 기반 스크래퍼 테스트"""
    import scraper  # 기존 스크래퍼
    
    start = time.time()
    tasks = [scraper.get_newspaper_data(m['oid'], TEST_DATE, force_refresh=True) for m in TEST_MEDIA]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    total_articles = sum(len(page['articles']) for r in results if r for page in r)
    return elapsed, total_articles

async def benchmark_httpx():
    """새로운 httpx 기반 스크래퍼 테스트"""
    import scraper_httpx  # httpx 기반 스크래퍼
    
    start = time.time()
    tasks = [scraper_httpx.get_newspaper_data(m['oid'], TEST_DATE) for m in TEST_MEDIA]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    total_articles = sum(len(page['articles']) for r in results if r for page in r)
    return elapsed, total_articles

async def main():
    print("=" * 60)
    print("🏎️ News Room Scraper Benchmark")
    print(f"📅 테스트 날짜: {TEST_DATE}")
    print(f"📰 테스트 언론사: {', '.join(m['name'] for m in TEST_MEDIA)}")
    print("=" * 60)
    
    # Playwright 벤치마크
    print("\n[1/2] Playwright 기반 스크래퍼 테스트 중...")
    try:
        pw_time, pw_articles = await benchmark_playwright()
        print(f"  ✅ 완료: {pw_time:.2f}초 ({pw_articles}개 기사)")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        pw_time, pw_articles = None, 0
    
    # httpx 벤치마크
    print("\n[2/2] httpx 기반 스크래퍼 테스트 중...")
    try:
        httpx_time, httpx_articles = await benchmark_httpx()
        print(f"  ✅ 완료: {httpx_time:.2f}초 ({httpx_articles}개 기사)")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        httpx_time, httpx_articles = None, 0
    
    # 결과 비교
    print("\n" + "=" * 60)
    print("📊 결과 비교")
    print("=" * 60)
    
    if pw_time and httpx_time:
        speedup = pw_time / httpx_time
        print(f"  Playwright: {pw_time:.2f}초")
        print(f"  httpx:      {httpx_time:.2f}초")
        print(f"  🚀 속도 향상: {speedup:.1f}배 빠름!")
    else:
        print("  (일부 테스트 실패로 비교 불가)")

if __name__ == "__main__":
    asyncio.run(main())
