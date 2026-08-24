# -*- coding: utf-8 -*-
"""app.py — UI Streamlit trực quan hoá Buổi 5 (tiếng Việt).

Minh hoạ luồng:  PDF gốc -> Text OCR -> Chunk (3 chiến lược).

Khởi chạy:
    .venv\\Scripts\\python.exe -m streamlit run app.py
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
RAW_DIR = OUTPUT / "raw"
CHUNK_DIR = OUTPUT / "chunks"
PAGES_DIR = OUTPUT / "pages"
DATADEMO = BASE / "datademo"
PIPELINE = BASE / "src" / "pipeline.py"

PAGE_RE = re.compile(r"===== TRANG (\d+) \| nguồn: (\S+) =====\n?(.*?)(?=====|$)", re.S)

STRATEGY_LABELS = {
    "fixed_size": "Fixed-size",
    "semantic": "Semantic",
    "hierarchical": "Hierarchical",
}
STRATEGY_DESC = {
    "fixed_size": "Cắt theo số ký tự cố định + overlap",
    "semantic": "Cắt theo đoạn văn, hết câu khi có thể",
    "hierarchical": "Mỗi mốc Chương/Mục/Điều/Điểm bắt đầu 1 chunk",
}
COLORS = [
    "#cfe8ff", "#ffe9c7", "#d9f0d3", "#f5d0d0", "#e3d7f5",
    "#c7ecf0", "#fbe3c9", "#d7d7f7", "#d3e8cf", "#f2d3e8",
]


# ---------------------------------------------------------------- load
@st.cache_data(show_spinner=False)
def list_documents() -> list[str]:
    if not CHUNK_DIR.exists():
        return []
    return sorted(p.name.replace("_chunks.jsonl", "") for p in CHUNK_DIR.glob("*_chunks.jsonl"))


@st.cache_data(show_spinner=False)
def load_raw_pages(doc: str) -> list[dict]:
    path = RAW_DIR / f"{doc}_raw.txt"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    pages = []
    for i, block in enumerate(PAGE_RE.findall(text), start=1):
        pages.append({"page": int(block[0]), "method": block[1], "text": block[2].rstrip()})
    if not pages:
        # không có marker trang -> coi cả file là 1 trang
        pages = [{"page": 1, "method": "text", "text": text}]
    return pages


@st.cache_data(show_spinner=False)
def load_raw_meta(doc: str) -> dict:
    path = RAW_DIR / f"{doc}_raw.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_chunks(doc: str) -> pd.DataFrame:
    path = CHUNK_DIR / f"{doc}_chunks.jsonl"
    if not path.exists():
        return pd.DataFrame()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DataFrame(rows)


def page_images(doc: str) -> list[Path]:
    folder = PAGES_DIR / doc
    if not folder.exists():
        return []
    return sorted(folder.glob("page_*.png"))


# ---------------------------------------------------------------- pipeline
def run_pipeline(pdf: str | None) -> tuple[int, str]:
    """Gọi src/pipeline.py --write để OCR + chunking một (hoặc tất cả) PDF."""
    cmd = [sys.executable, str(PIPELINE), "--write"]
    if pdf:
        cmd += ["--pdf", pdf]
    proc = subprocess.run(
        cmd,
        cwd=str(BASE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode, out


# ---------------------------------------------------------------- render
def render_chunk_card(chunk: dict, color: str) -> None:
    structure = chunk.get("structure") or {}
    badge = (
        f"🏷 {structure.get('type', '—')}"
        + (f" · {structure.get('title', '')}" if structure.get("title") else "")
        if structure
        else "🏷 không có cấu trúc"
    )
    with st.expander(
        f"**{chunk['chunk_id']}** · trang {chunk['page_start']}–{chunk['page_end']}"
        f" · {len(chunk['text']):,} ký tự · {badge}"
    ):
        st.markdown(f"<div style='background:{color}; padding:10px; border-radius:8px;'>{html.escape(chunk['text']).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)


def render_boundaries(chunks: list[dict], limit: int) -> None:
    st.markdown("**Trực quan ranh giới chunk** (mỗi màu = 1 chunk liên tục):")
    buffer = ""
    for i, c in enumerate(chunks):
        color = COLORS[i % len(COLORS)]
        buffer += f"<span style='background:{color};'>{html.escape(c['text'])}</span>"
        if i < len(chunks) - 1:
            buffer += "<span style='color:red;'>‖</span>"
        if len(buffer) > limit:
            buffer += "<span style='color:red;'>… (đã cắt hiển thị)</span>"
            break
    st.markdown(
        buffer.replace(chr(10), "<br>")[: limit + 2000],
        unsafe_allow_html=True,
    )


def stats_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strat in ["fixed_size", "semantic", "hierarchical"]:
        sub = df[df["strategy"] == strat]
        lens = sub["text"].str.len()
        rows.append({
            "Chiến lược": STRATEGY_LABELS[strat],
            "Số chunk": len(sub),
            "Min (ký tự)": int(lens.min()) if len(sub) else 0,
            "Max (ký tự)": int(lens.max()) if len(sub) else 0,
            "Trung bình": round(float(lens.mean()), 1) if len(sub) else 0.0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- app
st.set_page_config(page_title="RAG Foundation — Buổi 5", page_icon="📄", layout="wide")
st.title("📄 RAG Foundation — Buổi 5")
st.caption("OCR PDF tiếng Việt + trực quan hoá 3 chiến lược chunking (fixed-size · semantic · hierarchical)")

docs = list_documents()
pdf_choices = sorted(p.name for p in DATADEMO.glob("*.pdf")) if DATADEMO.exists() else []

# ---- sidebar
with st.sidebar:
    st.markdown("### ⚙️ Xử lý tài liệu")
    if pdf_choices:
        sel_pdf = st.selectbox("PDF trong datademo/", pdf_choices, key="proc_pdf")
        process_all = st.checkbox("Xử lý tất cả PDF", key="proc_all", value=len(pdf_choices) == 1)
    else:
        st.caption("Không có PDF trong datademo/.")
        sel_pdf, process_all = None, False
    clicked = st.button("▶️ Xử lý tài liệu", type="primary")
    if clicked:
        try:
            with st.spinner("Đang OCR + chunking… (Llamaparse có thể mất 1-2 phút/file)"):
                rc, out = run_pipeline(None if process_all else sel_pdf)
        except subprocess.TimeoutExpired:
            st.error("Xử lý quá lâu (quá 60 phút) — bị huỷ.")
            rc, out = 1, ""
        st.markdown("**Kết quả pipeline:**")
        st.code(out[-2500:], language="text")
        if rc == 0:
            st.success("Xử lý xong! Đang tải lại dữ liệu…")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Pipeline kết thúc với lỗi (xem log bên trên).")

    st.markdown("---")
    st.markdown("### 📚 Tài liệu đã xử lý")
    if docs:
        doc = st.selectbox("Chọn tài liệu", docs, key="doc_sel")
        strategy = st.radio(
            "✂️ Chiến lược chunking",
            ["fixed_size", "semantic", "hierarchical"],
            format_func=lambda s: STRATEGY_LABELS[s],
        )
        st.info(STRATEGY_DESC[strategy])
        highlight_limit = st.slider("Giới hạn ký tự hiển thị ranh giới", 2000, 20000, 8000, step=1000)
    else:
        st.caption("Chưa có tài liệu. Chọn PDF phía trên rồi bấm **Xử lý tài liệu**.")
        doc = None

    st.markdown("---")
    st.caption("Buổi 5 **không** tạo embedding, không lưu vector DB, không gọi LLM.")

if not docs:
    st.info("Chưa có dữ liệu trong `output/`. Dùng nút **▶️ Xử lý tài liệu** ở sidebar để chạy OCR + chunking.")
    st.stop()

pages = load_raw_pages(doc)
meta = load_raw_meta(doc)
df = load_chunks(doc)
imgs = page_images(doc)

st.subheader(f"📂 Tài liệu: `{doc}`")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Số trang", len(pages))
col2.metric("OCR dùng Llamaparse", "✅ Có" if meta.get("ocr_used") else "❌ Không")
col3.metric("Số ký tự", f"{meta.get('char_count', 0):,}")
col4.metric("Số chunk (3 chiến lược)", f"{len(df):,}")

tab_pdf, tab_text, tab_chunk, tab_compare = st.tabs(
    ["1️⃣ PDF gốc", "2️⃣ Text sau OCR", "3️⃣ Chunk", "4️⃣ So sánh 3 chiến lược"]
)

# ---------------- tab 1: PDF
with tab_pdf:
    if imgs:
        page_idx = st.select_slider("Chọn trang PDF", options=list(range(1, len(imgs) + 1)), value=1)
        st.image(str(imgs[page_idx - 1]), caption=f"Trang {page_idx} (render 150dpi)", width="stretch")
        st.caption("PDF gốc là ảnh scan → được render thành PNG để minh hoạ bước 'scan → OCR'.")
    else:
        st.info("Không có ảnh trang (chưa render). Chạy pipeline với `--render-pages`.")

# ---------------- tab 2: text
with tab_text:
    if pages:
        sel_page = st.selectbox("Chọn trang text", options=[p["page"] for p in pages], format_func=lambda n: f"Trang {n}")
        p = next(x for x in pages if x["page"] == sel_page)
        st.code(p["text"], language=None)
        st.caption(f"Nguồn text trang này: **{p['method']}** — đã chuẩn hoá Unicode NFC.")
    else:
        st.info("Chưa có text.")

# ---------------- tab 3: chunks
with tab_chunk:
    if df.empty:
        st.info("Chưa có chunk.")
    else:
        sub = df[df["strategy"] == strategy].reset_index(drop=True)
        st.markdown(f"### Chiến lược: **{STRATEGY_LABELS[strategy]}**")
        st.markdown(STRATEGY_DESC[strategy])
        st.dataframe(sub[["chunk_id", "page_start", "page_end", "text"]].assign(
            độ_dài=sub["text"].str.len()
        ), width="stretch", height=220)

        render_boundaries(sub.to_dict("records"), highlight_limit)

        st.markdown("---")
        st.markdown("### Danh sách chunk đầy đủ")
        for i, c in enumerate(sub.to_dict("records")):
            render_chunk_card(c, COLORS[i % len(COLORS)])

# ---------------- tab 4: compare
with tab_compare:
    st.markdown("### So sánh 3 chiến lược")
    st.dataframe(stats_table(df), width="stretch")
    st.markdown("#### Nhận xét trực quan")
    st.markdown(
        "- **Fixed-size**: số chunk nhiều, độ dài đồng đều (~500 ký tự), nhưng có thể cắt ngang giữa câu/đoạn.\n"
        "- **Semantic**: chunk giữ trọn đoạn văn, ít bị cắt ngang câu, độ dài tự nhiên theo đoạn.\n"
        "- **Hierarchical**: mỗi chunk bắt đầu ở một mốc cấu trúc (Chương/Mục/Điều/Điểm) — dễ truy hồi theo quy định pháp luật, nhưng chunk có thể dài bất đối xứng."
    )
    hier = df[df["strategy"] == "hierarchical"]
    no_struct = hier[hier["structure"].isna() | (hier["structure"].apply(lambda s: not s))]
    if len(no_struct):
        st.warning(f"Có {len(no_struct)} chunk hierarchical không có cấu trúc (phần mở đầu hoặc văn bản không có tiêu đề).")
    st.caption("Bảng thống kê tính trên text sau OCR (Unicode NFC).")

st.markdown("---")
st.caption("Hướng dẫn: chạy `python src/pipeline.py --dry-run` để xem kế hoạch, `--write` để sinh dữ liệu.")
