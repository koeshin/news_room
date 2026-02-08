import streamlit as st
import asyncio
from datetime import datetime, timedelta
import scraper
import storage
import analysis
import time
import threading
import json

# 페이지 설정
st.set_page_config(page_title="나의 뉴스룸", layout="wide")

# 사이드바 메뉴
menu = st.sidebar.selectbox("메뉴 선택", ["뉴스룸", "스크랩 북", "환경 설정"])

# 사이드바: 키워드 필터 (Feature 1)
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 키워드 필터")
keyword_filter = st.sidebar.text_input("키워드 입력", placeholder="예: 삼성, AI, 경제")
if keyword_filter:
    st.sidebar.caption(f"🏷️ 필터 적용 중: **{keyword_filter}**")

# 세션 상태 초기화 (데이터 캐싱용)
if "news_data" not in st.session_state:
    st.session_state.news_data = {}

# 백그라운드 스크래핑 상태
if "bg_scraping_started" not in st.session_state:
    st.session_state.bg_scraping_started = False
if "bg_scraping_date" not in st.session_state:
    st.session_state.bg_scraping_date = None

# 스크랩 상태 캐싱 (UI 반응 속도 향상용)
if "scrapped_urls" not in st.session_state:
    st.session_state.scrapped_urls = set()
    # 초기 로드 시 한 번 채워넣기
    all_scraps = storage.load_scraps()
    for date_key in all_scraps:
        for s in all_scraps[date_key]:
            st.session_state.scrapped_urls.add(s['url'])

def background_scrape_all(media_list, date_str, exclude_oid=None):
    """백그라운드에서 모든 언론사 스크래핑"""
    for media in media_list:
        if media['oid'] == exclude_oid:
            continue
        # 캐시 확인 후 없으면 스크래핑
        if not storage.load_news_cache(date_str, media['oid']):
            try:
                asyncio.run(scraper.get_newspaper_data(media['oid'], date_str))
                print(f"[BG] {media['name']} 스크래핑 완료")
            except Exception as e:
                print(f"[BG] {media['name']} 스크래핑 실패: {e}")

def get_today():
    return datetime.now()

