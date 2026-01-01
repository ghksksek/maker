import streamlit as st
import streamlit.components.v1 as components
import fitz  # PyMuPDF
import os
from PIL import Image
import io
import gc
import re
import base64

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="기출 연습서 생성기", initial_sidebar_state="collapsed")

# --- 스타일 커스텀 ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    
    /* 문항 번호 헤더 (회색 음영) */
    .slot-header {
        background-color: #e0e0e0;
        color: #333;
        font-weight: 800;
        border-radius: 8px;
        padding: 8px 0;
        margin-bottom: 10px;
        text-align: center;
        font-size: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* 선택창 가운데 정렬 */
    .stSelectbox div[data-baseweb="select"] div {
        justify-content: center !important;
        text-align: center !important;
    }
    
    /* 삭제 버튼 */
    button[kind="secondary"] {
        padding: 0px 5px !important; border: 1px solid #ffcccc; background-color: #fff5f5; color: #ff4b4b; font-weight: bold;
    }
    button[kind="secondary"]:hover { border-color: #ff4b4b; background-color: #ffcccc; color: #ff0000; }
    
    /* 추가(+) 버튼 스타일 (크게 유지) */
    .big-plus-button > button {
        height: 160px !important;
        border: 4px dashed #4f8bf9 !important;
        background-color: #f0f7ff !important;
        color: #4f8bf9 !important;
        font-size: 50px !important;
        font-weight: 900 !important;
        width: 100%;
        margin-top: 0px; 
    }
    .big-plus-button > button:hover { background-color: #e0efff !important; }
    
    .stFileUploader { margin-bottom: 10px; }
    
    div[data-testid="column"] {
        padding-bottom: 0px;
    }
</style>
""", unsafe_allow_html=True)

# 메인 타이틀
st.title("📑 기출 연습서 생성기")

# 제목과 입력창 사이 여백
st.markdown("<br><br>", unsafe_allow_html=True)

# --- 0. 세션 ---
if 'target_q_count' not in st.session_state: st.session_state.target_q_count = 5 
def increase_q(): st.session_state.target_q_count += 1
def decrease_q():
    if st.session_state.target_q_count > 1: st.session_state.target_q_count -= 1

# --- 기능: 1번 년도 변경 시 전체 적용 ---
def on_y1_change():
    if "y_1" in st.session_state and st.session_state.y_1 != "선택":
        new_year = st.session_state.y_1
        for k in range(2, st.session_state.target_q_count + 1):
            st.session_state[f"y_{k}"] = new_year

# --- 기능: 특정 년도 변경 시 이후 자동 적용 ---
def on_year_change(idx):
    key = f"y_{idx}"
    if key in st.session_state:
        ny = st.session_state[key]
        if ny != "선택":
            for k in range(idx + 1, st.session_state.target_q_count + 1):
                st.session_state[f"y_{k}"] = ny

# --- 1. 데이터 ---
def get_available_exams():
    if not os.path.exists("output"): os.makedirs("output"); return {}
    exams = {}
    folders = [f for f in os.listdir("output") if os.path.isdir(os.path.join("output", f))]
    for folder in folders:
        match = re.match(r"(\d{4})", folder)
        if match: exams[match.group(1)] = folder
    return dict(sorted(exams.items(), reverse=True))

available_exams = get_available_exams()

# --- 자동 다운로드 함수 ---
def auto_download_pdf(file_path, file_name):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        js = f"""
        <script>
            setTimeout(function() {{
                const link = document.createElement('a');
                link.href = 'data:application/pdf;base64,{b64}';
                link.download = '{file_name}';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }}, 500);
        </script>
        """
        components.html(js, height=0)
    except Exception as e:
        st.error(f"다운로드 트리거 오류: {e}")

# --- 2. 설정 UI ---
final_font_path = None
if os.path.exists("MALGUN.TTF"): final_font_path = "MALGUN.TTF"
else:
    candidates = ["malgun.ttf", "Malgun.ttf", "C:/Windows/Fonts/malgun.ttf"]
    for p in candidates: 
        if os.path.exists(p):
            final_font_path = p; break

title_font_path = "SBM.ttf" if os.path.exists("SBM.ttf") else None

# UI 배치
c_title, c_dummy = st.columns([1, 2]) 
with c_title:
    custom_title_input = st.text_input("title", max_chars=12, placeholder="문제집 이름을 입력해주세요.", label_visibility="collapsed")
    custom_title = custom_title_input if custom_title_input else "기출 연습서"

c_tog1, c_tog2, c_dummy2 = st.columns([0.8, 1.2, 2])
with c_tog1:
    show_source = st.toggle("출처 표시", value=True)
with c_tog2:
    one_q_per_row = st.toggle("한 페이지에 한 문항씩 표시", value=False)

# --- 3. 문항 구성 ---
st.divider()
compress_img = True 

if not available_exams:
    st.error("❌ 'output' 폴더에 변환된 시험지가 없습니다.")
else:
    user_selections = {}
    years_list = ["선택"] + list(available_exams.keys())
    cur_cnt = st.session_state.target_q_count
    total_slots = cur_cnt + 1 
    
    for start_idx in range(1, total_slots + 1, 5):
        end_idx = min(start_idx + 4, total_slots)
        with st.container(border=True):
            cols = st.columns(5)
            for i in range(5):
                q_num = start_idx + i
                if q_num > total_slots: break
                with cols[i]:
                    if q_num <= cur_cnt:
                        # 헤더
                        if q_num == cur_cnt:
                            c_txt, c_btn = st.columns([3, 1])
                            with c_txt: st.markdown(f"<div class='slot-header' style='margin:0;'>{q_num}문</div>", unsafe_allow_html=True)
                            with c_btn:
                                if st.button("－", key=f"d_{q_num}", help="삭제"): decrease_q(); st.rerun()
                        else: st.markdown(f"<div class='slot-header'>{q_num}문</div>", unsafe_allow_html=True)
                        
                        # 년도
                        y = st.selectbox(
                            "y", years_list, 
                            key=f"y_{q_num}", 
                            label_visibility="collapsed", 
                            format_func=lambda x: "년도" if x == "선택" else f"{x}년", 
                            on_change=on_year_change,
                            args=(q_num,)
                        )
                        
                        # 번호
                        if y != "선택":
                            mv = 35 if y in ['2017', '2018'] else 40
                            q_options = ["선택"] + [f"{k}번" for k in range(1, mv+1)]
                            
                            n_str = st.selectbox(
                                "n", q_options,
                                index=0,
                                key=f"n_{q_num}",
                                label_visibility="collapsed"
                            )
                            if n_str != "선택":
                                n = int(n_str.replace("번", ""))
                                user_selections[q_num] = (y, n)
                        else:
                            st.selectbox("n", ["번호"], key=f"n_{q_num}", label_visibility="collapsed", disabled=True)
                    else:
                        st.markdown('<div class="big-plus-button">', unsafe_allow_html=True)
                        if st.button("＋", key="add"): increase_q(); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

    # --- 4. PDF 생성 ---
    st.divider()
    valid_count = len(user_selections)
    if st.button(f"🚀 {valid_count}문제 PDF 생성하기", type="primary", use_container_width=True):
        if valid_count == 0:
            st.warning("문제를 선택해주세요.")
        else:
            prog = st.progress(0); stat = st.empty()
            
            PT = 2.83465
            PW = 297.0 * PT
            PH = 420.0 * PT
            
            MARGIN = 20 * PT
            HEADER_H = 18 * PT 
            FOOTER_H = 25 * PT
            COL_GAP = 12 * PT
            COL_W = (PW - (2 * MARGIN) - COL_GAP) / 2
            START_Y = MARGIN + HEADER_H + 10
            
            THEME_COLOR = (0.4, 0.4, 0.4)
            LINE_COLOR = (0.8, 0.8, 0.8)
            
            font_alias = "my_font"; title_alias = "my_title"
            doc = fitz.open()

            def draw_header(page, pg_num, title_text):
                pg_y = MARGIN + 10
                if final_font_path:
                    page.insert_text((MARGIN, pg_y), str(pg_num), fontname=font_alias, fontfile=final_font_path, fontsize=24, color=(0,0,0))
                else:
                    page.insert_text((MARGIN, pg_y), str(pg_num), fontsize=24, color=(0,0,0), fontname="helv")
                
                line_y = MARGIN + HEADER_H
                title_size = 27
                title_y = line_y - 23
                
                use_font = title_font_path if title_font_path else final_font_path
                use_alias = title_alias if title_font_path else font_alias
                
                if use_font:
                    tw = fitz.Font(fontfile=use_font).text_length(title_text, fontsize=title_size)
                    tx = (PW - tw) / 2
                    page.insert_text((tx, title_y), title_text, fontname=use_alias, fontfile=use_font, fontsize=title_size, color=(0,0,0))
                    page.insert_text((tx+0.7, title_y), title_text, fontname=use_alias, fontfile=use_font, fontsize=title_size, color=(0,0,0))
                else:
                    tw = fitz.Font("helv").text_length(title_text, fontsize=title_size)
                    tx = (PW - tw) / 2
                    page.insert_text((tx, title_y), title_text, fontsize=title_size, color=(0,0,0))

                btxt = "신성우의 로직트리 제공"
                if final_font_path: calc_font = fitz.Font(fontfile=final_font_path)
                else: calc_font = fitz.Font("helv")
                
                box_font_size = 11
                text_width = calc_font.text_length(btxt, fontsize=box_font_size)
                bx = PW - MARGIN - text_width
                by = line_y - 7
                
                if final_font_path:
                    page.insert_text((bx, by), btxt, fontname=font_alias, fontfile=final_font_path, fontsize=box_font_size, color=THEME_COLOR)
                    page.insert_text((bx+0.3, by), btxt, fontname=font_alias, fontfile=final_font_path, fontsize=box_font_size, color=THEME_COLOR)
                else:
                    page.insert_text((bx, by), btxt, fontsize=box_font_size, color=THEME_COLOR)
                
                page.draw_line((MARGIN, line_y), (PW - MARGIN, line_y), color=LINE_COLOR, width=1.5)

            def add_page(n):
                p = doc.new_page(width=PW, height=PH)
                draw_header(p, n, custom_title)
                c = PW / 2
                p.draw_line((c, START_Y), (c, PH - FOOTER_H), color=LINE_COLOR, width=0.5)
                return p

            pg_cnt = 1
            curr_page = add_page(pg_cnt)
            yl, yr = START_Y, START_Y
            
            p_idx = 0
            for i in range(1, cur_cnt + 1):
                if i not in user_selections: continue
                y, sn = user_selections[i]
                f = available_exams[y]
                stat.text(f"처리 중... {i}문")
                
                ip = f"output/{f}/{sn:02d}.jpg"
                if os.path.exists(ip):
                    with Image.open(ip) as pim:
                        sw, sh = pim.size
                        sc = COL_W / sw
                        ih = sh * sc
                        
                        # [수정] 한 줄 표시를 위해 높이 복구 (35 -> 20)
                        hh = 20 if show_source else 0 
                        th = hh + ih
                        lim = PH - FOOTER_H - 5 
                        
                        fits_l = (yl + th <= lim)
                        fits_r = (yr + th <= lim)
                        col = None
                        
                        # 한 페이지에 한 문항씩 표시
                        if one_q_per_row:
                            if yl + th <= lim:
                                col = 'l'
                            else:
                                if yl == START_Y: col = 'l'
                                else:
                                    pg_cnt += 1
                                    curr_page = add_page(pg_cnt)
                                    yl = START_Y; yr = START_Y
                                    col = 'l'
                        else:
                            # 2열 배치
                            if yl <= yr:
                                if fits_l: col = 'l'
                                elif fits_r: col = 'r'
                            else:
                                if fits_r: col = 'r'
                                elif fits_l: col = 'l'
                            
                            if col is None:
                                if yl == START_Y and yr == START_Y: col = 'r' if yr < yl else 'l'
                                elif yr == START_Y: col = 'r'
                                elif yl == START_Y: col = 'l'
                                else:
                                    pg_cnt += 1
                                    curr_page = add_page(pg_cnt)
                                    yl = START_Y; yr = START_Y
                                    col = 'l'
                        
                        if col == 'l': cx=MARGIN; cy=yl; yl += th + 20
                        else: cx=MARGIN+COL_W+COL_GAP; cy=yr; yr += th + 20
                        
                        iy = cy
                        if show_source:
                            # [수정] 한 줄로 복구
                            t = f"{y} LEET 추리논증 {sn}번"
                            if final_font_path:
                                curr_page.insert_text((cx, cy+12), t, fontname=font_alias, fontfile=final_font_path, fontsize=9, color=(0.4,0.4,0.4))
                            else:
                                curr_page.insert_text((cx, cy+12), t, fontsize=9, color=(0.4,0.4,0.4))
                            iy += hh
                        
                        r = fitz.Rect(cx, iy, cx+COL_W, iy+ih)
                        b = io.BytesIO(); pim.save(b, format='JPEG', quality=90)
                        curr_page.insert_image(r, stream=b.getvalue()); b.close()
                        
                        curr_page.draw_rect(fitz.Rect(cx, iy, cx+19, iy+20), color=(1,1,1), fill=(1,1,1))
                        
                        ns = f"{i}."
                        ny = iy + 14
                        if final_font_path:
                            curr_page.insert_text((cx, ny), ns, fontname=font_alias, fontfile=final_font_path, fontsize=13, color=(0,0,0))
                            curr_page.insert_text((cx+0.7, ny), ns, fontname=font_alias, fontfile=final_font_path, fontsize=13, color=(0,0,0))
                        else: curr_page.insert_text((cx, ny), ns, fontsize=13, color=(0,0,0))
                
                p_idx += 1
                prog.progress(p_idx / valid_count)
                gc.collect()

            tot = len(doc)
            bw, bh = 60, 24
            for i, p in enumerate(doc):
                pg = i+1
                cx = PW/2; by = PH - FOOTER_H/2 + bh/2
                p.draw_rect(fitz.Rect(cx-bw/2, by-bh, cx+bw/2, by), color=THEME_COLOR, width=0.8)
                ft = f"{pg}  /  {tot}"
                tr = fitz.Rect(cx-bw/2, by-bh+6, cx+bw/2, by)
                if final_font_path:
                    p.insert_textbox(tr, ft, fontname=font_alias, fontfile=final_font_path, fontsize=10, align=1, color=THEME_COLOR)
                    p.insert_textbox(fitz.Rect(tr.x0+0.5, tr.y0, tr.x1+0.5, tr.y1), ft, fontname=font_alias, fontfile=final_font_path, fontsize=10, align=1, color=THEME_COLOR)
                else: p.insert_textbox(tr, ft, fontsize=10, align=1, color=THEME_COLOR)
            
            safe_name = custom_title.strip()
            out = f"{safe_name}.pdf"
            
            doc.save(out, garbage=4, deflate=True); doc.close()
            st.success("완료! 다운로드가 곧 시작됩니다.")
            
            auto_download_pdf(out, out)
            with open(out, "rb") as f: st.download_button("📥 수동 다운로드", f, file_name=out, mime="application/pdf", use_container_width=True)