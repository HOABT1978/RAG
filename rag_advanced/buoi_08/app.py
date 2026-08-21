"""
Ứng dụng Streamlit Advanced RAG - Buổi 08
Giao diện trực quan hóa Pipeline 5 Tầng: BM25 -> Semantic -> RRF Fusion -> Reranker -> Grounded LLM
"""

import os
import sys
import json
import time
import pandas as pd
import streamlit as st
from pathlib import Path

# Thêm thư mục Buổi 08 vào sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    load_advanced_config,
    get_advanced_status,
    query_advanced_rag,
    compare_retrieval_modes,
    load_chunks
)

# Cấu hình Trang Streamlit
st.set_page_config(
    page_title="Advanced RAG Dashboard - Buổi 08",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện hiện đại, chuyên nghiệp
st.markdown("""
<style>
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .badge-status {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-answered { background-color: #DCFCE7; color: #166534; }
    .badge-insufficient { background-color: #FEF3C7; color: #92400E; }
    .badge-retrieval { background-color: #E0F2FE; color: #075985; }
    .badge-unavailable { background-color: #FEE2E2; color: #991B1B; }
    
    .card-accepted {
        border-left: 4px solid #22C55E;
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .card-rejected {
        border-left: 4px solid #EF4444;
        background-color: #FFF5F5;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        opacity: 0.8;
    }
    .metric-box {
        background-color: #F1F5F9;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #64748B;
    }
</style>
""", unsafe_allow_html=True)


# Cache Nạp Chunks Corpus theo strategy
@st.cache_data(show_spinner=False)
def cached_load_chunks(strategy: str):
    return load_chunks(strategy=strategy)


# ---------------------------------------------------------------------------
# SIDEBAR SYSTEM STATUS & CONFIGURATION
# ---------------------------------------------------------------------------

st.sidebar.title("⚙️ Cấu hình Advanced RAG")

# Load config từ .env
try:
    config = load_advanced_config()
    config_error = None
except Exception as err:
    config = None
    config_error = str(err)

if config_error:
    st.sidebar.error(f"❌ Lỗi File .env: {config_error}")
    st.stop()

# Selectbox Chọn Strategy & Mode
strategy = st.sidebar.selectbox(
    "1. Chunking Strategy",
    options=["hierarchical", "semantic", "fixed-size"],
    index=0,
    help="Chiến lược cắt phân đoạn tài liệu"
)

mode = st.sidebar.selectbox(
    "2. RAG Retrieval Mode",
    options=["hybrid_rerank", "hybrid", "semantic", "bm25"],
    index=0,
    help="hybrid_rerank: BM25 + Semantic + RRF + Cross-Encoder Reranker"
)

# Thông tin Trạng thái Chẩn đoán System (Read-only)
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Trạng thái Chẩn đoán Hệ thống")

status_res = get_advanced_status(strategy=strategy)

st.sidebar.text(f"Corpus Chunks: {status_res['corpus_size']}")
st.sidebar.text(f"BM25 Ready: {'✅ Có' if status_res['bm25_ready'] else '❌ Chưa'}")

if status_res["collection_exists"]:
    st.sidebar.success(f"Vector Collection: `{status_res['collection_name']}` ({status_res['collection_count']} records)")
else:
    st.sidebar.warning(f"Vector Collection: Chưa tồn tại\nHãy chạy CLI prepare-semantic")

st.sidebar.text(f"Embedding: {status_res['embedding_model']} ({status_res['embedding_dim']}d)")
st.sidebar.text(f"API Key Status: {'✅ Đã có' if status_res['has_api_key'] else '❌ Thiếu'}")

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Parameters (.env)")
col_sb1, col_sb2 = st.sidebar.columns(2)
with col_sb1:
    st.caption(f"BM25 K: **{config['bm25_candidates']}**")
    st.caption(f"Semantic K: **{config['semantic_candidates']}**")
    st.caption(f"RRF k: **{config['rrf_k']}**")
    st.caption(f"RRF Weights: **{config['rrf_bm25_weight']}/{config['rrf_semantic_weight']}**")
with col_sb2:
    st.caption(f"Reranker K: **{config['rerank_candidates']}**")
    st.caption(f"Final Top-K: **{config['final_top_k']}**")
    st.caption(f"Rerank Min Score: **{config['rerank_min_score']}**")
    st.caption(f"Reranker Model: **{config['reranker_model']}**")

st.sidebar.caption(f"Reranker Cached: {'✅ Đã cache' if status_res['reranker_cached'] else '⏳ Chưa load'}")


# ---------------------------------------------------------------------------
# MAIN HEADER & TABS
# ---------------------------------------------------------------------------

st.markdown('<div class="main-header">⚡ Advanced RAG Dashboard — Buổi 08</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Kiến trúc RAG Multi-stage: BM25 + Semantic Search + RRF Fusion + Cross-Encoder Reranker + Grounded LLM</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Hỏi đáp Advanced RAG",
    "🔀 So sánh Retrieval",
    "📈 Pipeline Trace",
    "📊 Đánh giá Metrics"
])