def is_sunday():
    return datetime.now().weekday() == 6

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
        # 기본값을 오늘로 설정
        selected_date = st.date_input("날짜 선택", get_today())
    
    # 일요일인 경우 특별 처리
    if is_sunday() and selected_date.strftime("%Y-%m-%d") == format_date_display(get_today()):
        st.info("📰 일요일에는 신문이 발행되지 않습니다.")
        
        st.markdown("---")
        st.subheader("📊 주간 리포트")
        st.write("이번 주 스크랩한 기사들을 AI가 분석한 주간 리포트를 생성하시겠습니까?")
        
        if st.button("✨ 주간 리포트 생성하기", type="primary", use_container_width=True):
            with st.spinner("Gemini가 이번 주 스크랩 기사를 분석 중입니다... (약 10~20초 소요)"):
                weekly_scraps = storage.get_weekly_scraps()
                if weekly_scraps:
                    report = analysis.generate_weekly_report(weekly_scraps)
                    st.markdown("### 📋 이번 주 뉴스 리포트")
                    st.markdown(report)
                else:
                    st.warning("이번 주에 스크랩한 기사가 없습니다.")
        
        st.markdown("---")
        st.caption("💡 Tip: 다른 날짜를 선택하여 지난 신문을 확인할 수 있습니다.")
    else:
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
        
        # 백그라운드 스크래핑 시작 (첫 번째 언론사 로드 후)
        if not st.session_state.bg_scraping_started or st.session_state.bg_scraping_date != date_str:
            st.session_state.bg_scraping_started = True
            st.session_state.bg_scraping_date = date_str
            thread = threading.Thread(
                target=background_scrape_all,
                args=(media_list, date_str, oid),
                daemon=True
            )
            thread.start()
            st.toast("🔄 백그라운드에서 다른 언론사 스크래핑 시작...", icon="⏳")
                
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
            # 섹션별로 페이지 그룹화 (A, B, E, S 등)
            import re
            from collections import defaultdict
            
            section_pages = defaultdict(list)
            for page_data in display_data:
                page_name = page_data['page']
                # 섹션 추출 (A, B, E 등)
                section_match = re.search(r'^([A-Z]+)', page_name)
                if section_match:
                    section = section_match.group(1)
                    section_pages[section].append(page_data)
            
            # 각 섹션 내에서 페이지 번호로 정렬
            def sort_key_number(page_dict):
                p = page_dict['page']
                match = re.search(r'(\d+)', p)
                if match:
                    return int(match.group(1))
                return 999
            
            for section in section_pages:
                section_pages[section].sort(key=sort_key_number)
            
            # 섹션을 알파벳 순으로 정렬
            sorted_sections = sorted(section_pages.keys())
            
            # 각 섹션을 페이지 번호 범위로 나누기 (1-10, 11-20, 21-30, ...)
            section_chunks = []
            
            for section in sorted_sections:
                pages_in_section = section_pages[section]
                
                # 페이지 번호 범위별로 그룹화
                range_groups = defaultdict(list)
                for page_data in pages_in_section:
                    page_num = sort_key_number(page_data)
                    # 페이지 번호를 10 단위로 그룹화 (1-10=0, 11-20=1, 21-30=2, ...)
                    range_idx = (page_num - 1) // 10
                    range_groups[range_idx].append(page_data)
                
                # 각 범위 그룹을 청크로 변환
                for range_idx in sorted(range_groups.keys()):
                    chunk_pages = range_groups[range_idx]
                    
                    # 실제 시작/끝 페이지 번호
                    start_num = sort_key_number(chunk_pages[0])
                    end_num = sort_key_number(chunk_pages[-1])
                    
                    # 범위 레이블 (1-10, 11-20, 21-30, ...)
                    range_start = range_idx * 10 + 1
                    range_end = (range_idx + 1) * 10
                    
                    chunk_size = len(chunk_pages)
                    
                    section_chunks.append({
                        'section': section,
                        'start': start_num,
                        'end': end_num,
                        'pages': chunk_pages,
                        'label': f"{section}{range_start}-{range_end}",
                        'size': chunk_size
                    })
            
            # 세션 상태에 선택된 섹션 청크 저장
            selected_chunk_key = f"selected_chunk_{cache_key}"
            if selected_chunk_key not in st.session_state:
                st.session_state[selected_chunk_key] = 0
            
            # 청크 선택 버튼들
            if len(section_chunks) > 1:
                st.markdown("### 📑 면 선택")
                
                # 버튼을 5개씩 나눠서 표시
                buttons_per_row = 5
                for row_start in range(0, len(section_chunks), buttons_per_row):
                    row_chunks = section_chunks[row_start:row_start + buttons_per_row]
                    cols = st.columns(len(row_chunks))
                    
                    for col_idx, chunk in enumerate(row_chunks):
                        chunk_idx = row_start + col_idx
                        with cols[col_idx]:
                            # 현재 선택된 청크인지 확인
                            is_selected = st.session_state[selected_chunk_key] == chunk_idx
                            button_type = "primary" if is_selected else "secondary"
                            
                            if st.button(
                                chunk['label'],
                                key=f"chunk_btn_{cache_key}_{chunk_idx}",
                                type=button_type,
                                use_container_width=True
                            ):
                                st.session_state[selected_chunk_key] = chunk_idx
                                st.rerun()
                
                st.divider()
            
            # 선택된 청크의 페이지만 표시
            selected_chunk_idx = st.session_state[selected_chunk_key]
            if selected_chunk_idx < len(section_chunks):
                current_chunk = section_chunks[selected_chunk_idx]
                current_pages = current_chunk['pages']
                
                # 전체 면 리스트를 2개씩 묶어서 처리
                cols_per_row = 2
                
                for i in range(0, len(current_pages), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j in range(cols_per_row):
                        if i + j < len(current_pages):
                            page = current_pages[i + j]
                            with cols[j]:
                                with st.container(border=True):
                                    st.markdown(f"#### 📍 {page['page']}")
                                    
                                    # 키워드 필터 적용
                                    filtered_articles = page['articles']
                                    if keyword_filter:
                                        keywords = [k.strip() for k in keyword_filter.split(',')]
                                        filtered_articles = [
                                            art for art in page['articles']
                                            if any(kw.lower() in art['title'].lower() or kw.lower() in (art.get('subtitle') or '').lower() for kw in keywords)
                                        ]
                                    
                                    if not filtered_articles and keyword_filter:
                                        st.caption("필터 결과 없음")
                                    
                                    for idx, art in enumerate(filtered_articles):
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
                                            # 스크랩 버튼 (Popover)
                                            is_scrapped = art['url'] in st.session_state.scrapped_urls
                                            
                                            if is_scrapped:
                                                # 이미 스크랩된 경우 바로 삭제 버튼
                                                if st.button("★", key=f"scr_{cache_key}_{page['page']}_{idx}", help="스크랩 해제"):
                                                    storage.toggle_scrap(format_date_display(selected_date), selected_media, art)
                                                    st.session_state.scrapped_urls.discard(art['url'])
                                                    st.toast("삭제됨!", icon="🗑️")
                                                    st.rerun()
                                            else:
                                                # 스크랩 추가 - Popover 사용
                                                with st.popover("☆", use_container_width=False):
                                                    st.write("📁 폴더 선택")
                                                    
                                                    folder_list = storage.get_folder_list()
                                                    if not folder_list:
                                                        folder_list = ["기본"]
                                                    
                                                    selected_folder = st.selectbox(
                                                        "폴더",
                                                        folder_list,
                                                        label_visibility="collapsed",
                                                        key=f"folder_select_{cache_key}_{page['page']}_{idx}"
                                                    )
                                                    
                                                    if st.button("💾 저장", key=f"save_{cache_key}_{page['page']}_{idx}", type="primary", use_container_width=True):
                                                        storage.toggle_scrap(
                                                            format_date_display(selected_date),
                                                            selected_media,
                                                            art,
                                                            folder=selected_folder
                                                        )
                                                        st.session_state.scrapped_urls.add(art['url'])
                                                        st.toast(f"'{selected_folder}' 폴더에 저장!", icon="✅")
                                                        st.rerun()
                                        st.divider()

# 2. 스크랩 북 화면
elif menu == "스크랩 북":
    st.title("📑 스크랩 북")
    
    scraps = storage.load_scraps()
    
    if not scraps:
        st.info("저장된 스크랩이 없습니다. 뉴스룸에서 마음에 드는 기사를 스크랩해 보세요!")
    else:
        # 폴더 필터 (Feature 3)
        folder_list = storage.get_folder_list()
        col_folder, col_new_folder = st.columns([3, 1])
        with col_folder:
            selected_folder = st.selectbox("📁 폴더 선택", ["전체"] + folder_list)
        with col_new_folder:
            new_folder = st.text_input("새 폴더", placeholder="폴더명")
            if new_folder and st.button("추가"):
                storage.add_folder(new_folder)
                st.rerun()
        
        # 폴더별 필터링
        if selected_folder == "전체":
            filtered_scraps = scraps
        else:
            filtered_scraps = storage.get_scraps_by_folder(selected_folder)
        
        # 날짜별 역순 정렬
        sorted_dates = sorted(filtered_scraps.keys(), reverse=True) if filtered_scraps else []
        
        # 내보내기 버튼 (Feature 6)
        col_export, col_count = st.columns([1, 3])
        with col_export:
            if st.button("📝 마크다운 내보내기"):
                filename = f"scrap_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                storage.export_scraps_to_markdown(filtered_scraps, filename)
                st.success(f"✅ {filename} 저장 완료!")
        with col_count:
            total_count = sum(len(items) for items in filtered_scraps.values())
            st.caption(f"📊 총 {total_count}개 기사")
        

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
            if date_str not in filtered_scraps:
                continue
            st.header(f"📅 {date_str}")
            for idx, item in enumerate(filtered_scraps[date_str]):
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
    
    # 기존 언론사 코드 목록에서 선택
    try:
        with open("naver_media_codes.json", "r", encoding="utf-8") as f:
            media_codes = json.load(f)
        available_media = media_codes.get("flat_list", [])
        
        # 이미 추가된 OID 제외
        existing_oids = {m['oid'] for m in settings['media_list']}
        available_media = [m for m in available_media if m['oid'] not in existing_oids]
        
        if available_media:
            # 카테고리별로 그룹화하여 표시
            media_options = [f"{m['name']} ({m['category']})" for m in available_media]
            selected_idx = st.selectbox(
                "추가할 언론사 선택",
                range(len(media_options)),
                format_func=lambda x: media_options[x]
            )
            
            if st.button("➕ 추가하기", type="primary"):
                selected_media = available_media[selected_idx]
                settings['media_list'].append({
                    "name": selected_media['name'],
                    "oid": selected_media['oid']
                })
                storage.save_settings(settings)
                st.success(f"{selected_media['name']}이(가) 추가되었습니다!")
                st.rerun()
        else:
            st.info("✅ 모든 언론사가 이미 추가되어 있습니다.")
            
    except FileNotFoundError:
        st.error("naver_media_codes.json 파일을 찾을 수 없습니다.")
