"""
Ứng dụng Streamlit Dashboard Advanced RAG - Buổi 08
Giao diện trực quan hóa Pipeline Multi-stage 5 Tầng: BM25 -> Semantic -> RRF -> Reranker -> LLM
"""

import os
import sys
import json
import time
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from rag import load_chunks
from advanced_rag import (
    load_advanced_config,
    get_advanced_status,
    search_bm25,
    search_semantic,
    search_hybrid,
    search_hybrid_rerank,
    query_advanced_rag,
    compare_retrieval_modes
)

# ---------------------------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Advanced RAG Dashboard - Buổi 08",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------------------------------------------------------------------
# CACHE HELPERS
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600)
def get_cached_config():
    return load_advanced_config()


@st.cache_data(ttl=60)
def get_cached_status(strategy: str):
    return get_advanced_status(strategy=strategy)


# ---------------------------------------------------------------------------
# SIDEBAR CONTROL PANEL
# ---------------------------------------------------------------------------
config = get_cached_config()

st.sidebar.title("⚙️ Cấu hình Advanced RAG")
strategy = st.sidebar.selectbox(
    "Chiến lược Chunking (Strategy)",
    options=["hierarchical", "fixed-size", "semantic"],
    index=0
)

status_info = get_cached_status(strategy)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Trạng thái Hệ thống")
st.sidebar.markdown(f"**API Key**: {'✅ Có' if status_info['has_api_key'] else '❌ Thiếu'}")
st.sidebar.markdown(f"**Corpus Size**: `{status_info['corpus_size']}` chunks")
st.sidebar.markdown(f"**Vector Collection**: `{status_info['collection_name']}`")
st.sidebar.markdown(f"**Collection Status**: {'✅ Đã tạo (' + str(status_info['collection_count']) + ' items)' if status_info['collection_exists'] else '⚠️ Chưa tồn tại'}")
st.sidebar.markdown(f"**Embedding Model**: `{status_info['embedding_model']}` ({status_info['embedding_dim']}d)")
st.sidebar.markdown(f"**Reranker Model**: `{status_info['reranker_model']}`")
st.sidebar.markdown(f"**Reranker Cache**: {'✅ Đã có trên đĩa' if status_info['reranker_cached'] else '⚠️ Chưa nạp'}")

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Tham số Pipeline")
st.sidebar.markdown(f"- **BM25 Candidates**: `{config['bm25_candidates']}`")
st.sidebar.markdown(f"- **Semantic Candidates**: `{config['semantic_candidates']}`")
st.sidebar.markdown(f"- **RRF k**: `{config['rrf_k']}` | **Weights**: BM25={config['rrf_bm25_weight']}, Sem={config['rrf_semantic_weight']}")
st.sidebar.markdown(f"- **Rerank Candidates**: `{config['rerank_candidates']}` | **Min Score**: `{config['rerank_min_score']}`")
st.sidebar.markdown(f"- **Final Top-K**: `{config['final_top_k']}`")


# ---------------------------------------------------------------------------
# MAIN HEADER & TAB NAVIGATION
# ---------------------------------------------------------------------------
st.title("⚡ Advanced RAG Dashboard — Buổi 08")
st.caption("Kiến trúc RAG Nâng cao 5 Tầng: BM25 Lexical + Gemini Semantic Vector ➔ RRF Fusion ➔ Cross-Encoder Reranking ➔ Grounded LLM")

tab1, tab2, tab3, tab4 = st.tabs([
    "💬 1. Hỏi đáp Advanced RAG",
    "🔀 2. So sánh Retrieval",
    "🔍 3. Pipeline Trace",
    "📈 4. Đánh giá Metrics"
])