# ---------------------------------------------------------------------------
# TAB 1: HỎI ĐÁP ADVANCED RAG
# ---------------------------------------------------------------------------

with tab1:
    st.markdown("### 💬 Trả lời Câu hỏi với RAG Grounding & Citations")

    question = st.text_input(
        "Nhập câu hỏi của bạn:",
        placeholder="Ví dụ: Điều 7 Thông tư 02/2023/TT-NHNN quy định về báo cáo như thế nào?",
        key="query_input"
    )

    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        run_query = st.button("🚀 Gửi câu hỏi", type="primary", use_container_width=True)

    if run_query and question.strip():
        with st.spinner("Đang thực thi Pipeline Advanced RAG..."):
            try:
                res = query_advanced_rag(
                    question=question,
                    mode=mode,
                    strategy=strategy
                )
                st.session_state["last_query_result"] = res
            except Exception as e:
                st.error(f"❌ Lỗi khi thực thi RAG: {str(e)}")

    if "last_query_result" in st.session_state:
        res = st.session_state["last_query_result"]

        st.markdown("---")

        # 1. Status Badge Header
        status_code = res["status"]
        if status_code == "answered":
            badge_html = '<span class="badge-status badge-answered">✅ ANSWERED</span>'
        elif status_code == "insufficient_evidence":
            badge_html = '<span class="badge-status badge-insufficient">⚠️ INSUFFICIENT EVIDENCE</span>'
        elif status_code == "retrieval_only":
            badge_html = '<span class="badge-status badge-retrieval">ℹ️ RETRIEVAL ONLY</span>'
        else:
            badge_html = '<span class="badge-status badge-unavailable">❌ RERANKER UNAVAILABLE</span>'

        st.markdown(f"#### Kết quả Trả lời | Status: {badge_html}", unsafe_allow_html=True)
        st.caption(f"Mode: `{res['mode']}` | Strategy: `{res['strategy']}`")

        # Warning Messages nếu có
        if res.get("warnings"):
            for w in res["warnings"]:
                st.warning(f"⚠️ {w}")

        # Hướng dẫn chi tiết nếu Reranker Unavailable
        if status_code == "reranker_unavailable":
            st.error(
                "❌ **Mô hình Cross-Encoder Reranker chưa sẵn sàng hoặc gặp lỗi nạp mô hình.**\n\n"
                "👉 **Hướng dẫn khắc phục:**\n"
                "1. Đảm bảo máy tính có kết nối Internet để tải mô hình `BAAI/bge-reranker-v2-m3` (~2.2GB) từ Hugging Face Hub.\n"
                "2. Hoặc mở Terminal và chủ động chạy lệnh CLI chẩn đoán Reranker:\n"
                "   `python rag_foundation/buoi_08/advanced_rag.py rerank --strategy hierarchical --question \"test\"`\n"
                "3. Kiểm tra xem bộ nhớ RAM/VRAM và dung lượng ổ đĩa tại `storage/huggingface/` có còn đủ trống hay không."
            )

        # 2. Render Answer Text
        st.markdown("##### 📝 Câu trả lời:")
        st.info(res["answer"])

        # 3. Render Citations
        if res.get("citations"):
            st.markdown("##### 📌 Trích dẫn Nguồn gốc (Citations):")
            for cite in res["citations"]:
                st.markdown(f"- **{cite['evidence_id']}**: `{cite['source']}` ({cite['display']})")

        st.markdown("---")

        # 4. Render Evidence Cards
        st.markdown("##### 📚 Danh sách Chunk Bằng chứng (Evidence Cards):")

        for idx, ev in enumerate(res["evidence"], 1):
            is_acc = ev.get("accepted", False)
            card_class = "card-accepted" if is_acc else "card-rejected"
            acc_label = "🟢 ACCEPTED (Đưa vào Prompt)" if is_acc else "🔴 REJECTED (Bị loại bởi Gate)"

            b_rank_str = f"#{ev['bm25_rank']}" if ev['bm25_rank'] else "N/A"
            b_score_str = f"{ev['bm25_score']}" if ev['bm25_score'] is not None else "N/A"
            s_rank_str = f"#{ev['semantic_rank']}" if ev['semantic_rank'] else "N/A"
            s_dist_str = f"{ev['semantic_distance']}" if ev['semantic_distance'] is not None else "N/A"

            rrf_score_str = f"{ev['rrf_score']}" if ev['rrf_score'] is not None else "N/A"
            fused_rank_str = f"#{ev['fused_rank']}" if ev['fused_rank'] else "N/A"

            r_score_str = f"{ev['rerank_score']}" if ev['rerank_score'] is not None else "N/A"
            r_raw_str = f"{ev['rerank_raw_score']}" if ev['rerank_raw_score'] is not None else "N/A"
            r_rank_str = f"#{ev['rerank_rank']}" if ev['rerank_rank'] else "N/A"
            r_change_str = f"+{ev['rank_change']}" if ev['rank_change'] and ev['rank_change'] > 0 else str(ev.get('rank_change', 'N/A'))

            with st.container():
                st.markdown(f"""
                <div class="{card_class}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>[E{idx}] {ev['source']} (Tr. {ev['page_start']}-{ev['page_end']}) — Chunk ID: <code>{ev['chunk_id']}</code></strong>
                        <span style="font-weight: bold;">{acc_label}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                with col_e1:
                    st.caption(f"**BM25**: Rank {b_rank_str} | Score: {b_score_str}")
                with col_e2:
                    st.caption(f"**Semantic**: Rank {s_rank_str} | Dist: {s_dist_str}")
                with col_e3:
                    st.caption(f"**RRF Fusion**: Rank {fused_rank_str} | Score: {rrf_score_str}")
                with col_e4:
                    st.caption(f"**Reranker**: Rank {r_rank_str} (Diff: {r_change_str}) | Score: {r_score_str} (Raw: {r_raw_str})")

                with st.expander("📖 Xem toàn bộ nội dung Chunk Text"):
                    st.write(ev["text"])


# ---------------------------------------------------------------------------
# TAB 2: SO SÁNH RETRIEVAL MODES (COMPARE)
# ---------------------------------------------------------------------------

with tab2:
    st.markdown("### 🔀 So sánh Thứ tự Xếp hạng giữa các Retrieval Modes")
    st.caption("Chạy cùng một câu hỏi qua 4 chế độ truy xuất (BM25, Semantic, Hybrid RRF, Hybrid Rerank) mà KHÔNG gọi LLM Generation.")

    comp_question = st.text_input(
        "Nhập câu hỏi cần so sánh:",
        placeholder="Điều 7 quy định gì?",
        key="compare_input"
    )

    if st.button("📊 Thực thi So sánh 4 Modes", type="primary") and comp_question.strip():
        with st.spinner("Đang chạy truy xuất qua 4 retrieval modes..."):
            try:
                comp_res = compare_retrieval_modes(question=comp_question, strategy=strategy)
                st.session_state["last_compare_result"] = comp_res
            except Exception as e:
                st.error(f"❌ Lỗi khi so sánh: {str(e)}")

    if "last_compare_result" in st.session_state:
        c_res = st.session_state["last_compare_result"]
        table_data = c_res["comparison_table"]

        st.markdown("##### 📋 Bảng Tổng hợp So sánh Ranking Chéo (Cross-Mode Rank Table):")

        df = pd.DataFrame(table_data)
        if not df.empty:
            df_display = df[[
                "chunk_id", "bm25_rank", "semantic_rank", "fused_rank", "rerank_rank", "rank_movement", "modes_present"
            ]].copy()

            df_display.columns = [
                "Chunk ID", "BM25 Rank", "Semantic Rank", "Fused (RRF) Rank", "Rerank Rank", "Rank Movement", "Modes Present"
            ]

            st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.markdown("##### ⏱️ Thời gian thực thi (Latencies ms):")
        cols_lat = st.columns(5)
        l_dict = c_res["latencies_ms"]
        cols_lat[0].metric("BM25 Latency", f"{l_dict['bm25']} ms")
        cols_lat[1].metric("Semantic Latency", f"{l_dict['semantic']} ms")
        cols_lat[2].metric("Hybrid Latency", f"{l_dict['hybrid']} ms")
        cols_lat[3].metric("Rerank Latency", f"{l_dict['hybrid_rerank']} ms")
        cols_lat[4].metric("Total Latency", f"{l_dict['total']} ms")


# ---------------------------------------------------------------------------
# TAB 3: PIPELINE TRACE
# ---------------------------------------------------------------------------

with tab3:
    st.markdown("### 📈 Phân tích Pipeline Trace & Latency Breakdown")

    if "last_query_result" in st.session_state:
        q_tr = st.session_state["last_query_result"]["trace"]

        st.markdown("##### 🔢 Luồng dịch chuyển Candidate Counts qua từng tầng:")
        c1, c2, c3, c4, c5 = st.columns(5)

        c1.markdown(f'<div class="metric-box"><div class="metric-value">{q_tr["bm25_candidates"]}</div><div class="metric-label">1. BM25 Candidates</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-box"><div class="metric-value">{q_tr["semantic_candidates"]}</div><div class="metric-label">2. Semantic Candidates</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-box"><div class="metric-value">{q_tr["union"]} ({q_tr["overlap"]} overlap)</div><div class="metric-label">3. RRF Union</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-box"><div class="metric-value">{q_tr["reranked"]}</div><div class="metric-label">4. Rerank Candidates</div></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="metric-box"><div class="metric-value">{q_tr["accepted"]}</div><div class="metric-label">5. Accepted (Gate)</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### ⏱️ Latency Breakdown (Thời gian thực thi từng công đoạn ms):")

        lat_data = q_tr["latency_ms"]
        df_lat = pd.DataFrame([
            {"Stage": "1. BM25 Search", "Latency (ms)": lat_data.get("bm25", 0.0)},
            {"Stage": "2. Semantic Search", "Latency (ms)": lat_data.get("semantic", 0.0)},
            {"Stage": "3. RRF Fusion", "Latency (ms)": lat_data.get("fusion", 0.0)},
            {"Stage": "4. Reranking", "Latency (ms)": lat_data.get("rerank", 0.0)},
            {"Stage": "5. LLM Generation", "Latency (ms)": lat_data.get("generation", 0.0)},
            {"Stage": "Total Pipeline", "Latency (ms)": lat_data.get("total", 0.0)}
        ])

        st.table(df_lat)
    else:
        st.info("💡 Hãy thực hiện một câu hỏi ở Tab 1 để xem thông số Pipeline Trace thực tế.")

    st.markdown("---")
    st.markdown("##### 📌 Ghi chú & Thang đo Thống kê:")
    st.markdown("""
    - **BM25 Score**: Điểm số tần suất từ khóa BM25Okapi (*Càng cao càng tốt*).
    - **Cosine Distance**: Khoảng cách Cosine giữa embedding vectors (*Càng nhỏ càng tốt, 0.0 là trùng khớp tuyệt đối*).
    - **RRF Score**: Điểm số Reciprocal Rank Fusion kết hợp thứ hạng (*Càng cao càng tốt*).
    - **Rerank Score**: Điểm số Sigmoid chuẩn hóa trong đoạn `[0, 1]` của mô hình Cross-Encoder (*Càng cao càng tốt; Không phải xác suất toán học*).
    """)


# ---------------------------------------------------------------------------
# TAB 4: ĐÁNH GIÁ METRICS (EVALUATION REPORT)
# ---------------------------------------------------------------------------

with tab4:
    st.markdown("### 📊 Kết quả Đánh giá Benchmark (Retrieval & Answer Evaluation)")
    st.caption("Nạp báo cáo đánh giá tự động từ các file JSON trong thư mục `reports/`.")

    report_dir = BASE_DIR / "reports"
    json_files = list(report_dir.glob("*.json")) if report_dir.exists() else []

    if not json_files:
        st.warning("⚠️ Chưa có báo cáo JSON nào trong thư mục `rag_foundation/buoi_08/reports/`.\nHãy chạy `python evaluate.py` để khởi tạo báo cáo đánh giá.")
    else:
        selected_json = st.selectbox(
            "Chọn file báo cáo đánh giá:",
            options=[f.name for f in json_files],
            index=0
        )

        target_file = report_dir / selected_json
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            st.success(f"✅ Đã nạp thành công báo cáo `{selected_json}`")

            # Cảnh báo nếu gold data còn nhãn review
            if report_data.get("needs_human_review", False):
                st.warning("⚠️ Báo cáo ghi nhận dữ liệu benchmark vẫn còn chứa nhãn `needs_human_review = true`!")

            st.json(report_data)
        except Exception as e:
            st.error(f"❌ Lỗi khi đọc file JSON báo cáo: {str(e)}")
