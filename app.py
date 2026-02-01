import streamlit as st
import asyncio
from datetime import datetime, timedelta
import scraper
import storage
import analysis
import time

# 페이지 설정
st.set_page_config(page_title="나의 뉴스룸", layout="wide")

# 사이드바 메뉴
menu = st.sidebar.selectbox("메뉴 선택", ["뉴스룸", "스크랩 북", "환경 설정"])

# 세션 상태 초기화 (데이터 캐싱용)
if "news_data" not in st.session_state:
    st.session_state.news_data = {}

# 스크랩 상태 캐싱 (UI 반응 속도 향상용)
if "scrapped_urls" not in st.session_state:
    st.session_state.scrapped_urls = set()
    # 초기 로드 시 한 번 채워넣기
    all_scraps = storage.load_scraps()
    for date_key in all_scraps:
        for s in all_scraps[date_key]:
            st.session_state.scrapped_urls.add(s['url'])

def get_yesterday():
    return datetime.now() - timedelta(days=1)

def format_date_display(date_obj):
    return date_obj.strftime("%Y-%m-%d")

def format_date_param(date_obj):
    return date_obj.strftime("%Y%m%d")

# 1. 뉴스룸 화면
if menu == "뉴스룸":
    st.title("📰 나의 뉴스룸")
    
    settings = storage.load_settings()
    media_list = settings.get("media_list", [])
    
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_media = st.selectbox("언론사 선택", [m['name'] for m in media_list])
    with col2:
        # 기본값을 어제로 설정
        selected_date = st.date_input("날짜 선택", get_yesterday())
    
    date_str = selected_date.strftime("%Y%m%d")
    
    # --- Lazy Loading Logic (선택된 언론사만 로드) ---
    # 선택된 언론사 OID 가져오기
    oid = next(m['oid'] for m in media_list if m['name'] == selected_media)
    cache_key = f"{oid}_{date_str}"
    
    # 1단계: 세션 상태 확인 (가장 빠름)
    if cache_key not in st.session_state.news_data:
        # 2단계: 로컬 파일 캐시 확인 (네트워크 요청 없음)
        cached_data = storage.load_news_cache(date_str, oid)
        if cached_data:
            st.session_state.news_data[cache_key] = cached_data
            st.toast(f"⚡ {selected_media} 캐시에서 로드 완료!", icon="💾")
        else:
            # 3단계: 네트워크에서 가져오기 (가장 느림)
            with st.spinner(f"{selected_media} 뉴스를 가져오는 중... (최초 1회만 발생)"):
                data = asyncio.run(scraper.get_newspaper_data(oid, date_str))
                if data:
                    st.session_state.news_data[cache_key] = data
                else:
                    st.session_state.news_data[cache_key] = [] # 데이터 없음 표시
    
            
    # 새로고침 버튼 (강제 새로고침)
    if st.button("🔄 뉴스 새로고침", help="캐시를 무시하고 최신 데이터를 가져옵니다."):
        with st.spinner(f"{selected_media} 뉴스를 다시 가져옵니다..."):
             data = asyncio.run(scraper.get_newspaper_data(oid, date_str, force_refresh=True))
             st.session_state.news_data[cache_key] = data if data else []
             st.rerun()

    display_data = st.session_state.news_data.get(cache_key)
    
    if not display_data:
        st.info("데이터가 없습니다. 날짜를 확인하거나 '뉴스 새로고침'을 눌러주세요.")
    else:
        # 그리드 레이아웃 적용
        
        # 페이지 정렬 (A1, A2, A10 순서)
        def sort_key(page_dict):
            p = page_dict['page']
            # "A1면" 등에서 숫자 추출
            import re
            match = re.search(r'(\d+)', p)
            if match:
                return int(match.group(1))
            return 999
            
        pages = sorted(display_data, key=sort_key)
        
        # 전체 면 리스트를 2개씩 묶어서 처리
        cols_per_row = 2
        
        for i in range(0, len(pages), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < len(pages):
                    page = pages[i + j]
                    with cols[j]:
                        with st.container(border=True):
                            st.markdown(f"#### 📍 {page['page']}")
                            
                            for idx, art in enumerate(page['articles'][:5]): # 각 면당 최대 5개만 간략히? 아니면 전체? 일단 전체
                                col_a, col_b = st.columns([0.85, 0.15])
                                with col_a:
                                    # 제목
                                    st.markdown(f"**{art['title']}**")
                                    # 부제목 (작은 글씨)
                                    if art.get('subtitle'):
                                        st.caption(f"{art['subtitle']}")
                                     # 링크
                                    st.markdown(f"<a href='{art['url']}' target='_blank' style='text-decoration:none; color:gray; font-size:0.8em;'>기사 원문 ></a>", unsafe_allow_html=True)

                                with col_b:
                                    # 스크랩 버튼 (Toggle)
                                    is_scrapped = art['url'] in st.session_state.scrapped_urls
                                    btn_label = "★" if is_scrapped else "☆"
                                    btn_help = "스크랩 해제" if is_scrapped else "스크랩"
                                    
                                    if st.button(btn_label, key=f"scr_{cache_key}_{page['page']}_{idx}", help=btn_help):
                                        # Toggle Action
                                        added = storage.toggle_scrap(format_date_display(selected_date), selected_media, art)
                                        if added:
                                            st.session_state.scrapped_urls.add(art['url'])
                                            st.toast("저장완료!", icon="✅")
                                        else:
                                            st.session_state.scrapped_urls.discard(art['url'])
                                            st.toast("삭제됨!", icon="🗑️")
                                        st.rerun()
                                st.divider()

# 2. 스크랩 북 화면
elif menu == "스크랩 북":
    st.title("📑 스크랩 북")
    
    scraps = storage.load_scraps()
    
    if not scraps:
        st.info("저장된 스크랩이 없습니다. 뉴스룸에서 마음에 드는 기사를 스크랩해 보세요!")
    else:
        # 날짜별 역순 정렬
        sorted_dates = sorted(scraps.keys(), reverse=True)
        

        # 주간 리포트 버튼 (사이드바 혹은 상단)
        with st.expander("📊 AI 주간 리포트 (Beta)", expanded=False):
            st.info("지난 월요일부터 오늘(또는 어제)까지의 스크랩을 모아 AI가 분석해줍니다.")
            if st.button("이번 주 리포트 생성하기"):
                with st.spinner("Gemini가 기사를 읽고 분석 중입니다... (약 10~20초 소요)"):
                    weekly_scraps = storage.get_weekly_scraps()
                    report = analysis.generate_weekly_report(weekly_scraps)
                    st.markdown(report)

        st.divider()

        for date_str in sorted_dates:
            st.header(f"📅 {date_str}")
            for idx, item in enumerate(scraps[date_str]):
                # 읽음 상태에 따른 스타일
                is_read = item.get('read', False)
                container_border = True
                
                with st.container(border=container_border):
                    col_check, col_content, col_del = st.columns([0.05, 0.85, 0.1])
                    
                    with col_check:
                         # 읽음 체크박스
                         new_read_status = st.checkbox("", value=is_read, key=f"read_{date_str}_{idx}")
                         if new_read_status != is_read:
                             storage.mark_as_read(date_str, item['url'], new_read_status)
                             st.rerun()

                    with col_content:
                        title_prefix = "✅ " if is_read else ""
                        title_style = "color: gray; text-decoration: line-through;" if is_read else ""
                        
                        st.markdown(f"<h3 style='margin:0; padding:0; font-size:1.2em; {title_style}'>[{item['media']}] {item['title']}</h3>", unsafe_allow_html=True)
                        
                        if item['subtitle']:
                            st.write(item['subtitle'])
                        st.markdown(f"[기사 읽기]({item['url']})")
                        st.caption(f"스크랩 시간: {item['scrapped_at']}")
                        
                    with col_del:
                        if st.button("🗑️", key=f"del_{date_str}_{idx}", help="삭제"):
                            storage.remove_scrap(date_str, item['url'])
                            st.session_state.scrapped_urls.discard(item['url']) # 캐시 동기화
                            st.rerun()

# 3. 환경 설정 화면
elif menu == "환경 설정":
    st.title("⚙️ 환경 설정")
    
    settings = storage.load_settings()
    
    st.subheader("언론사 목록 관리")
    
    # 목록 표시 및 삭제
    for idx, media in enumerate(settings['media_list']):
        col_m1, col_m2, col_m3 = st.columns([0.4, 0.4, 0.2])
        col_m1.write(f"**{media['name']}**")
        col_m2.write(f"OID: {media['oid']}")
        if col_m3.button("삭제", key=f"del_media_{idx}"):
            settings['media_list'].pop(idx)
            storage.save_settings(settings)
            st.rerun()
            
    st.divider()
    
    st.subheader("신규 언론사 추가")
    with st.form("add_media_form"):
        new_name = st.text_input("언론사 이름 (예: 매일경제)")
        new_oid = st.text_input("언론사 OID (예: 009)")
        submit = st.form_submit_button("추가하기")
        
        if submit:
            if new_name and new_oid:
                # 중복 체크
                if any(m['oid'] == new_oid for m in settings['media_list']):
                    st.error("이미 존재하는 OID입니다.")
                else:
                    settings['media_list'].append({"name": new_name, "oid": new_oid})
                    storage.save_settings(settings)
                    st.success(f"{new_name}이(가) 추가되었습니다!")
                    st.rerun()
            else:
                st.error("이름과 OID를 모두 입력해 주세요.")
    
    st.info("""
    **OID 찾는 법:** 
    네이버 뉴스 '신문 보기' 페이지에서 해당 언론사를 클릭했을 때, 
    브라우저 주소창의 `/press/XXX/` 부분에서 **XXX** 숫자가 OID입니다.
    """)
