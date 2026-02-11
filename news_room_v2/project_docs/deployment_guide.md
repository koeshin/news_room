# 배포 가이드: 나만의 뉴스룸 웹사이트 만들기

이 가이드는 GitHub에 코드를 올리면 자동으로 배포되어, 인터넷 어디서든 접속할 수 있는 웹사이트를 만드는 방법을 설명합니다. 가장 추천하는 플랫폼은 **Railway**입니다.

---

## 1. 배포 준비물 (파일 생성)

프로젝트 루트 디렉토리에 `Dockerfile`이 필요합니다. 이 파일은 서버 컴퓨터 세팅을 자동화해줍니다.

### `Dockerfile` 생성
`news_room_v2` 폴더가 아닌, **최상위 루트 폴더**에 `Dockerfile`이라는 이름(확장자 없음)으로 아래 내용을 저장하세요.

```dockerfile
# 1. 파이썬 3.11 버전 사용
FROM python:3.11-slim

# 2. 작업 폴더 설정
WORKDIR /app

# 3. 필수 패키지 설치
# 시스템 패키지 업데이트 및 git 설치 (필요시)
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 4. 의존성 파일 복사 및 설치
COPY news_room_v2/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Playwright 브라우저 설치 (뉴스 수집용)
RUN playwright install --with-deps chromium

# 6. 소스 코드 복사
COPY . /app

# 7. 포트 설정
ENV PORT=8000
EXPOSE 8000

# 8. 서버 실행 명령어 (데이터 다운로드 로직 포함 가능)
CMD ["uvicorn", "news_room_v2.web.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 2. Railway 배포 단계

### 1단계: GitHub 연결
1. [Railway.app](https://railway.app/)에 접속하여 가입합니다.
2. "New Project" -> "Deploy from GitHub repo"를 선택합니다.
3. 방금 푸시한 `news_room` 리포지토리를 선택합니다. (`v2` 브랜치 선택)

### 2단계: 서비스 설정
1. 리포지토리를 선택하면 자동으로 빌드가 시작됩니다.
2. **Settings** 탭 -> **Networking** 섹션으로 이동합니다.
3. "Public Networking"에서 "Generate Domain"을 클릭합니다.
   - 예: `financial-news-room-production.up.railway.app` 같은 주소가 생깁니다. 이 주소가 당신의 웹사이트 주소입니다!

### 3단계: 환경 변수 설정 (중요)
로컬에서 `.env` 파일에 썼던 내용들(API 키 등)을 Railway에 등록해야 합니다.
1. **Variables** 탭으로 이동합니다.
2. `OPENAI_API_KEY`, `TAVILY_API_KEY` 등을 입력하고 추가합니다.

### 4단계: 데이터 영구 저장 (Volume) **[매우 중요]**
Railway 서버는 배포할 때마다 초기화됩니다. 수집한 뉴스 데이터(`scraped_data_history`)가 날아가지 않으려면 **Volume**을 연결해야 합니다.
1. Railway 프로젝트 뷰에서 우클릭 -> **Volume** 추가.
2. 생성된 Volume과 배포된 서비스를 연결합니다.
3. 서비스의 **Settings** -> **Service** -> **Volume Mounts**에서 아래 경로를 마운트합니다.
   - **Mount Path:** `/app/news_room_v2/scraped_data_history`

---

## 3. 기존 데이터(스크랩, DB) 옮기는 방법

로컬에 있는 `scraps.json`이나 `chroma_db`는 `.gitignore`에 의해 GitHub에 올라가지 않았습니다. 이 데이터를 배포된 서버로 옮기는 가장 쉬운 방법은 **"클라우드 저장소(Google Drive 등)를 통한 다운로드"** 입니다.

### 1단계: 데이터 압축 (로컬)
터미널에서 중요한 데이터를 압축합니다.
```bash
# 중요 데이터 압축 (scraps.json, chroma_db, settings.json 등)
tar -czvf my_data.tar.gz scraps.json news_room_v2/chroma_db news_room_v2/settings.json
```

### 2단계: 파일 업로드 및 링크 생성
1. 생성된 `my_data.tar.gz` 파일을 Google Drive나 Dropbox에 업로드합니다.
2. **"링크가 있는 모든 사용자에게 공개"** 로 설정하고 다운로드 링크를 복사합니다.
   - (참고: Google Drive의 경우 파일 ID를 이용해 직접 다운로드 링크로 변환해야 합니다.)

### 3단계: Railway에서 데이터 한 번만 가져오기
Railway의 **Variables** 탭에서 `DATA_URL`이라는 환경 변수를 만들고, 방금 복사한 다운로드 링크를 값으로 넣습니다.

그리고 `Dockerfile`의 마지막 줄(`CMD`)을 아래와 같이 수정해서 배포하면, 서버가 켜질 때 데이터를 다운로드 받습니다.

```dockerfile
# (수정된 CMD 예시)
CMD curl -L "$DATA_URL" -o data.tar.gz && tar -xzvf data.tar.gz && rm data.tar.gz && uvicorn news_room_v2.web.main:app --host 0.0.0.0 --port 8000
```
> **주의:** 이 방법은 매번 배포 때마다 데이터를 덮어쓸 위험이 있습니다. **최초 1회만** 이 코드로 배포하고, 데이터가 Volume에 잘 들어갔다면 다시 원래 `CMD`로 돌려놓는 것이 안전합니다.

### 더 좋은 방법 (추천)
가장 깔끔한 방법은 **S3(AWS)** 같은 외부 저장소를 사용하는 것입니다. `storage.py` 코드를 수정해서 로컬 파일 시스템 대신 S3에 저장하게 하면, 로컬/배포 환경 상관없이 같은 데이터를 쓸 수 있습니다. (추후 로드맵에 포함 가능)
