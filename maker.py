import streamlit as st
import streamlit.components.v1 as components  # [중요] 자동 다운로드를 위해 꼭 필요합니다
import fitz  # PyMuPDF
import os
from PIL import Image
import io
import gc
import re
import base64

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="나만의 문제집 생성기", initial_sidebar_state="collapsed")

# --- 스타일 커스텀 ---
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    
    .slot-header {
        text-align: center; font-weight: 700; background-color: #f0f2f6;
        padding: 5px; border-radius: 5px; margin-bottom: 10px; font-size: 15px; color: #333;
        height: 40px; display: flex; align-items: center; justify-content: center;
    }
    
    button[kind="secondary"] {
        padding: 0px 5px !important; border: 1px solid #ffcccc; background-color: #fff5f5; color: #ff4b4b; font-weight: bold;
    }
    button[kind="secondary"]:hover { border-color: #ff4b4b; background-color: #ffcccc; color: #ff0000; }
    
    .big-plus-button > button {
        height: 100px !important; border: 2px dashed #4f8bf9 !important; background-color: #f0f7ff !important;
        color: #4f8bf9 !important; font-size: 24px !important; font-weight: bold !important; width: 100%;
        margin-top: 25px; 
    }
    .big-plus-button > button:hover { background-color: #e0efff !important; }
    
    .stFileUploader { margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("📑 나만의 맞춤 문제집 생성기")

# --- 0. 세션 ---
if 'target_q_count' not in st.session_state: st.session_state.target_q_count = 10
def increase_q(): st.session_state.target_q_count += 1
def decrease_q():
    if st.session_state.target_q_count > 1: st.session_state.target_q_count -= 1

# --- 1. 데이터 ---
def get_available_exams():
    if not os.path.exists("output"): os.makedirs("output"); return {}
    exams = {}
    folders = [f for f in os.listdir("output") if os.path.isdir(os.path.join("output", f))]
    for folder in folders:
        match = re.match(r"(\d{4})", folder)
        if match: exams[match.group(1)] = folder
    return dict(sorted(exams.items()))

available_exams = get_available_exams()

# --- 자동 다운로드 함수 ---
def auto_download_pdf(file_path, file_name):
    with open(file_path, "rb") as f: data = f.read()
    b64 = base64.b64encode(data).decode()
    js = f"""
    <script>
        var a = document.createElement('a');
        a.href = 'data:application/pdf;base64,{b64}';
        a.download = '{file_name}';
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    </script>
    """
    components.html(js, height=0)

# --- 2. 설정 ---
c_set1, c_set2 = st.columns(2)
with c_set1:
    custom_title = st.text_input("문제집 이름", value="추리논증 문항모음")
    show_source = st.toggle("상단 출처 표시", value=True)

with c_set2:
    final_font_path = None
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        if os.path.exists("MALGUN.TTF"):
            final_font_path = "MALGUN.TTF"
            st.caption("✅ 본문: MALGUN.TTF (폴더 내 파일)")
        else:
            def get_sys_font():
                candidates = ["malgun.ttf", "Malgun.ttf", "C:/Windows/Fonts/malgun.ttf"]
                for p in candidates: 
                    if os.path.exists(p): return p
                return None
            sys_font = get_sys_font()
            if sys_font:
                final_font_path = sys_font
                st.caption("✅ 본문: 시스템 기본 맑은고딕")
            else:
                uploaded = st.file_uploader("본문 폰트(TTF)", type="ttf", key="main")
                if uploaded:
                    with open("custom_font.ttf", "wb") as f: f.write(uploaded.getbuffer())
                    final_font_path = "custom_font.ttf"

    with c_f2:
        title_font_path = None
        if os.path.exists("SBM.ttf"):
            title_font_path = "SBM.ttf"
            st.caption("✅ 제목: SBM.ttf (폴더 내 파일)")
        else:
            up_title = st.file_uploader("제목용 SBM.ttf", type="ttf", key="sbm")
            if up_title:
                with open("SBM.ttf", "wb") as f: f.write(up_title.getbuffer())
                title_font_path = "SBM.ttf"

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
                        if q_num == cur_cnt:
                            c_txt, c_btn = st.columns([2, 1])
                            with c_txt: st.markdown(f"<div class='slot-header' style='margin:0;'>{q_num}문</div>", unsafe_allow_html=True)
                            with c_btn:
                                if st.button("－", key=f"d_{q_num}", help="삭제"): decrease_q(); st.rerun()
                        else: st.markdown(f"<div class='slot-header'>{q_num}문</div>", unsafe_allow_html=True)
                        
                        y = st.selectbox("y", years_list, key=f"y_{q_num}", label_visibility="collapsed", format_func=lambda x: "년도 선택" if x == "선택" else f"{x}년")
                        
                        if y != "선택":
                            mv = 35 if y in ['2017', '2018'] else 40
                            q_options = [f"{k}번" for k in range(1, mv+1)]
                            default_idx = (q_num - 1) if (q_num <= mv) else 0
                            n_str = st.selectbox("n", q_options, index=default_idx, key=f"n_{q_num}", label_visibility="collapsed")
                            n = int(n_str.replace("번", ""))
                            user_selections[q_num] = (y, n)
                        else:
                            st.selectbox("n", ["문항 번호"], key=f"n_{q_num}", label_visibility="collapsed", disabled=True)
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
                # 1. 페이지 번호
                pg_y = MARGIN + 10
                if final_font_path:
                    page.insert_text((MARGIN, pg_y), str(pg_num), fontname=font_alias, fontfile=final_font_path, fontsize=24, color=(0,0,0))
                else:
                    page.insert_text((MARGIN, pg_y), str(pg_num), fontsize=24, color=(0,0,0), fontname="helv")
                
                # 2. 제목
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

                # 3. 우측 상단 텍스트 (박스 없음)
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
                
                # 4. 상단 가로선 (1.5 굵기)
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
                        hh = 20 if show_source else 0
                        th = hh + ih
                        lim = PH - FOOTER_H - 5 
                        
                        fits_l = (yl + th <= lim)
                        fits_r = (yr + th <= lim)
                        col = None
                        
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
                            t = f"{y} LEET 추리논증 {sn}번"
                            if final_font_path: curr_page.insert_text((cx, cy+12), t, fontname=font_alias, fontfile=final_font_path, fontsize=9, color=(0.4,0.4,0.4))
                            else: curr_page.insert_text((cx, cy+12), t, fontsize=9, color=(0.4,0.4,0.4))
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
            
            out = "나만의_문제집_완성.pdf"
            doc.save(out, garbage=4, deflate=True); doc.close()
            st.success("완료! 다운로드가 곧 시작됩니다.")
            auto_download_pdf(out, out)
            with open(out, "rb") as f: st.download_button("📥 수동 다운로드", f, file_name=out, mime="application/pdf", use_container_width=True)