# ---------------------------------------------------------------------------
# TAB 1: HỎI ĐÁP ADVANCED RAG
# ---------------------------------------------------------------------------
with tab1:
    st.subheader("💬 Form Hỏi đáp RAG Nâng cao")

    col_m, col_btn = st.columns([3, 1])
    with col_m:
        selected_mode = st.selectbox(
            "Chọn Retrieval Mode cho Answer Pipeline:",
            options=["hybrid_rerank", "hybrid", "semantic", "bm25"],
            index=0,
            help="`hybrid_rerank` là mode mặc định chính thức cho Advanced RAG."
        )

    question_input = st.text_area(
        "Nhập câu hỏi tra cứu pháp lý:",
        value="Điều 7 quy định như thế nào về cơ cấu lại thời hạn trả nợ?",
        height=100
    )

    if st.button("🚀 Chạy Advanced RAG Pipeline", type="primary", use_container_width=True):
        if not question_input.strip():
            st.error("⚠️ Vui lòng nhập câu hỏi trước khi thực thi.")
        else:
            with st.spinner("Đang xử lý qua Pipeline 5 tầng..."):
                try:
                    res = query_advanced_rag(
                        question=question_input,
                        mode=selected_mode,
                        strategy=strategy
                    )
                    st.session_state["latest_query_result"] = res
                except ValueError as ve:
                    st.error(f"⚠️ Lỗi xử lý: {str(ve)}")
                except Exception as ex:
                    st.error(f"❌ Lỗi hệ thống: {str(ex)}")

    if "latest_query_result" in st.session_state:
        res = st.session_state["latest_query_result"]
        status = res.get("status")

        st.markdown("---")
        st.markdown("### 📌 Kết quả Trả lời & Trích dẫn")

        status_color_map = {
            "answered": ("🟢 PASS: Đã trả lời thành công", "success"),
            "insufficient_evidence": ("🟡 WARNING: Không đủ bằng chứng tự tin", "warning"),
            "retrieval_only": ("🟠 NOTICE: Chỉ truy xuất bằng chứng (Generation lỗi)", "info"),
            "reranker_unavailable": ("🔴 ERROR: Mô hình Reranker chưa sẵn sàng", "error")
        }
        status_label, status_type = status_color_map.get(status, (status, "info"))

        if status_type == "success":
            st.success(status_label)
        elif status_type == "warning":
            st.warning(status_label)
        elif status_type == "error":
            st.error(status_label)
            st.info("💡 **Hướng dẫn**: Nếu là lần chạy đầu tiên với Reranker, mô hình `BAAI/bge-reranker-v2-m3` (~2.2GB) cần được nạp qua CLI. Hãy chạy lệnh `python rag_advanced/buoi_08/advanced_rag.py rerank --question '...'` từ terminal để nạp mô hình.")
        else:
            st.info(status_label)

        if res.get("answer"):
            st.markdown("#### 📝 Câu trả lời Grounded:")
            st.markdown(res["answer"])

        if res.get("citations"):
            with st.expander(f"📚 Xem Danh sách Trích dẫn Chi tiết ({len(res['citations'])} items)", expanded=True):
                for c in res["citations"]:
                    st.markdown(f"- **[{c['label']}]** ➔ Chunk ID: `{c['chunk_id']}` | Nguồn: **{c['source']}** (Trang {c['page_start']}-{c['page_end']})")

        if res.get("warnings"):
            for w in res["warnings"]:
                st.warning(f"⚠️ {w}")

        st.markdown("---")
        st.markdown("### 📦 Thẻ Bằng chứng (Evidence Cards)")

        evidence_items = res.get("evidence", [])
        if not evidence_items:
            st.info("Chưa có bằng chứng nào được truy xuất.")
        else:
            for idx, e in enumerate(evidence_items, 1):
                status_icon = "✅ Accepted" if e.get("accepted") else "❌ Rejected"
                card_title = f"Evidence #{idx} | Chunk `{e['chunk_id']}` | {status_icon}"
                with st.expander(card_title, expanded=e.get("accepted", False)):
                    st.markdown(f"**Nguồn**: `{e['source']}` (Trang {e['page_start']}-{e['page_end']})")
                    st.markdown(f"**Nội dung**: {e['text']}")
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"**BM25 Rank**: `{e.get('bm25_rank') or '-'}`")
                        st.markdown(f"**BM25 Score**: `{e.get('bm25_score') or '-'}`")
                    with col2:
                        st.markdown(f"**Semantic Rank**: `{e.get('semantic_rank') or '-'}`")
                        st.markdown(f"**Cosine Dist**: `{e.get('semantic_distance') or '-'}`")
                    with col3:
                        st.markdown(f"**Fused Rank**: `{e.get('fused_rank') or '-'}`")
                        st.markdown(f"**RRF Score**: `{e.get('rrf_score') or '-'}`")
                    with col4:
                        st.markdown(f"**Rerank Rank**: `{e.get('rerank_rank') or '-'}`")
                        st.markdown(f"**Rerank Score**: `{e.get('rerank_score') or '-'}`")
                        st.markdown(f"**Rank Change**: `{e.get('rank_change') or '-'}`")


