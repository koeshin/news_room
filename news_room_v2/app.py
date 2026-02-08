import streamlit as st
import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
import storage

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Feedback file
FEEDBACK_FILE = os.path.join(SCRIPT_DIR, "data", "user_feedback.json")

# Page Config
st.set_page_config(page_title="News Room v2", layout="wide")

# Sidebar Menu (Removed Icons)
menu = st.sidebar.radio("메뉴", ["뉴스룸", "AI 추천 (20대)", "스크랩북", "설정"])

# Sidebar: Keyword Filter
st.sidebar.markdown("---")
st.sidebar.subheader("키워드 필터")
keyword_filter = st.sidebar.text_input("키워드 입력", placeholder="예: 삼성, AI, 경제")
if keyword_filter:
    st.sidebar.caption(f"🔍 필터 적용: **{keyword_filter}**")

# Session State Init
if "news_data" not in st.session_state:
    st.session_state.news_data = {}
if "scrapped_urls" not in st.session_state:
    st.session_state.scrapped_urls = set()
    all_scraps = storage.load_scraps()
    for date_key in all_scraps:
        for s in all_scraps[date_key]:
            st.session_state.scrapped_urls.add(s['url'])

# --- Helper Functions ---
def get_today():
    return datetime.now()

def format_date_display(date_obj):
    return date_obj.strftime("%Y-%m-%d")

def format_date_param(date_obj):
    return date_obj.strftime("%Y%m%d")

def load_recommendations():
    rec_file = os.path.join(SCRIPT_DIR, "data", "loop_output.json")
    if os.path.exists(rec_file):
        with open(rec_file, 'r') as f:
            return json.load(f)
    return []

def get_20s_recommendations(all_recs):
    return [r for r in all_recs if r.get("persona") == "20s"]

def sort_key_number(page_dict):
    p = page_dict.get('page', '999')
    match = re.search(r'(\d+)', str(p))
    if match: return int(match.group(1))
    return 999

def save_user_feedback(article, score):
    """Save user rating to JSON."""
    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "article_id": article.get("id", article.get("url")), # Fallback ID
        "title": article.get("title"),
        "media": article.get("media"),
        "score": score,
        "full_text": article.get("full_text", "")
    }
    
    feedbacks = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            try: feedbacks = json.load(f)
            except: pass
            
    feedbacks.append(feedback_entry)
    
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=2)

