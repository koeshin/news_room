import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def configure_genai():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True

def generate_weekly_report(scraps):
    """
    Gemini를 사용하여 주간 스크랩 리포트를 생성합니다.
    """
    if not configure_genai():
        return "⚠️ Google API Key가 설정되지 않았습니다. `.env` 파일을 확인해주세요."

    if not scraps:
        return "분석할 스크랩 데이터가 없습니다."

    # 모델 설정 (Gemini Pro)
    model = genai.GenerativeModel('gemini-pro')

    # 프롬프트 구성
    prompt = """
    당신은 나의 뉴스 큐레이터이자 분석가입니다. 
    아래는 내가 이번 주(월~토) 동안 스크랩한 뉴스 기사 목록입니다.
    이 기사들을 바탕으로 **주간 뉴스 브리핑 리포트**를 작성해 주세요.

    **[작성 가이드라인]**
    1. **핵심 키워드 3가지**: 전체 기사를 관통하는 핵심 키워드 3개를 뽑아주세요.
    2. **주요 이슈 요약**: 스크랩한 기사들을 주제별로 묶어서 어떤 이슈에 관심을 가졌는지 요약해 주세요. (각 이슈별로 2~3문장)
    3. **인사이트**: 내가 스크랩한 기사들의 경향을 분석하여, 내가 어떤 분야(정치, 경제, 기술 등)에 관심이 많은지, 그리고 다음 주에 눈여겨봐야 할 점은 무엇인지 조언해 주세요.
    4. 톤앤매너: 전문적이지만 친절하게(해요체), 마크다운 형식을 사용하여 가독성 있게 작성해 주세요.

    **[스크랩 기사 목록]**
    """

    for item in scraps:
        prompt += f"- 날짜: {item.get('date', 'Unknown')}\n"
        prompt += f"  언론사: {item['media']}\n"
        prompt += f"  제목: {item['title']}\n"
        if item.get('subtitle'):
            prompt += f"  내용요약: {item['subtitle']}\n"
        prompt += "\n"

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 리포트 생성 중 오류가 발생했습니다: {str(e)}"

def generate_one_line_summary(title, subtitle=""):
    """
    기사 제목과 부제목을 바탕으로 1줄 요약을 생성합니다. (Feature 2)
    """
    if not configure_genai():
        return ""
    
    try:
        # Gemini Flash 사용 (빠르고 저렴함)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
다음 뉴스 기사를 한 줄(최대 30자)로 요약해 주세요. 결과만 출력하세요.

제목: {title}
부제목: {subtitle if subtitle else '(없음)'}
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return ""

async def generate_summaries_batch(articles):
    """
    여러 기사의 요약을 병렬로 생성합니다.
    """
    if not configure_genai():
        return {}
    
    summaries = {}
    for art in articles:
        summary = generate_one_line_summary(art.get('title', ''), art.get('subtitle', ''))
        summaries[art['url']] = summary
    
    return summaries