# ---------------------------------------------------------------------------
# TAB 2: SO SÁNH RETRIEVAL
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("🔀 So sánh Thứ tự Xếp hạng giữa 4 Chế độ Retrieval")
    st.caption("Chạy cùng 1 câu hỏi qua 4 modes: BM25 ➔ Semantic ➔ Hybrid RRF ➔ Hybrid + Rerank. Tuyệt đối KHÔNG gọi LLM generation.")

    comp_question = st.text_input(
        "Câu hỏi so sánh thứ tự xếp hạng:",
        value="Điều 7 quy định như thế nào về cơ cấu lại thời hạn trả nợ?",
        key="comp_q_input"
    )

    if st.button("📊 Chạy So sánh 4 Modes", type="secondary", use_container_width=True):
        with st.spinner("Đang truy xuất và hợp nhất 4 modes..."):
            try:
                comp_data = compare_retrieval_modes(question=comp_question, strategy=strategy)
                st.session_state["latest_comparison_result"] = comp_data
            except Exception as e:
                st.error(f"⚠️ Lỗi so sánh: {str(e)}")

    if "latest_comparison_result" in st.session_state:
        cmp_res = st.session_state["latest_comparison_result"]
        table_data = cmp_res["summary_table"]
        latencies = cmp_res["latency_ms"]

        st.markdown("#### ⚡ Thời gian thực thi (Latency ms):")
        col_l1, col_l2, col_l3, col_l4 = st.columns(4)
        col_l1.metric("BM25 Latency", f"{latencies['bm25']} ms")
        col_l2.metric("Semantic Latency", f"{latencies['semantic']} ms")
        col_l3.metric("Hybrid Latency", f"{latencies['hybrid']} ms")
        col_l4.metric("Hybrid Rerank Latency", f"{latencies['hybrid_rerank']} ms")

        st.markdown("---")
        st.markdown("#### 📋 Bảng So sánh Tổng hợp Chéo:")

        formatted_rows = []
        for r in table_data:
            ranks = r["ranks"]
            formatted_rows.append({
                "Chunk ID": r["chunk_id"],
                "Source": r["source"],
                "BM25 Rank": f"#{ranks.get('bm25')}" if "bm25" in ranks else "-",
                "Semantic Rank": f"#{ranks.get('semantic')}" if "semantic" in ranks else "-",
                "Fused Rank": f"#{ranks.get('hybrid')}" if "hybrid" in ranks else "-",
                "Rerank Rank": f"#{ranks.get('hybrid_rerank')}" if "hybrid_rerank" in ranks else "-",
                "Rank Change": f"+{r['rank_change']}" if (r['rank_change'] is not None and r['rank_change'] > 0) else f"{r['rank_change'] or '-'}",
                "Final Modes": ", ".join(r["present_in_modes"])
            })

        st.dataframe(formatted_rows, use_container_width=True)


