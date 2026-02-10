# News Room Project


네이버 뉴스의 신문 지면 서비스를 활용하여 기사를 면 단위로 모아볼 수 있는 애플리케이션입니다. 종이 신문의 레이아웃을 디지털 환경에서 효율적으로 탐색하고 관리할 수 있도록 제작되었습니다.

## 주요 기능

### 기사 수집 및 탐색
- 여러 언론사의 신문 지면을 1면부터 순서대로 확인
- 섹션 기반 페이지네이션 (A1-10, A11-20, B1-10 등)
- 키워드 필터링 (제목, 부제목 검색)
- 초고속 스크래핑 (기존 대비 6.9배 향상)

### 스크랩 관리
- 관심 있는 기사 스크랩 및 읽음 상태 관리
- 폴더와 태그 시스템으로 체계적인 분류
- 마크다운 형식으로 내보내기 지원

### AI 기능
- AI Weekly Report: Gemini API로 주간 뉴스 요약 생성
- AI 1-Line Summary: 빠른 기사 파악을 위한 한 줄 요약

### 성능 최적화
- Persistent Caching: 로컬에 데이터 저장하여 즉시 로딩
- Lazy Loading: 선택한 언론사만 로드
- Force Refresh: 캐시 우회 및 최신 데이터 가져오기

## 성능 개선

| 항목 | 기존 | 개선 | 향상률 |
|------|------|------|------|
| 스크래핑 속도 (456개 기사) | 85.56초 | 12.48초 | 6.9배 |
| 병렬 처리 | 5개 동시 | 10개 동시 | 2배 |
| 캐시 히트 시 로딩 | N/A | 즉시 | - |

## 기술 스택

```
Frontend: Streamlit
Scraping: Playwright (Chromium)
AI: Google Gemini (Pro, Flash)
Storage: JSON (로컬 캐싱)
Async: asyncio + Semaphore
```

## 설치 및 실행

### 요구사항
- Python 3.8 이상

### 1. 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 2. Playwright 브라우저 설치
```bash
playwright install chromium
```

### 3. 환경 변수 설정 (선택)
AI 기능을 사용하려면 `.env` 파일 생성:
```
GOOGLE_API_KEY=your_api_key_here
```

### 4. 앱 실행
```bash
streamlit run app.py
```

## 프로젝트 구조

```
news_room/
├── app.py                      # Streamlit UI 및 메인 로직
├── scraper.py                  # 기본 스크래퍼
├── scraper_optimized.py        # 최적화 스크래퍼 (6.9배 빠름)
├── storage.py                  # 로컬 JSON 데이터 관리
├── analysis.py                 # Gemini AI 분석
├── naver_media_codes.json      # 언론사 코드
├── scraped_data/               # 캐시 데이터 (날짜별/언론사별)
└── walkthrough/                # 개발 기록
```

## 주요 파일 설명

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit UI, 사용자 인터랙션, 워크플로우 제어 |
| `scraper_optimized.py` | 최적화된 Playwright 스크래퍼 (브라우저 재사용, 리소스 차단) |
| `storage.py` | 스크랩 데이터, 캐시, 폴더/태그 관리 |
| `analysis.py` | Gemini API 연동 (주간 리포트, 1줄 요약) |

## 사용 가이드

### 1. 뉴스 보기
- 날짜와 언론사 선택
- 캐시가 있으면 즉시 로딩, 없으면 자동 스크래핑
- Force Refresh 버튼으로 최신 데이터 가져오기

### 2. 스크랩 관리
- 별 아이콘 클릭으로 스크랩 추가/제거
- 스크랩북 탭에서 폴더 생성 및 태그 추가
- 마크다운 내보내기로 외부 활용

### 3. AI 리포트
- 스크랩북에서 "AI Weekly Report" 클릭
- 주간 뉴스 요약 자동 생성
- (일요일 자동 안내)

