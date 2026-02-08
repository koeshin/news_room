# 뉴스룸 V2 시스템 아키텍처 가이드

이 문서는 LLM 및 개발자가 `news_room_v2` 프로젝트의 구조와 작동 방식을 이해하기 위해 작성되었습니다.

## 1. 프로젝트 개요
**News Room v2**는 개인화된 뉴스 추천 시스템입니다. 사용자의 읽기 기록과 설정을 바탕으로, 네이버 지면 뉴스 데이터를 수집, 분석, 추천합니다.
- **Frontend:** HTML/CSS/JS (Jinja2 Templates)
- **Backend:** FastAPI (Python)
- **Storage:** JSON Files (NoSQL-like simple storage)
- **AI Core:** LLM 기반 페르소나 분석 및 기사 점수화

---

## 2. 디렉토리 구조 및 역할

### `📂 news_room_v2/`
프로젝트의 루트 디렉토리입니다.

#### **핵심 실행 파일**
- **`web/main.py`**: **[Entry Point]** FastAPI 애플리케이션의 진입점입니다. 웹 서버 라우팅, API 엔드포인트 정의가 포함되어 있습니다.
- **`storage.py`**: 데이터 저장 및 로드 로직을 담당합니다. 파일 시스템 경로 관리의 중심입니다.
- **`refine_model.py`**: 추천 모델의 핵심 로직입니다. 사용자 피드백을 반영하거나 추천 점수를 계산합니다.

#### **Core & Analysis (`core/`)**
- **`simulate.py`**: 추천 시뮬레이션 및 데이터 분석을 수행하는 스크립트입니다.
- **`personas/`**: 사용자 페르소나 정의 파일(.md)들이 위치합니다. (예: `persona_20s.md`)

#### **Data Collection (`scrapers/`)**
- **`history_scraper.py`**: 과거 데이터 수집용 스크레이퍼입니다.
- **`daily_scrape.sh`**: 매일 실행되는 뉴스 데이터 수집 스크립트입니다.
- **`naver_media_codes.json`**: 네이버 뉴스 언론사 코드(OID) 및 카테고리 정보가 정의되어 있습니다.

#### **Data Storage (`data/` & `scraped_data_history/`)**
- **`scraped_data_history/`**: 날짜별(`YYYYMMDD`)로 수집된 뉴스 데이터(JSON)가 저장됩니다.
- **`data/user_feedback.json`**: (예정) 사용자 평가 로그가 저장됩니다.
- **`settings.json`**: 사용자의 구독 언론사 및 설정이 저장됩니다.

#### **Web Interface (`web/`)**
- **`templates/`**: HTML 템플릿 파일들 (`news_room.html`, `recommendations.html`, `settings.html` 등).
- **`static/`**: CSS (`style.css`), 이미지 등 정적 리소스.

---

## 3. 데이터 흐름 (Data Flow)

### 1단계: 수집 (Collection)
1. `daily_scrape.sh` 실행 (또는 `scrapers/` 내 스크립트).
2. `naver_media_codes.json`에 정의된 언론사의 지면 뉴스를 수집.
3. 결과는 `scraped_data_history/{YYYYMMDD}/{OID}.json` 형태로 저장.

### 2단계: 분석 및 추천 (Analysis)
1. 사용자가 웹 UI 또는 스크립트를 통해 추천 요청.
2. `core/` 또는 `refine_model.py`가 실행됨.
3. `personas/`의 페르소나와 최근 사용자 기록을 바탕으로 기사별 관련성 점수(Score) 계산.
4. 결과는 `data/loop_output.json` 등에 저장되어 웹에서 로드.

### 3단계: 제공 및 피드백 (Serving & Feedback)
1. **뉴스룸 (`/newsroom`)**: 날짜별, 언론사별 지면 뉴스를 원문 그대로 열람. 사용자는 '저장(Scrap)' 가능.
2. **AI 추천 (`/recommendations`)**: 분석된 추천 기사를 열람 및 '평가(1~5점)' 가능.
3. **설정 (`/settings`)**: 구독 언론사 관리.
4. 사용자 행동(평가, 스크랩)은 `/api/log` 등을 통해 서버에 기록되어 다음 추천의 입력 데이터로 활용(예정).

---

## 4. 상호 연결성 (Dependencies)
- **Web ↔ Storage**: `web/main.py`는 `storage.py` 함수들을 호출하여 데이터를 읽고 씁니다.
- **Scraper ↔ Storage**: 스크레이퍼는 독자적으로 실행되지만, `storage.py`의 경로 규칙을 따릅니다.
- **Settings ↔ Scraper**: 사용자가 설정에서 언론사를 변경하면, 스크레이퍼는 `settings.json`을 참조하여 수집 대상을 변경해야 합니다.

---

## 5. 실행 방법
```bash
# 서버 실행 (개발 모드)
uvicorn web.main:app --host 0.0.0.0 --port 8000 --reload
```
