import streamlit as st
import fitz  # PyMuPDF
import os
from PIL import Image
import io

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="나만의 문제집 생성기")

# --- 스타일 커스텀 ---
st.markdown("""
<style>
    .exam-card { background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #eee; margin-bottom: 15px; }
    div[data-testid="stHorizontalBlock"] button { width: 100%; height: 38px; min-height: 38px; padding: 0px !important; font-size: 14px; font-weight: 600; border-radius: 6px; border: 1px solid #d1d5db; margin: 2px 0px; }
    div[data-testid="stHorizontalBlock"] button[kind="primary"] { background-color: #4f8bf9; border-color: #4f8bf9; color: white; }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] { background-color: #ffffff; color: #374151; }
    div[data-testid="stHorizontalBlock"] button:hover { border-color: #4f8bf9; color: #4f8bf9; }
</style>
""", unsafe_allow_html=True)

st.title("📑 나만의 맞춤 문제집 생성기 (LEET 전용)")

# --- 0. 세션 초기화 ---
if 'exam_cart' not in st.session_state: st.session_state.exam_cart = []
if 'selected_questions_map' not in st.session_state: st.session_state.selected_questions_map = {}

def toggle_question(exam_id, q_num):
    current_list = st.session_state.selected_questions_map.get(exam_id, [])
    if q_num in current_list: current_list.remove(q_num)
    else: current_list.append(q_num); current_list.sort()
    st.session_state.selected_questions_map[exam_id] = current_list

def get_korean_font_path():
    # [수정됨] 1순위: 사용자가 지정한 대문자 파일명 (MALGUN.TTF)
    if os.path.exists("MALGUN.TTF"): return "MALGUN.TTF"
    
    # 혹시 모를 다른 대소문자 경우의 수 대비
    if os.path.exists("malgun.ttf"): return "malgun.ttf"
    if os.path.exists("Malgun.ttf"): return "Malgun.ttf"
    
    # 2순위: 로컬 윈도우 폰트 (테스트용)
    candidates = ["C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/gulim.ttf", "C:/Windows/Fonts/batang.ttf", "C:/Windows/Fonts/NanumGothic.ttf"]
    for path in candidates:
        if os.path.exists(path): return path
    return None

# --- 1. 사이드바 ---
with st.sidebar:
    st.header("1️⃣ 시험지 추가")
    with st.expander("시험 정보 입력", expanded=True):
        # 연도 선택 (2017 ~ 2026)
        input_year = st.selectbox("연도", range(2017, 2027))
        
        # 고정값 처리
        st.info(f"시험: LEET\n과목: 추리논증\n책형: 홀수형")
        input_type = "LEET"
        input_subject = "추리논증"
        input_book = "홀수형"
        
        # 문항 수 설정 (2017, 2018년은 35문제, 나머지는 40문제)
        if input_year in [2017, 2018]:
            max_q_count = 35
        else:
            max_q_count = 40
            
        folder_name = f"{input_year}_{input_type}_{input_subject}_{input_book}"
        full_path = f"output/{folder_name}"
        
        if st.button("➕ 목록에 추가", type="primary", use_container_width=True):
            if os.path.exists(full_path):
                if folder_name not in [e['id'] for e in st.session_state.exam_cart]:
                    st.session_state.exam_cart.append({
                        'id': folder_name,
                        'title': f"{input_year} {input_type}",
                        'sub': f"{input_subject} ({input_book})",
                        'full_title': f"{input_year} {input_type} {input_subject} {input_book}",
                        'path': full_path,
                        'max_q': max_q_count
                    })
                    st.session_state.selected_questions_map[folder_name] = []
                    st.rerun()
                else:
                    st.toast("이미 추가된 시험지입니다.")
            else:
                st.error(f"폴더 없음: {folder_name}\n(깃허브 output 폴더를 확인하세요)")

    st.markdown("---")
    st.subheader("📊 선택 현황")
    total_q = sum([len(q) for q in st.session_state.selected_questions_map.values()])
    st.metric("총 문항 수", f"{total_q} 문제")

