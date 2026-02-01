import streamlit as st
import asyncio
from datetime import datetime, timedelta
import scraper
import storage

# 페이지 설정
st.set_page_config(page_title="나의 뉴스룸", layout="wide")

# 사이드바 메뉴
menu = st.sidebar.selectbox("메뉴 선택", ["뉴스룸", "스크랩 북", "환경 설정"])

# 세션 상태 초기화 (데이터 캐싱용)
if "news_data" not in st.session_state:
    st.session_state.news_data = {}

def get_yesterday():
    return datetime.now() - timedelta(days=1)

def format_date_display(date_obj):
    return date_obj.strftime("%Y-%m-%d")

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
    
    # --- Parallel Prefetching Logic ---
    # 앱 시작 시(혹은 날짜 변경 시) 모든 언론사의 데이터를 미리 가져옴
    if "prefetched_date" not in st.session_state:
        st.session_state.prefetched_date = None
        
    current_date_check = f"{date_str}"
    
    # 아직 이 날짜에 대한 프리패칭을 시도하지 않았다면 시작
    if st.session_state.prefetched_date != current_date_check:
        with st.spinner(f"{format_date_display(selected_date)} 뉴스 전체 그물을 던지는 중... (전체 언론사 동시 로딩)"):
            async def prefetch_all():
                tasks = []
                for m in media_list:
                    check_key = f"{m['oid']}_{date_str}"
                    if check_key not in st.session_state.news_data:
                        tasks.append(scraper.get_newspaper_data(m['oid'], date_str))
                    else:
                        tasks.append(asyncio.sleep(0, result=st.session_state.news_data[check_key])) # Dummy
                
                results = await asyncio.gather(*tasks)
                
                for m, res in zip(media_list, results):
                    key = f"{m['oid']}_{date_str}"
                    st.session_state.news_data[key] = res
            
            asyncio.run(prefetch_all())
            st.session_state.prefetched_date = current_date_check
            # st.success("모든 신문 배달 완료!") # 너무 깜빡거릴 수 있으므로 생략 혹은 Toast
            
    # 선택된 언론사 데이터 표시
    oid = next(m['oid'] for m in media_list if m['name'] == selected_media)
    cache_key = f"{oid}_{date_str}"
    
    if st.button("뉴스 새로고침"):
        # 강제 새로고침
        with st.spinner(f"{selected_media} 뉴스를 다시 가져옵니다..."):
             data = asyncio.run(scraper.get_newspaper_data(oid, date_str))
             st.session_state.news_data[cache_key] = data
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
                                    if st.button("scrap", key=f"scr_{cache_key}_{page['page']}_{idx}", help="스크랩 저장"):
                                        success = storage.add_scrap(format_date_display(selected_date), selected_media, art)
                                        if success:
                                            st.toast("저장완료!", icon="✅")
                                        else:
                                            st.toast("이미 저장됨", icon="ℹ️")
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
        
        for date_str in sorted_dates:
            st.header(f"📅 {date_str}")
            for idx, item in enumerate(scraps[date_str]):
                with st.container(border=True):
                    col_x, col_y = st.columns([0.9, 0.1])
                    with col_x:
                        st.subheader(f"[{item['media']}] {item['title']}")
                        if item['subtitle']:
                            st.write(item['subtitle'])
                        st.markdown(f"[기사 읽기]({item['url']})")
                        st.caption(f"스크랩 시간: {item['scrapped_at']}")
                    with col_y:
                        if st.button("삭제", key=f"del_{date_str}_{idx}"):
                            storage.remove_scrap(date_str, item['url'])
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