# ---------------------------------------------------------------------------
# TAB 3: PIPELINE TRACE
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("🔍 Pipeline Trace & Luồng Dữ liệu Candidates")
    st.caption("Xem thông số rút gọn candidate qua từng tầng xử lý và độ trễ latency thực tế.")

    if "latest_query_result" in st.session_state:
        trace = st.session_state["latest_query_result"].get("trace", {})

        st.markdown("#### 🔄 Luồng biến đổi Candidate Counts:")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("1. BM25 Candidates", trace.get("bm25_candidates", 0))
        c2.metric("2. Semantic Candidates", trace.get("semantic_candidates", 0))
        c3.metric("3. Union / Overlap", f"{trace.get('union', 0)} / {trace.get('overlap', 0)}")
        c4.metric("4. Reranked", trace.get("reranked", 0))
        c5.metric("5. Accepted Evidence", trace.get("accepted", 0))

        st.markdown("---")
        st.markdown("#### ⏱️ Chi tiết Latency từng Stage (ms):")
        lat_dict = trace.get("latency_ms", {})

        lat_rows = [
            {"Stage": "1. BM25 Search", "Latency (ms)": f"{lat_dict.get('bm25', 0.0)} ms"},
            {"Stage": "2. Semantic Vector Search", "Latency (ms)": f"{lat_dict.get('semantic', 0.0)} ms"},
            {"Stage": "3. RRF Fusion", "Latency (ms)": f"{lat_dict.get('fusion', 0.0)} ms"},
            {"Stage": "4. Cross-Encoder Rerank", "Latency (ms)": f"{lat_dict.get('rerank', 0.0)} ms"},
            {"Stage": "5. Grounded LLM Generation", "Latency (ms)": f"{lat_dict.get('generation', 0.0)} ms"},
            {"Stage": "TOTAL PIPELINE", "Latency (ms)": f"{lat_dict.get('total', 0.0)} ms"}
        ]
        st.table(lat_rows)
    else:
        st.info("💡 Hãy thực hiện ít nhất 1 truy vấn ở **Tab 1** để xem Pipeline Trace chi tiết.")

    st.markdown("---")
    st.markdown("### 💡 Chú thích Thang điểm (Metric Legend)")
    st.markdown("""
    - **BM25 Score**: Điểm số tần suất xuất hiện từ khóa khớp chính xác (*Càng cao càng tốt*).
    - **Cosine Distance**: Khoảng cách vector giữa query và document (*Càng nhỏ càng tốt, 0.0 là trùng khớp tuyệt đối*).
    - **RRF Score**: Điểm số Reciprocal Rank Fusion tổng hợp vị trí thứ hạng (*Càng cao càng tốt*).
    - **Rerank Score**: Điểm số Sigmoid chuẩn hóa trong khoảng `[0, 1]` từ raw logit của Cross-Encoder (*Càng cao càng tốt; Đây là điểm tự tin của mô hình, KHÔNG PHẢI xác suất toán học*).
    """)


# ---------------------------------------------------------------------------
# TAB 4: ĐÁNH GIÁ METRICS
# ---------------------------------------------------------------------------
with tab4:
    st.subheader("📈 Báo cáo Đánh giá Benchmark Offline")
    st.caption("Đọc trực tiếp báo cáo JSON do `evaluate.py` tạo trong thư mục `reports/`.")

    reports_dir = BASE_DIR / "reports"
    report_files = sorted(list(reports_dir.glob("*.json")), reverse=True)

    if not report_files:
        st.warning("⚠️ Chưa tìm thấy báo cáo JSON nào trong thư mục `reports/`.")
        st.info("💡 Hãy chạy lệnh CLI sau từ terminal để tạo báo cáo đánh giá:\n```bash\npython rag_advanced/buoi_08/evaluate.py --strategy hierarchical --k 5\n```")
    else:
        selected_report_file = st.selectbox("Chọn file báo cáo đánh giá:", options=[f.name for f in report_files])
        report_path = reports_dir / selected_report_file

        with open(report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        st.markdown(f"**Timestamp**: `{report_data.get('timestamp')}` | **Strategy**: `{report_data.get('strategy')}` | **K**: `{report_data.get('k')}`")

        warn_info = report_data.get("needs_human_review_warning", {})
        if warn_info.get("has_review_flag"):
            st.warning(f"⚠️ {warn_info.get('message')}")

        st.markdown("#### 📊 Bảng Chỉ số Chất lượng Truy xuất (Retrieval Quality Metrics):")
        mode_results = report_data.get("results_by_mode", {})

        metrics_rows = []
        for m_name, m_data in mode_results.items():
            metrics_rows.append({
                "Mode": m_name,
                "Recall@K": f"{m_data.get('recall_at_k', 0.0):.4f}",
                "MRR@K": f"{m_data.get('mrr_at_k', 0.0):.4f}",
                "nDCG@K": f"{m_data.get('ndcg_at_k', 0.0):.4f}",
                "Mean Latency": f"{m_data.get('latency_mean_ms', 0.0):.2f} ms",
                "P50 Latency": f"{m_data.get('latency_p50_ms', 0.0):.2f} ms",
                "Evaluated Queries": m_data.get("evaluated_queries_count", 0)
            })

        st.table(metrics_rows)
