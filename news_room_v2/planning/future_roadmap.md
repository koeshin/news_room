# Future Roadmap & Improvement Plan

이 문서는 News Room v2의 초개인화(Hyper-personalization)를 위한 향후 개발 방향과 구체적인 실행 계획을 담고 있습니다.

## 🚀 목표: "나에게 가장 초개인화된 뉴스룸"

---

## 1. 피드백 루프 완성 (Feedback Loop Integration)
현재 `tracking_component`와 로그 수집은 되어 있으나, 이것이 실제 추천 알고리즘(`refine_model.py`)에 반영되지 않고 있습니다.

### 할 일 (Todo)
- [ ] **Data Pipeline 연결**: `data/user_feedback.json` (또는 logs) 데이터를 `refine_model.py`가 로드하도록 수정.
- [ ] **가중치 동적 조정**: 사용자가 좋아요(5점)를 준 기사의 키워드 가중치를 페르소나 벡터에 추가.
- [ ] **Negative Filtering**: 낮은 점수(1~2점)를 준 기사의 주제나 키워드는 향후 추천에서 감점 처리.
- [ ] **Implicit Feedback**: 명시적 평가(1~5점) 외 체류 시간, 클릭 여부 등 암시적 피드백 수집 및 반영.

---

## 2. 페르소나 고도화 (Advanced Persona Evolution)
페르소나가 정적인 텍스트 파일에 머물지 않고, 사용자와 함께 성장해야 합니다.

### 할 일 (Todo)
- [ ] **Daily Keyword Generation**: 매일 밤, 그날의 사용자 활동(스크랩, 평가)을 요약하여 `personas/persona_20s.md`의 키워드 섹션을 LLM으로 자동 업데이트.
- [ ] **Context Awareness**: "주말에는 가벼운 에세이", "평일 아침에는 경제 뉴스" 등 시간/요일별 선호도 학습 모델 추가.
- [ ] **Interest Decay**: 오래된 관심사의 가중치를 서서히 낮추는 로직 구현 (최신 관심사 우선).

---

## 3. 추천 시스템 고도화 (Recommendation Engine Refinement)
단순 키워드 매칭을 넘어선 깊이 있는 추천을 지향합니다.

### 할 일 (Todo)
- [ ] **Serendipity(우연성) 확보**: 필터 버블 방지를 위해, 사용자의 관심사 밖이지만 사회적으로 중요한 이슈(Breaking News)를 20% 비율로 섞어서 추천 ("Must Read" 섹션).
- [ ] **Cross-Reference Analysis**: 동일 사건에 대해 보수/진보/중도 언론사의 기사를 묶어서 보여주는 "관점 비교" 기능.
- [ ] **Why This?**: "이 기사를 추천한 이유: 최근 '반도체' 관련 기사를 3건 스크랩하셨습니다"와 같은 설명(Explainability) 추가.

---

## 4. 추가 제안 사항 (Suggestions)

### 💡 Multi-Modal Experience
- **TTS 브리핑**: 출근길에 들을 수 있도록, 추천 기사 5개를 요약하여 오디오 브리핑으로 생성.
- **Visual News**: 텍스트 기사를 인포그래픽 스타일의 카드뉴스로 변환 (이미지 생성 모델 활용).

### 💡 Notification System
- **Real-time Alert**: 페르소나와 일치도 95% 이상의 중요한 기사가 수집되면 즉시 알림 제공.
- **Daily Digest**: 매일 저녁, "오늘 놓치면 안 될 뉴스 3선" 이메일/알림 발송.

### 💡 Community & Social (Optional)
- 유사한 페르소나를 가진 익명의 사용자들과 "이달의 추천 기사" 랭킹 공유.

---

## 📋 우선순위 실행 계획 (Next Steps)

1. **User Feedback Integration**: 수집된 평가 데이터를 추천 점수 계산 로직에 반영 (최우선).
2. **Dynamic Persona Update Script**: 일일 로그 분석 및 페르소나 파일 갱신 스크립트 작성.
3. **UI for Feedback**: "이 추천이 왜 떴나요?" 툴팁 추가 등 UX 개선.
