# 2026-02-10 작업 기록

## 요약
- 총 작업 수: 3개 영역 (환경설정, 데이터수집, 페르소나 고도화)
- 총 변경 파일: 6개 (`setup_and_run.bat`, `scrapers/history_scraper.py`, `core/vector_store.py`, `core/agent_persona.py`, `core/refine_model.py`, `core/recommendation.py`)
- 주요 성과: 페르소나 자동 업데이트 및 부정 필터링 추천 시스템 구현

---

## 작업 1: News Room V2 환경 설정 및 스크래퍼 개선

### 무엇을
- 대상: `setup_and_run.bat`, `scrapers/history_scraper.py`
- 범위: 가상환경 구축, 패키지 설치, 스크래퍼 정제 로직 개선

### 어떻게
- 방법:
    - Windows UTF-8 인코딩 설정 (`chcp 65001`) 및 이모지 제거
    - 정규식(Regex) 강화: 괄호(`(AI)`, `(5)` 등), URL, 기자명 제거
    - 문장 추출 로직 변경: 문단 당 1문장 → 2문장
- 도구: `playwright`, `bs4`, `chromadb`

### 왜
- 배경: Windows 환경에서의 인코딩 오류 및 데이터 품질 저하 문제 해결
- 목적: 안정적인 실행 환경과 고품질의 뉴스 텍스트 데이터(2025.09~2026.01) 확보

### 결과
- `news_room_v2_env` 구축 및 의존성 설치 완료
- 스크래퍼 기능 개선 (텍스트 정제율 향상)

---

## 작업 2: 페르소나 고도화 (Persona Elevation)

### 무엇을
- 대상: `core/agent_persona.py`, `core/refine_model.py`
- 범위: Gemini 1.5 Flash 연동을 통한 페르소나 동적 업데이트

### 어떻게
- 방법:
    - `update_persona_definition` 함수 구현 (Gemini 1.5 Flash 사용)
    - 사용자 피드백(평점 1-5점)을 분석하여 `persona_20s.md` 파일 자동 수정
    - 프롬프트 설계: `Key Interests` 추가 및 `Negative Keywords` 섹션 생성
- 도구: `google-generativeai`

### 왜
- 배경: 정적인 페르소나로는 사용자의 변화하는 취향 반응 불가 (Roadmap 1-2, 1-3)
- 목적: 사용자가 싫어하는(1-2점) 주제를 파악하여 페르소나에 부정 키워드로 등록

### 결과
- 피드백 루프 구현 완료 (평점 → 페르소나 업데이트)

---

## 작업 3: 동적 추천 시스템 구축

### 무엇을
- 대상: `core/recommendation.py` (신규)
- 범위: 실시간 페르소나 반영 뉴스 추천

### 어떻게
- 방법:
    - Markdown 파싱을 통한 `Interests` 및 `Negative Keywords` 로딩
    - 부정 키워드 포함 시 점수 페널티 부여 로직 구현
    - Vector Search + 필터링 조합
- 도구: `chromadb`, `sentence-transformers`

### 왜
- 배경: 업데이트된 페르소나를 즉시 추천 결과에 반영하여 사용자 만족도 제고
- 목적: 싫어하는 뉴스는 줄이고 관심사는 더 정확하게 추천

### 결과
- `walkthrough.md` 사용자 가이드 작성 완료 (검증 프로세스 정립)
