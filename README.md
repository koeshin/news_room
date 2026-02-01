# 📰 News Room (나의 뉴스룸)

**News Room**은 네이버 뉴스 신문 지면(Newspaper) 서비스를 크롤링하여, 종이 신문처럼 면(Page) 별로 뉴스를 모아볼 수 있는 **Streamlit 기반 웹 애플리케이션**입니다.

![App Screenshot](https://via.placeholder.com/800x400?text=News+Room+App+Preview)
*(스크린샷 이미지가 있다면 여기에 추가하세요)*

## ✨ 주요 기능 (Features)

*   **📰 지면별 뉴스 보기**: 조선일보, 중앙일보, 매일경제 등 주요 언론사의 신문 지면을 1면부터 순서대로(A1, A2...) 볼 수 있습니다.
*   **⚡️ 초고속 병렬 로딩 (Parallel Prefetching)**: 앱 실행 시 등록된 모든 언론사의 뉴스를 비동기(Asyncio)로 미리 가져와, 로딩 없이 즉시 기사를 열람할 수 있습니다.
*   **🤖 스마트 부제목 추출**: 기사 목록에서 제목뿐만 아니라 **부제목(요약문)**을 자동으로 추출하여 보여줍니다. (동아일보 등 다양한 구조 지원)
*   **📑 스크랩북**: 마음에 드는 기사를 원클릭으로 저장하고, 날짜별로 관리할 수 있습니다.
*   **⚙️ 언론사 관리**: 보고 싶은 언론사를 OID로 자유롭게 추가/삭제할 수 있습니다.

## 🏗 아키텍처 (Architecture)

이 프로젝트는 **Python**으로 작성되었으며, 다음과 같은 기술 스택을 사용합니다.

```mermaid
graph TD
    User([User]) -->|Web Browser| Streamlit[Streamlit UI]
    Streamlit -->|Event Loop| AsyncManager[Asyncio Manager]
    AsyncManager -->|Concurrently| Scraper[Playwright Scraper]
    
    subgraph Scraping Engine
        Scraper -->|Headless Browser| NaverNews[Naver News (Newspaper View)]
        Scraper -- blocks --> Resources[Images/Fonts/Ads]
        Scraper -- extracts --> Subtitles[Subtitles/Summaries]
    end
    
    Streamlit -->|Read/Write| Storage[Local JSON Storage]
    Storage --> Settings[settings.json]
    Storage --> Scraps[scraps.json]
```

*   **Frontend**: `Streamlit`을 사용하여 직관적인 그리드 레이아웃 UI 구현
*   **Backend/Scraping**: 
    *   `Playwright (Async API)`: 동적 웹 페이지(JavaScript) 렌더링 및 데이터 추출
    *   `BeautifulSoup4`: HTML 파싱 및 DOM 탐색
    *   `Asyncio`: 다중 언론사 병렬 크롤링 및 세마포어(Semaphore)를 이용한 리소스 제어
*   **Storage**: 로컬 JSON 파일을 이용한 경량 데이터베이스 (`settings.json`, `scraps.json`)

## 🛠 설치 및 실행 방법 (Setup & Run)

### 1. 환경 설정

Python 3.8 이상이 필요합니다.

```bash
# 레포지토리 클론
git clone https://github.com/Start-to-End-Project/news_room.git
cd news_room

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 2. 실행

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501`에서 앱을 사용할 수 있습니다.

## 📁 프로젝트 구조

```
news_room/
├── app.py              # 메인 애플리케이션 (UI 및 로직)
├── scraper.py          # 크롤링 모듈 (Playwright)
├── storage.py          # 데이터 저장/로드 모듈
├── settings.json       # 언론사 설정 파일
├── scraps.json         # (자동생성) 스크랩 데이터
├── requirements.txt    # 의존성 목록
└── README.md           # 프로젝트 문서
```

## ⚠️ 주의사항

*   이 프로그램은 네이버 뉴스의 HTML 구조에 의존적이므로, 네이버 측의 UI 변경 시 작동하지 않을 수 있습니다.
*   과도한 요청은 차단될 수 있으므로 `scraper.py`에 구현된 세마포어(Semaphore) 제한을 임의로 해제하지 마세요.
# news_room