# --- 1. 뉴스룸 화면 ---
if menu == "뉴스룸":
    st.title("📰 뉴스룸")
    
    settings = storage.load_settings()
    media_list = settings.get("media_list", [])
    
    col1, col2 = st.columns([1, 1])
    with col1:
        selected_media_name = st.selectbox("언론사 선택", [m['name'] for m in media_list])
    with col2:
        selected_date = st.date_input("날짜 선택", get_today())
    
    selected_media = next((m for m in media_list if m['name'] == selected_media_name), None)
    if not selected_media:
        st.error("언론사 정보를 찾을 수 없습니다.")
        st.stop()
        
    oid = selected_media['oid']
    date_str = format_date_param(selected_date)
    cache_key = f"{oid}_{date_str}"
    
    if st.button("🔄 뉴스 새로고침", use_container_width=True):
        if cache_key in st.session_state.news_data:
            del st.session_state.news_data[cache_key]
        st.rerun()

    if cache_key not in st.session_state.news_data:
        data = storage.load_news_data(date_str, oid)
        st.session_state.news_data[cache_key] = data
        
    display_data = st.session_state.news_data.get(cache_key)
    
    if not display_data:
        st.info("해당 날짜의 데이터가 없습니다.")
    else:
        # Group by Page
        pages_map = defaultdict(list)
        for article in display_data:
            p = article.get('page', '기타')
            pages_map[p].append(article)
        
        page_data_list = [{'page': p, 'articles': arts} for p, arts in pages_map.items()]
        
        # Group by Section
        section_pages = defaultdict(list)
        for page_data in page_data_list:
            page_name = page_data['page']
            section_match = re.search(r'^([A-Z]+)', str(page_name))
            if section_match:
                section = section_match.group(1)
                section_pages[section].append(page_data)
        
        # Sort
        for section in section_pages:
            section_pages[section].sort(key=sort_key_number)
            
        sorted_sections = sorted(section_pages.keys())
        
        # Pagination
        section_chunks = []
        for section in sorted_sections:
            pages_in_section = section_pages[section]
            range_groups = defaultdict(list)
            for page_data in pages_in_section:
                page_num = sort_key_number(page_data)
                range_idx = (page_num - 1) // 10
                range_groups[range_idx].append(page_data)
            
            for range_idx in sorted(range_groups.keys()):
                chunk_pages = range_groups[range_idx]
                start_num = sort_key_number(chunk_pages[0])
                end_num = sort_key_number(chunk_pages[-1])
                range_start = range_idx * 10 + 1
                range_end = (range_idx + 1) * 10
                
                section_chunks.append({
                    'label': f"{section}{range_start}-{range_end}면",
                    'chunk_idx': len(section_chunks),
                    'pages': chunk_pages
                })
        
        # Chunk Selection (Centered & Larger)
        selected_chunk_key = f"selected_chunk_{cache_key}"
        if selected_chunk_key not in st.session_state:
            st.session_state[selected_chunk_key] = 0
            
        if len(section_chunks) > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            # Centering using columns
            c_spacer1, c_main, c_spacer2 = st.columns([0.1, 0.8, 0.1])
            with c_main:
                st.markdown("### 📰 지면 선택")
                cols = st.columns(4) # 4 buttons per row for larger size
                for i, chunk in enumerate(section_chunks):
                    row_idx = i // 4
                    col_idx = i % 4
                    # If new row needed, we can't easily dynamically break lines in st.columns loop 
                    # efficiently without pre-calculation. 
                    # Simpler approach: Iterate logic
                    pass

                # Pre-calculate rows
                rows = [section_chunks[i:i + 4] for i in range(0, len(section_chunks), 4)]
                for row_chunks in rows:
                    cols = st.columns(4)
                    for idx, chunk in enumerate(row_chunks):
                        with cols[idx]:
                            is_selected = st.session_state[selected_chunk_key] == chunk['chunk_idx']
                            if st.button(chunk['label'], key=f"chunk_{chunk['chunk_idx']}", type="primary" if is_selected else "secondary", use_container_width=True):
                                st.session_state[selected_chunk_key] = chunk['chunk_idx']
                                st.rerun()
            st.divider()

        # Display Pages
        selected_chunk_idx = st.session_state[selected_chunk_key]
        if selected_chunk_idx < len(section_chunks):
            current_pages = section_chunks[selected_chunk_idx]['pages']
            
            cols_per_row = 2
            for i in range(0, len(current_pages), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(current_pages):
                        page = current_pages[i+j]
                        with cols[j]:
                            with st.container(border=True):
                                st.markdown(f"#### {page['page']}")
                                
                                articles_to_show = page['articles']
                                if keyword_filter:
                                    keywords = [k.strip() for k in keyword_filter.split(',')]
                                    articles_to_show = [a for a in articles_to_show if any(k.lower() in a.get('title','').lower() for k in keywords)]
                                
                                # Import at top or here (already imported in Recs tab, but safe to import again or move to top)
                                from tracking_component import news_tracker
                                
                                # Prepare Data
                                tracker_data = []
                                for art in articles_to_show:
                                    url = art.get('url', '#')
                                    is_scrapped = url in st.session_state.scrapped_urls
                                    tracker_data.append({
                                        "id": url, # Use URL as ID
                                        "title": art.get('title', '제목 없음'),
                                        "media": selected_media_name,
                                        "summary": art.get('subtitle', ''),
                                        "url": url,
                                        "score": 0, # No score in general news
                                        "is_action_done": is_scrapped
                                    })

                                # Render Component
                                # Render Component
                                # Use unique key using Processed Page Name
                                safe_page_key = str(page['page']).replace(" ", "_")
                                event_dict = news_tracker(
                                    tracker_data, 
                                    action_label="저장 💾", 
                                    show_score=False, 
                                    show_remove=False, 
                                    key=f"news_tracker_{selected_chunk_idx}_{safe_page_key}"
                                )

                                if event_dict:
                                    event_type = event_dict.get("event")
                                    target_id = event_dict.get("target_id") # URL
                                    
                                    # Log Behavior
                                    if event_type in ["hover", "click"]:
                                        log_entry = {
                                            "timestamp": event_dict.get("timestamp"),
                                            "user": "default", 
                                            "page": "News Room",
                                            "event": event_type,
                                            "target_id": target_id,
                                            "duration_ms": event_dict.get("duration_ms"),
                                            "url": event_dict.get("url")
                                        }
                                        with open(os.path.join(SCRIPT_DIR, "data", "user_behavior_logs.jsonl"), "a", encoding="utf-8") as f:
                                            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                                            
                                    # Handle Save/Unsave (Action)
                                    if event_type == "action_request":
                                        # Find original article object to save
                                        target_art = next((a for a in articles_to_show if a.get('url') == target_id), None)
                                        if target_art:
                                            # Toggle Scrap
                                            if target_id in st.session_state.scrapped_urls:
                                                storage.toggle_scrap(format_date_display(selected_date), selected_media_name, target_art)
                                                st.session_state.scrapped_urls.discard(target_id)
                                            else:
                                                storage.toggle_scrap(format_date_display(selected_date), selected_media_name, target_art)
                                                st.session_state.scrapped_urls.add(target_id)
                                            st.rerun()

# --- 2. Recommendations ---
elif menu == "AI 추천 (20대)":
    st.title("🎯 AI 맞춤 추천 (20대)")
    st.caption("사용자의 관심사를 분석하여 선별된 뉴스입니다.")
    
    # Import Tracker
    from tracking_component import news_tracker
    
    recommendations = load_recommendations()
    recs_20s = get_20s_recommendations(recommendations)
    
    # Hidden Recommendations
    if "hidden_recs" not in st.session_state:
        st.session_state.hidden_recs = set()
        
    # Filter out hidden
    visible_recs = [r for r in recs_20s if r.get('id') not in st.session_state.hidden_recs]
    
    if not visible_recs:
        if recs_20s:
            st.info("모든 추천 기사를 숨겼습니다.")
        else:
            st.warning("아직 추천 데이터가 없습니다. 분석이 완료될 때까지 기다려 주세요.")
    else:
        st.success(f"오늘의 추천 뉴스 {len(visible_recs)}건을 찾았습니다!")
        
        # Prepare Data for Component
        tracker_data = []
        for i, rec in enumerate(visible_recs[:20], 1):
            feedback_key = f"rated_{rec.get('id', i)}"
            is_rated = st.session_state.get(feedback_key, False)
            
            tracker_data.append({
                "id": rec.get('id'),
                "title": rec.get('title'),
                "media": rec.get('media'),
                "summary": (rec.get('summary', '')[0] if isinstance(rec.get('summary'), list) else rec.get('summary', ''))[:100],
                "url": rec.get('id') if rec.get('id', '').startswith('http') else '#',
                "score": rec.get('score', 0),
                "is_action_done": is_rated
            })
            
        # RENDER COMPONENT
        event_dict = news_tracker(tracker_data, action_label="평가 ⭐", key="rec_tracker")
        
        # Handle Events
        if event_dict:
            event_type = event_dict.get("event")
            target_id = event_dict.get("target_id")
            
            # Log Behavior
            if event_type in ["hover", "click"]:
                log_entry = {
                    "timestamp": event_dict.get("timestamp"),
                    "user": "default", 
                    "page": "Recommendations",
                    "event": event_type,
                    "target_id": target_id,
                    "duration_ms": event_dict.get("duration_ms"),
                    "url": event_dict.get("url")
                }
                # Append to log file
                with open(os.path.join(SCRIPT_DIR, "user_behavior_logs.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                    
            # Handle Interaction
            if event_type == "action_request":
                st.session_state["rating_target"] = target_id
                st.rerun()
                
            if event_type == "remove_request":
                st.session_state.hidden_recs.add(target_id)
                
                # Log Removal
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "user": "default", 
                    "page": "Recommendations",
                    "event": "remove",
                    "target_id": target_id,
                    "url": target_id # URL is ID
                }
                with open(os.path.join(SCRIPT_DIR, "data", "user_behavior_logs.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
                st.toast("기사가 추천 목록에서 제외되었습니다.")
                st.rerun()

        # Check if Rating Modal Needed
        if "rating_target" in st.session_state:
            target_id = st.session_state["rating_target"]
            target_rec = next((r for r in recs_20s if r.get('id') == target_id), None)
            
            if target_rec:
                with st.popover("평가하기 (선택됨)", use_container_width=True):
                    st.write(f"**{target_rec.get('title')}**")
                    rating = st.slider("점수", 1, 5, 3, key=f"rate_modal_{target_id}")
                    if st.button("제출", key=f"sub_modal_{target_id}", type="primary"):
                        save_user_feedback(target_rec, rating)
                        st.session_state[f"rated_{target_id}"] = True
                        del st.session_state["rating_target"]
                        st.rerun()

# --- 3. Scrapbook ---
elif menu == "스크랩북":
    st.title("📂 스크랩북")
    
    scraps = storage.load_scraps()
    if not scraps:
        st.info("아직 저장된 스크랩이 없습니다.")
    else:
        sorted_dates = sorted(scraps.keys(), reverse=True)
        folder_list = storage.get_folder_list()
        selected_folder = st.selectbox("폴더 필터", ["전체"] + folder_list)
        
        for date_str in sorted_dates:
            items = scraps[date_str]
            if selected_folder != "전체":
                items = [i for i in items if i.get('folder', '기본') == selected_folder]
            
            if not items: continue
            
            st.subheader(date_str)
            for idx, item in enumerate(items):
                with st.container(border=True):
                    col_a, col_b = st.columns([0.9, 0.1])
                    with col_a:
                        st.markdown(f"**[{item.get('media','?')}] [{item['title']}]({item['url']})**")
                        if item.get('subtitle'): st.caption(item['subtitle'])
                    with col_b:
                        if st.button("삭제", key=f"del_sc_{date_str}_{idx}"):
                            storage.remove_scrap(date_str, item['url'])
                            st.session_state.scrapped_urls.discard(item['url'])
                            st.rerun()

# --- 4. Settings ---
elif menu == "설정":
    st.title("⚙️ 설정")
    
    settings = storage.load_settings()
    
    st.subheader("언론사 관리")
    for idx, media in enumerate(settings['media_list']):
        c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
        c1.write(media['name'])
        c2.write(media['oid'])
        if c3.button("삭제", key=f"rm_m_{idx}"):
            settings['media_list'].pop(idx)
            storage.save_settings(settings)
            st.rerun()
            
    st.divider()
    
    st.subheader("언론사 추가")
    try:
        with open(storage.NAVER_CODES_FILE, "r", encoding="utf-8") as f:
             codes_data = json.load(f)
             available = codes_data.get('flat_list', [])
             
        existing_oids = {m['oid'] for m in settings['media_list']}
        options = [m for m in available if m['oid'] not in existing_oids]
        
        if options:
            sel_idx = st.selectbox("추가할 언론사", range(len(options)), format_func=lambda x: f"{options[x]['name']} ({options[x]['category']})")
            if st.button("추가"):
                to_add = options[sel_idx]
                settings['media_list'].append({"name": to_add['name'], "oid": to_add['oid']})
                storage.save_settings(settings)
                st.rerun()
        else:
            st.info("모든 언론사가 추가되었습니다.")
            
    except Exception as e:
        st.error(f"언론사 코드를 불러올 수 없습니다: {e}")