# --- 2. 메인 화면 ---
st.header("2️⃣ 문항 선택")

if not st.session_state.exam_cart:
    st.info("👈 왼쪽 사이드바에서 시험지를 추가해주세요.")
else:
    cols_layout = st.columns(2)
    for idx, exam in enumerate(st.session_state.exam_cart):
        col_idx = idx % 2
        with cols_layout[col_idx]:
            with st.container(border=True):
                c1, c2 = st.columns([8, 1])
                with c1:
                    st.subheader(exam['title'])
                    st.caption(f"{exam['sub']} - 총 {exam['max_q']}문항")
                with c2:
                    if st.button("✕", key=f"del_{exam['id']}", help="삭제"):
                        st.session_state.exam_cart.pop(idx)
                        del st.session_state.selected_questions_map[exam['id']]
                        st.rerun()
                
                selected_list = st.session_state.selected_questions_map.get(exam['id'], [])
                current_max_q = exam.get('max_q', 40)
                
                cols_per_row = 8
                rows_needed = (current_max_q + cols_per_row - 1) // cols_per_row
                
                for r in range(rows_needed):
                    cols = st.columns(cols_per_row)
                    for c in range(cols_per_row):
                        q_num = r * cols_per_row + c + 1
                        
                        if q_num <= current_max_q:
                            with cols[c]:
                                is_sel = q_num in selected_list
                                st.button(f"{q_num}", key=f"btn_{exam['id']}_{q_num}", type="primary" if is_sel else "secondary", on_click=toggle_question, args=(exam['id'], q_num), use_container_width=True)
                
                if selected_list: st.caption(f"✅ {len(selected_list)}개 선택됨")
                else: st.caption("선택 없음")

    st.divider()

    # --- 3. 생성 옵션 ---
    st.header("3️⃣ 문제집 만들기")
    
    st.markdown("##### ⚙️ 기본 설정")
    col_set1, col_set2 = st.columns(2)
        
    with col_set1:
        show_source = st.toggle("상단 출처 표시", value=True)
        compress_img = st.toggle("용량 최적화 (JPEG)", value=True)
        
    with col_set2:
        auto_font = get_korean_font_path()
        final_font_path = None
        if auto_font:
            st.caption(f"폰트: {os.path.basename(auto_font)}")
            final_font_path = auto_font
        else:
            custom_font_file = st.file_uploader("폰트(TTF) 필요", type="ttf")
            if custom_font_file:
                with open("custom_font.ttf", "wb") as f: f.write(custom_font_file.getbuffer())
                final_font_path = "custom_font.ttf"

    if total_q > 0:
        if st.button(f"🚀 총 {total_q}문제 PDF 생성하기", type="primary", use_container_width=True):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # PDF 규격 (A3)
            PT_PER_MM = 2.83465
            PAGE_W = 297.0 * PT_PER_MM
            PAGE_H = 420.0 * PT_PER_MM
            MARGIN = 20 * PT_PER_MM
            COL_GAP = 12 * PT_PER_MM
            COL_W = (PAGE_W - (2 * MARGIN) - COL_GAP) / 2
            
            # [고정 설정값]
            FIXED_NUM_POS_X_MM = 0   
            FIXED_NUM_POS_Y_MM = 1   
            FIXED_FONT_SIZE = 13     
            
            NUM_X_PT = FIXED_NUM_POS_X_MM * PT_PER_MM
            NUM_Y_PT = FIXED_NUM_POS_Y_MM * PT_PER_MM
            
            HEADER_H_PT = 20 if show_source else 0
            
            FIXED_MASK_W = 19
            FIXED_MASK_H = 20
            
            doc = fitz.open()
            
            def add_page():
                p = doc.new_page(width=PAGE_W, height=PAGE_H)
                center = PAGE_W / 2
                shape = p.new_shape()
                shape.draw_line((center, MARGIN), (center, PAGE_H - MARGIN))
                shape.finish(color=(0.8, 0.8, 0.8), width=0.5)
                shape.commit()
                return p

            curr_page = add_page()
            y_left, y_right = MARGIN, MARGIN
            new_q_num, proc_cnt = 1, 0
            
            fontname_alias = "my_font"
            
            for exam in st.session_state.exam_cart:
                target_qs = sorted(st.session_state.selected_questions_map[exam['id']])
                
                for q_orig in target_qs:
                    status_text.text(f"작업 중... {new_q_num}번 문항")
                    
                    # JPG 파일 로드
                    img_path = f"{exam['path']}/{q_orig:02d}.jpg"
                    
                    if os.path.exists(img_path):
                        with Image.open(img_path) as pil_img:
                            src_w, src_h = pil_img.size
                            
                            scale = COL_W / src_w
                            img_h = src_h * scale
                            total_h = HEADER_H_PT + img_h
                            
                            if y_left + total_h <= PAGE_H - MARGIN:
                                cx, cy = MARGIN, y_left
                                y_left += total_h + 20
                            elif y_right + total_h <= PAGE_H - MARGIN:
                                cx, cy = MARGIN + COL_W + COL_GAP, y_right
                                y_right += total_h + 20
                            else:
                                curr_page = add_page()
                                y_left, y_right = MARGIN, MARGIN
                                cx, cy = MARGIN, y_left
                                y_left += total_h + 20
                            
                            # [1] 출처
                            img_start_y = cy
                            if show_source:
                                header_txt = f"{exam['full_title']} {q_orig}번"
                                text_pt = (cx, cy + 12)
                                if final_font_path:
                                    curr_page.insert_text(text_pt, header_txt, fontname=fontname_alias, fontfile=final_font_path, fontsize=9, color=(0.4, 0.4, 0.4))
                                else:
                                    curr_page.insert_text(text_pt, header_txt, fontsize=9, color=(0.4, 0.4, 0.4))
                                img_start_y += HEADER_H_PT

                            # [2] 이미지
                            rect = fitz.Rect(cx, img_start_y, cx + COL_W, img_start_y + img_h)
                            if compress_img:
                                img_byte_arr = io.BytesIO()
                                pil_img.convert('RGB').save(img_byte_arr, format='JPEG', quality=85)
                                curr_page.insert_image(rect, stream=img_byte_arr.getvalue())
                            else:
                                curr_page.insert_image(rect, filename=img_path)
                            
                            # [3] 지우개
                            shape = curr_page.new_shape()
                            shape.draw_rect(fitz.Rect(cx, img_start_y, cx + FIXED_MASK_W, img_start_y + FIXED_MASK_H))
                            shape.finish(color=(1, 1, 1), fill=(1, 1, 1), width=0)
                            shape.commit()

                            # [4] 새 번호 (겹쳐쓰기)
                            num_pt = (cx + NUM_X_PT, img_start_y + NUM_Y_PT + FIXED_FONT_SIZE)
                            num_str = f"{new_q_num}."
                            
                            if final_font_path:
                                curr_page.insert_text(num_pt, num_str, fontname=fontname_alias, fontfile=final_font_path, fontsize=FIXED_FONT_SIZE, color=(0,0,0))
                                curr_page.insert_text((num_pt[0] + 0.7, num_pt[1]), num_str, fontname=fontname_alias, fontfile=final_font_path, fontsize=FIXED_FONT_SIZE, color=(0,0,0))
                            else:
                                curr_page.insert_text(num_pt, num_str, fontsize=FIXED_FONT_SIZE, color=(0,0,0))
                                curr_page.insert_text((num_pt[0] + 0.7, num_pt[1]), num_str, fontsize=FIXED_FONT_SIZE, color=(0,0,0))

                            new_q_num += 1
                    
                    proc_cnt += 1
                    progress_bar.progress(proc_cnt / total_q)
            
            out_name = "나만의_문제집_완성.pdf"
            doc.save(out_name, garbage=4, deflate=True)
            doc.close()
            
            st.success("완료!")
            with open(out_name, "rb") as f:
                st.download_button("📥 다운로드", f, file_name=out_name, mime="application/pdf", use_container_width=True)
    else:
        st.warning("문제를 선택해주세요.")