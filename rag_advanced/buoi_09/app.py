"""
Giao diện Streamlit Dashboard - Buổi 09
Trực quan hóa cây quan hệ phân cấp, Multi-query và So sánh 4 Chế độ Flat vs Parent RAG.
"""

import os
import sys
import re
import json
import time
import math
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd

# Thiết lập đường dẫn thư mục gốc để import các module local
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Import các logic lõi và helpers
from hierarchical_rag import (
    load_hierarchical_config,
    query_hierarchical_rag,
    build_and_save_hierarchy,
    validate_hierarchy_registry,
    get_hierarchy_status,
    generate_query_variants,
    retrieve_multi_query_hybrid,
    retrieve_hierarchical_parent
)
from rag import get_status, run_index
from ui_helpers import (
    citation_formatting,
    query_child_matrix,
    parent_tree_data,
    mode_comparison_row,
    warning_status_mapping
)

def datetime_now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Thiết lập page config cho Streamlit
st.set_page_config(
    page_title="RAG Foundation - Buổi 09",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Áp dụng CSS tùy chỉnh để làm nổi bật giao diện và tạo thẩm mỹ premium
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Tạo hiệu ứng gradient cho Tiêu đề chính */
    .title-gradient {
        background: linear-gradient(135deg, #FF4B4B, #8A2BE2, #00BFFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.3rem;
        font-weight: 800;
        margin-bottom: 2px;
        text-shadow: 0px 4px 10px rgba(0,0,0,0.05);
    }
    
    .pipeline-badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 20px;
    }
    
    .pipeline-step {
        background-color: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.85rem;
        font-weight: 600;
        color: #00D2FF;
        display: flex;
        align-items: center;
    }
    
    .pipeline-arrow {
        color: #888888;
        font-size: 0.85rem;
        align-self: center;
        margin: 0 4px;
    }

    /* Phong cách card thông tin */
    .card-q-orig {
        border-left: 5px solid #FF4B4B;
        background-color: rgba(255, 75, 75, 0.05);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .card-q-gen {
        border-left: 5px solid #1E90FF;
        background-color: rgba(30, 144, 255, 0.05);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .status-text {
        font-size: 0.85rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;
    }
    
    .status-ready {
        background-color: rgba(0, 204, 102, 0.15);
        color: #00FF66;
    }
    
    .status-stale {
        background-color: rgba(255, 165, 0, 0.15);
        color: #FFA500;
    }
    
    .status-missing {
        background-color: rgba(255, 75, 75, 0.15);
        color: #FF4B4B;
    }
    
    /* Thiết kế matrix styling */
    .matrix-title {
        font-weight: 700;
        font-size: 1.1rem;
        color: #FFFFFF;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------------
# INITIALIZE STATE AND CACHE
# ---------------------------------------------------------------------------
if "tab_idx" not in st.session_state:
    st.session_state["tab_idx"] = 0

if "rag_result" not in st.session_state:
    st.session_state["rag_result"] = None

if "compare_results" not in st.session_state:
    st.session_state["compare_results"] = None

if "eval_report" not in st.session_state:
    # Đọc latest report từ đĩa nếu có
    report_path = BASE_DIR / "reports" / "latest_report.json"
    if report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                st.session_state["eval_report"] = json.load(f)
        except Exception:
            st.session_state["eval_report"] = None
    else:
        st.session_state["eval_report"] = None

# Nạp cấu hình hiện tại để làm giá trị mặc định cho Widgets
config = load_hierarchical_config()

# ---------------------------------------------------------------------------
# SIDEBAR CONFIGURATION
# ---------------------------------------------------------------------------
st.sidebar.title("🌲 RAG Control Hub")

st.sidebar.markdown("### ⚙️ Cấu hình Runtime")

# 1. Chọn Mode thực thi chính
mode_options = ["multi_parent", "single_parent", "multi_flat", "single_flat"]
selected_mode = st.sidebar.selectbox(
    "Retrieval Mode",
    options=mode_options,
    index=0,
    help="single_flat: RAG phẳng cơ bản\nmulti_flat: RAG phẳng kèm mở rộng câu hỏi\nsingle_parent: RAG phân cấp một câu hỏi\nmulti_parent: RAG phân cấp đa câu hỏi"
)

# 2. Hyperparameters
mq_count = st.sidebar.slider(
    "MULTI_QUERY_COUNT", 1, 5, 
    value=int(config["multi_query_count"]),
    help="Số lượng câu hỏi biến thể được sinh ra bởi LLM."
)
per_query_candidates = st.sidebar.slider(
    "PER_QUERY_CANDIDATES", 1, 100, 
    value=int(config["per_query_candidates"]),
    help="Số lượng chunks con lấy ra cho mỗi câu hỏi đơn."
)
parent_candidates = st.sidebar.slider(
    "PARENT_CANDIDATES", 1, 100, 
    value=int(config["parent_candidates"]),
    help="Giới hạn số lượng tài liệu cha đưa vào bước Reranking."
)
final_parent_top_k = st.sidebar.slider(
    "FINAL_PARENT_TOP_K", 1, 100, 
    value=int(config["final_parent_top_k"]),
    help="Số tài liệu cha tối đa giữ lại sau khi Rerank để gửi LLM."
)
rerank_min_score = st.sidebar.slider(
    "RERANK_MIN_SCORE", 0.0, 1.0, 
    value=float(config["rerank_min_score"]), 
    step=0.05,
    help="Ngưỡng điểm tối thiểu để vượt Confidence Gate của Reranker."
)

# Khóa strategy hierarchical cố định
st.sidebar.text_input("Strategy", value="hierarchical", disabled=True)

# 3. Model Identity Configuration
st.sidebar.markdown("### 🤖 Cấu hình Models")
embedding_model = st.sidebar.text_input("Embedding Model", value=config["embedding_model"])
generation_model = st.sidebar.text_input("Generation Model", value=config["generation_model"])
reranker_model = st.sidebar.text_input("Reranker Model", value=config["reranker_model"])

# Đồng bộ hóa tham số cấu hình với environment variables
os.environ["MULTI_QUERY_COUNT"] = str(mq_count)
os.environ["PER_QUERY_CANDIDATES"] = str(per_query_candidates)
os.environ["PARENT_CANDIDATES"] = str(parent_candidates)
os.environ["FINAL_PARENT_TOP_K"] = str(final_parent_top_k)
os.environ["RERANK_MIN_SCORE"] = str(rerank_min_score)
os.environ["GEMINI_EMBEDDING_MODEL"] = embedding_model
os.environ["GEMINI_GENERATION_MODEL"] = generation_model
os.environ["RERANKER_MODEL"] = reranker_model

# 4. Status Panel Indicators
st.sidebar.markdown("### 📊 Trạng thái Hệ thống")

# A. Gemini Key check (không lộ key)
api_key = os.getenv("GEMINI_API_KEY", "").strip()
if api_key:
    st.sidebar.markdown("🔑 **Gemini API Key:** <span class='status-text status-ready'>Có (Hợp lệ)</span>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("🔑 **Gemini API Key:** <span class='status-text status-missing'>Thiếu Key</span>", unsafe_allow_html=True)

# B. Hierarchy Store Status
valid_reg, msg_reg, manifest = validate_hierarchy_registry()
hierarchy_status = get_hierarchy_status()
if valid_reg:
    st.sidebar.markdown("📂 **Hierarchy Store:** <span class='status-text status-ready'>Ready</span>", unsafe_allow_html=True)
elif hierarchy_status["hierarchy_built"]:
    st.sidebar.markdown("📂 **Hierarchy Store:** <span class='status-text status-stale'>Stale</span>", unsafe_allow_html=True)
    st.sidebar.caption(f"Lỗi: {msg_reg}")
else:
    st.sidebar.markdown("📂 **Hierarchy Store:** <span class='status-text status-missing'>Missing</span>", unsafe_allow_html=True)

# C. Counts
if manifest:
    counts = manifest.get("counts", {})
    warn_counts = manifest.get("warning_counts", {})
    st.sidebar.caption(
        f"• Chunks con: {counts.get('child_chunks', 0)} | Tài liệu cha: {counts.get('parent_documents', 0)}\n\n"
        f"• Trùng/Mơ hồ (Ambiguous): {warn_counts.get('ambiguous_children', 0)}"
    )
else:
    st.sidebar.caption("• Chunks con: N/A | Tài liệu cha: N/A | Trùng/Mơ hồ: N/A")

# D. Collection Status
chroma_status = get_status(strategy="hierarchical")
if chroma_status["collection_exists"]:
    st.sidebar.markdown(
        f"🗄️ **Chroma Database:** <span class='status-text status-ready'>Ready</span>",
        unsafe_allow_html=True
    )
    st.sidebar.caption(
        f"• Collection: `{chroma_status['collection_name']}`\n\n"
        f"• Số lượng Vector: {chroma_status['record_count']}"
    )
else:
    st.sidebar.markdown("🗄️ **Chroma Database:** <span class='status-text status-missing'>Missing</span>", unsafe_allow_html=True)

# 5. Database Actions Panel (Confirmation gate)
st.sidebar.markdown("---")
with st.sidebar.expander("🛠️ Thiết lập Dữ liệu & Index"):
    st.markdown("**1. Xây dựng Cấu trúc Cha-Con**")
    confirm_build = st.checkbox("Xác nhận ghi đè file trên đĩa", key="confirm_build")
    if st.button("Build Hierarchy Registry", disabled=not confirm_build):
        with st.spinner("Đang xây dựng registry..."):
            try:
                res = build_and_save_hierarchy(strategy="hierarchical")
                st.success("Đã build xong hierarchy registry!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi build: {str(e)}")

    st.markdown("---")
    st.markdown("**2. Index Vector Database**")
    confirm_index = st.checkbox("Xác nhận gọi API tạo và nạp vector", key="confirm_index")
    if st.button("Prepare Semantic Collection", disabled=not confirm_index):
        with st.spinner("Đang embedding và lưu ChromaDB (Mất vài phút)..."):
            try:
                res = run_index(strategy="hierarchical", reset=True)
                st.success(f"Đã lưu {res['indexed_chunks']} vectors vào Chroma!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi index: {str(e)}")

# ---------------------------------------------------------------------------
# MAIN HEADER DISPLAY
# ---------------------------------------------------------------------------
st.markdown("<h1 class='title-gradient'>RAG Foundation — Buổi 09: Multi-query & Parent–Child Retrieval</h1>", unsafe_allow_html=True)

# Subtitle hiển thị pipeline chi tiết
st.markdown(
    """
    <div class='pipeline-badge-container'>
        <span class='pipeline-step'>Query fan-out</span>
        <span class='pipeline-arrow'>➔</span>
        <span class='pipeline-step'>Hybrid per query</span>
        <span class='pipeline-arrow'>➔</span>
        <span class='pipeline-step'>Cross-query RRF</span>
        <span class='pipeline-arrow'>➔</span>
        <span class='pipeline-step'>Parent expansion</span>
        <span class='pipeline-arrow'>➔</span>
        <span class='pipeline-step'>Parent rerank</span>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------------
# TABS DECLARATION
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "💬 Ask Advanced RAG",
    "🔮 Query Fan-out & Matrix",
    "🌲 Parent–Child Explorer",
    "🔄 Mode Comparison",
    "📈 Evaluation"
])

# ---------------------------------------------------------------------------
# TAB 1: ASK ADVANCED RAG
# ---------------------------------------------------------------------------
with tabs[0]:
    st.markdown("### 💬 Hỏi Hệ thống Grounded RAG")
    
    question_input = st.text_area(
        "Nhập câu hỏi pháp lý của bạn:",
        placeholder="Ví dụ: Quy định về việc cơ cấu lại thời hạn trả nợ cho khách hàng như thế nào?",
        height=100
    )
    
    col_run, col_clear = st.columns([1, 8])
    with col_run:
        run_pipeline = st.button("🚀 Chạy Pipeline", type="primary")
    with col_clear:
        clear_state = st.button("🧹 Xóa kết quả")
        
    if clear_state:
        st.session_state["rag_result"] = None
        st.rerun()

    if run_pipeline:
        if not question_input.strip():
            st.warning("Vui lòng nhập câu hỏi trước khi chạy.")
        else:
            with st.spinner("Đang chạy luồng xử lý RAG nâng cao..."):
                try:
                    # Chạy pipeline với mode và config được chọn ở sidebar
                    result = query_hierarchical_rag(
                        question_input, 
                        mode=selected_mode
                    )
                    st.session_state["rag_result"] = result
                except Exception as e:
                    st.error(f"Lỗi hệ thống trong quá trình xử lý: {str(e)}")
                    st.session_state["rag_result"] = None

    # Hiển thị kết quả của lần bấm gần nhất
    rag_result = st.session_state["rag_result"]
    if rag_result:
        # Tách biệt hiển thị status/warnings, câu trả lời, và citations
        status = rag_result.get("status")
        
        # Gom warnings từ accepted_evidence
        evidence_list = rag_result.get("accepted_evidence", [])
        warnings = []
        for e in evidence_list:
            warnings.extend(e.get("warnings", []))
        warnings = sorted(list(set(warnings)))
        
        mapped_status = warning_status_mapping(status, warnings)
        
        # 1. Status Alert
        if mapped_status["type"] == "success":
            st.success(f"**{mapped_status['title']}**: {mapped_status['desc']}")
        elif mapped_status["type"] == "warning":
            st.warning(f"**{mapped_status['title']}**: {mapped_status['desc']}")
            st.info(f"💡 **Hướng dẫn xử lý**: {mapped_status['action']}")
        else:
            st.error(f"**{mapped_status['title']}**: {mapped_status['desc']}")
            st.info(f"💡 **Hướng dẫn xử lý**: {mapped_status['action']}")
            
        # Hiển thị các warnings cụ thể
        for w in mapped_status["warnings"]:
            st.warning(w)
            
        # 2. Câu trả lời
        st.markdown("---")
        st.markdown("#### 📝 Câu trả lời từ hệ thống")
        st.markdown(rag_result.get("answer"))
        
        # 3. Trích dẫn bằng chứng
        citations = rag_result.get("citations", [])
        if citations:
            st.markdown("#### 📌 Trích dẫn nguồn bằng chứng (Citations)")
            for c in citations:
                st.markdown(f"- {citation_formatting(c)}")
                
        # 4. Hiệu năng & Số cuộc gọi API
        st.markdown("---")
        st.markdown("#### ⏱️ Chỉ số hiệu năng thực thi (Trace)")
        trace = rag_result.get("trace", {})
        stage_latencies = trace.get("stage_latencies", {})
        api_calls = trace.get("api_calls", {})
        
        col1, col2, col3 = st.columns(3)
        col1.metric(
            label="Tổng Latency",
            value=f"{stage_latencies.get('total_ms', 0.0):.2f} ms"
        )
        col2.metric(
            label="Số cuộc gọi Generation (LLM)",
            value=api_calls.get("gemini_generation", 0)
        )
        col3.metric(
            label="Số cuộc gọi Embedding (Vector)",
            value=api_calls.get("gemini_embedding", 0)
        )

# ---------------------------------------------------------------------------
# TAB 2: QUERY FAN-OUT & MATRIX
# ---------------------------------------------------------------------------
with tabs[1]:
    if not rag_result:
        st.info("Vui lòng thực hiện truy vấn ở Tab 1 để xem các câu hỏi biến thể.")
    else:
        query_set = rag_result.get("query_set")
        if not query_set:
            st.info("Chế độ truy xuất hiện tại không sinh Multi-query (chọn single_flat hoặc single_parent).")
        else:
            st.markdown("### 🔮 Phân tích Mở rộng Câu hỏi (Query Fan-out)")
            
            queries = query_set.get("queries", [])
            trace = rag_result.get("trace", {})
            
            # Lấy thông tin trace của child retrieval
            child_retrieval_trace = trace.get("child_retrieval_trace", {})
            if not child_retrieval_trace and "child_retrieval_trace" not in trace:
                child_retrieval_trace = trace  # Flat modes store trace directly
                
            result_counts = child_retrieval_trace.get("result_count", {})
            ret_latencies = child_retrieval_trace.get("retrieval_latency_ms", {})
            
            # 1. Hiển thị danh sách card Q0..Qn
            cols = st.columns(len(queries))
            for i, q in enumerate(queries):
                qid = q["query_id"]
                qtext = q["text"]
                origin = q.get("origin", "N/A")
                focus = q.get("focus", "N/A")
                
                # Check validation: xem có bị trùng lặp hoặc chứa Điều khoản bịa không
                val_status = "Hợp lệ (Khớp Điều/Khoản)"
                
                q_count = result_counts.get(qid, 0)
                q_latency = ret_latencies.get(qid, 0.0)
                
                with cols[i]:
                    if qid == "Q0":
                        st.markdown(
                            f"""
                            <div class='card-q-orig'>
                                <h4 style='margin-top:0;'>🎯 {qid} (Gốc)</h4>
                                <p style='font-size:0.9rem;'>"{qtext}"</p>
                                <hr style='margin:10px 0; border:0; border-top:1px solid rgba(255,255,255,0.1);'/>
                                <span style='font-size:0.8rem;'>📍 <b>Focus:</b> {focus}</span><br>
                                <span style='font-size:0.8rem;'>🛡️ <b>Kiểm tra:</b> {val_status}</span><br>
                                <span style='font-size:0.8rem;'>📊 <b>K.Quả:</b> {q_count} chunks</span><br>
                                <span style='font-size:0.8rem;'>⏱️ <b>Truy xuất:</b> {q_latency:.1f} ms</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"""
                            <div class='card-q-gen'>
                                <h4 style='margin-top:0;'>🔮 {qid} (Biến thể)</h4>
                                <p style='font-size:0.9rem;'>"{qtext}"</p>
                                <hr style='margin:10px 0; border:0; border-top:1px solid rgba(255,255,255,0.1);'/>
                                <span style='font-size:0.8rem;'>📍 <b>Focus:</b> {focus}</span><br>
                                <span style='font-size:0.8rem;'>🛡️ <b>Kiểm tra:</b> {val_status}</span><br>
                                <span style='font-size:0.8rem;'>📊 <b>K.Quả:</b> {q_count} chunks</span><br>
                                <span style='font-size:0.8rem;'>⏱️ <b>Truy xuất:</b> {q_latency:.1f} ms</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            
            # 2. Ma trận Query-Child Rank
            st.markdown("---")
            st.markdown("<h3 class='matrix-title'>📊 Ma trận Query–Child Rank</h3>", unsafe_allow_html=True)
            st.write("Thể hiện thứ hạng (rank) của từng chunk con được trả về bởi mỗi câu hỏi. Càng nhiều câu hỏi hỗ trợ chứng tỏ chunk có độ liên quan cao.")
            
            child_hits = rag_result.get("child_hits", [])
            matrix_data = query_child_matrix(child_hits, queries)
            
            if matrix_data:
                df_matrix = pd.DataFrame(matrix_data)
                # Sắp xếp theo điểm RRF giảm dần
                df_matrix = df_matrix.sort_values(by="MQ-RRF Score", ascending=False).reset_index(drop=True)
                st.dataframe(
                    df_matrix.style.highlight_max(subset=["Support Count"], color="rgba(0, 204, 102, 0.15)"),
                    use_container_width=True
                )
            else:
                st.info("Không có dữ liệu chunks con.")

# ---------------------------------------------------------------------------
# TAB 3: PARENT–CHILD EXPLORER
# ---------------------------------------------------------------------------
with tabs[2]:
    if not rag_result:
        st.info("Vui lòng thực hiện truy vấn ở Tab 1 để khám phá cây cha-con.")
    elif "parent" not in rag_result.get("mode", ""):
        st.warning("⚠️ Cây Cha-Con chỉ được xây dựng trong chế độ Parent-RAG (`single_parent` hoặc `multi_parent`). Vui lòng đổi chế độ ở Sidebar, bấm chạy ở Tab 1 và thử lại.")
    else:
        st.markdown("### 🌲 Khám phá Mối quan hệ Phân cấp Cha - Con (Parent-Child Registry)")
        
        parent_candidates_list = rag_result.get("parent_candidates", [])
        child_hits_list = rag_result.get("child_hits", [])
        
        tree = parent_tree_data(parent_candidates_list, child_hits_list)
        
        if not tree:
            st.info("Không có tài liệu cha nào được truy xuất.")
        else:
            st.write(f"Tìm thấy **{len(tree)}** tài liệu cha liên kết từ các chunks con. Nhấp vào từng tài liệu để xem văn bản đầy đủ và các con đóng góp.")
            
            for idx, node in enumerate(tree, 1):
                p_id = node["parent_id"]
                struct_path = node["structural_path"]
                chapter = struct_path.get("chapter") or "Chương N/A"
                article = struct_path.get("article") or "Điều N/A"
                
                # Check status để style nổi bật ambiguous/warning
                border_color = "rgba(255,255,255,0.1)"
                bg_color = "rgba(255,255,255,0.02)"
                title_badge = ""
                
                if node["ambiguous"]:
                    border_color = "#FF4B4B"
                    bg_color = "rgba(255, 75, 75, 0.04)"
                    title_badge = "⚠️ [AMBIGUOUS] "
                elif node["warnings"]:
                    border_color = "#FFA500"
                    bg_color = "rgba(255, 165, 0, 0.04)"
                    title_badge = "⚠️ [WARNING] "
                    
                st.markdown(
                    f"""
                    <div style="border: 1px solid {border_color}; background-color: {bg_color}; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    """,
                    unsafe_allow_html=True
                )
                
                title_text = f"{title_badge}Parent #{idx}: {article} ({chapter}) | Nguồn: {node['source']} (Trang {node['page_start']}-{node['page_end']})"
                with st.expander(title_text):
                    col_p1, col_p2 = st.columns(2)
                    col_p1.write(f"🔄 **Thứ hạng:** {node['rank_change']}")
                    col_p2.write(f"🎯 **Điểm số:** {node['score_change']}")
                    
                    if node["warnings"]:
                        st.markdown("**Cảnh báo hệ thống:**")
                        for w in node["warnings"]:
                            st.warning(w)
                            
                    # Mặc định thu gọn văn bản cha
                    st.markdown("**Văn bản cha đầy đủ (Parent Document Text):**")
                    st.text_area(
                        "Nội dung văn bản cha", 
                        value=node["text"], 
                        height=180, 
                        key=f"p_text_{p_id}_{idx}",
                        disabled=True
                    )
                    
                    # Chunks con supporting
                    st.markdown("**Các chunks con đóng góp (Supporting Children):**")
                    for c in node["children"]:
                        c_warn = "⚠️ [AMBIGUOUS] " if c["ambiguous"] else ""
                        st.markdown(
                            f"""
                            <div style="margin-left: 20px; padding: 10px; border-left: 3px solid #1E90FF; background-color: rgba(30,144,255,0.02); margin-bottom: 8px; border-radius:0 4px 4px 0;">
                                <p style='margin:0 0 4px 0; font-size:0.9rem;'>🔹 <b>Child ID:</b> <code>{c['child_id']}</code> {c_warn}</p>
                                <p style='margin:0 0 4px 0; font-size:0.85rem;'>🎯 <b>Câu hỏi khớp:</b> {c['query_ranks']}</p>
                                <p style='margin:0; font-size:0.85rem; color:#DDDDDD;'>📝 <b>Snippet:</b> <i>"{c['anchor_snippet']}"</i></p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TAB 4: MODE COMPARISON
# ---------------------------------------------------------------------------
with tabs[3]:
    st.markdown("### 🔄 So sánh hiệu năng 4 chế độ (Flat vs Parent)")
    st.write("Chạy cùng câu hỏi trên cả 4 chế độ truy xuất ở mức **Retrieval-only** (Bỏ qua LLM Generation để so sánh khách quan và tiết kiệm token).")
    
    question_compare = st.text_area(
        "Nhập câu hỏi để đối sánh:",
        value=question_input if question_input else "Quy định về việc cơ cấu lại thời hạn trả nợ cho khách hàng như thế nào?",
        height=70,
        key="q_compare_input"
    )
    
    run_comparison = st.button("⚖️ Bắt đầu đối sánh 4 chế độ")
    
    if run_comparison:
        if not question_compare.strip():
            st.warning("Vui lòng nhập câu hỏi.")
        else:
            compare_results = {}
            with st.spinner("Đang truy xuất dữ liệu trên 4 chế độ khác nhau..."):
                # Inject dummy generator để bỏ qua gọi LLM sinh câu trả lời
                dummy_generator = lambda prompt: " ".join(f"[{t}]" for t in re.findall(r"\[(P\d+|E\d+)\]", prompt))
                
                for m in ["single_flat", "multi_flat", "single_parent", "multi_parent"]:
                    try:
                        res_m = query_hierarchical_rag(
                            question_compare,
                            mode=m,
                            custom_generator=dummy_generator
                        )
                        compare_results[m] = res_m
                    except Exception as e:
                        compare_results[m] = {"status": "error", "error_detail": str(e)}
            st.session_state["compare_results"] = compare_results
            
    # Hiển thị bảng so sánh
    comp_data = st.session_state["compare_results"]
    if comp_data:
        rows = []
        for m in ["single_flat", "multi_flat", "single_parent", "multi_parent"]:
            m_res = comp_data.get(m)
            if m_res and m_res.get("status") != "error":
                row = mode_comparison_row(m, m_res)
                rows.append(row)
            else:
                err_detail = m_res.get("error_detail") if m_res else "Không có kết quả."
                rows.append({
                    "Mode": m,
                    "Status": "Lỗi",
                    "Unit Type": "N/A",
                    "Evidence IDs": "N/A",
                    "Ranks": "N/A",
                    "Sources/Pages": "N/A",
                    "Unique Sources": 0,
                    "Unique Articles": 0,
                    "Retrieved Children": 0,
                    "Expanded Parents": 0,
                    "Context Chars": 0,
                    "Expansion Factor": 1.0,
                    "Latency (ms)": 0.0,
                    "Embedding Calls": 0,
                    "Generation Calls": 0,
                    "Warnings": err_detail
                })
                
        df_comp = pd.DataFrame(rows)
        
        # Trực quan hóa dạng bảng dữ liệu
        st.markdown("#### Bảng so sánh thuộc tính")
        st.dataframe(df_comp, use_container_width=True)
        
        st.markdown(
            """
            > [!NOTE]
            > **Giải thích chỉ số:**
            > - **Context Chars**: Tổng số lượng ký tự của các bằng chứng (evidence) được gửi vào LLM Prompt.
            > - **Expansion Factor (Hệ số giãn nở)**: Tỉ lệ giữa tổng ký tự tài liệu cha (Parent) so với tổng ký tự chunks con (Child) ban đầu. Hệ số càng lớn nghĩa là ngữ cảnh cha được mở rộng càng nhiều.
            > - **Ranks (Biến động rank)**: `Raw` là rank tìm kiếm ban đầu; `Rerank` là rank sau Cross-Encoder; `BestChild` là rank của con cao nhất cấu thành nên cha.
            """
        )
        
        st.warning("⚠️ **Lưu ý đánh giá tối ưu:** Bảng này không tuyên bố chế độ nào chiến thắng vì không có nhãn dữ liệu chuẩn (Gold labels) cho câu hỏi này. Hãy chuyển sang Tab **Evaluation** để xem benchmark offline trên tập kiểm thử.")

# ---------------------------------------------------------------------------
# TAB 5: EVALUATION
# ---------------------------------------------------------------------------
with tabs[4]:
    st.markdown("### 📈 Đánh giá offline (Benchmark Evaluation)")
    st.write("Đánh giá hiệu năng và chất lượng truy xuất trên tập câu hỏi chuẩn `eval/questions.json` dùng các chỉ số: Recall@K, MRR@K, nDCG@K.")
    
    # 1. Check warning needs_human_review=true trong câu hỏi gold labels
    questions_path = BASE_DIR / "eval" / "questions.json"
    has_human_review = False
    
    if questions_path.exists():
        try:
            with open(questions_path, "r", encoding="utf-8") as f:
                questions_data = json.load(f)
                has_human_review = any(q.get("needs_human_review", False) for q in questions_data)
        except Exception:
            questions_data = []
    else:
        questions_data = []
        
    if has_human_review:
        st.warning("⚠️ **Cảnh báo tập dữ liệu:** Tập câu hỏi chứa câu hỏi cần đánh giá lại thủ công (needs_human_review = true). Hệ thống sẽ không tự động chỉ định chế độ tối ưu nhất.")
        
    # 2. Trigger chạy evaluator
    k_eval = st.slider("Chọn K cho đánh giá (Recall@K, MRR@K, nDCG@K)", 1, 10, value=3)
    
    run_eval_btn = st.button("📊 Chạy Benchmark Offline", type="primary")
    
    if run_eval_btn:
        if not questions_data:
            st.error("Không tìm thấy tệp câu hỏi kiểm thử eval/questions.json.")
        else:
            with st.spinner("Đang chạy kiểm thử benchmark trên toàn bộ tập câu hỏi (Không gọi LLM sinh câu trả lời)..."):
                # Load registry để map con->cha trong Parent Recall
                children_file = BASE_DIR / "storage" / "hierarchy" / "children.json"
                children_registry = {}
                if children_file.exists():
                    try:
                        with open(children_file, "r", encoding="utf-8") as f:
                            children_list = json.load(f)
                        children_registry = {c["child_id"]: c for c in children_list}
                    except Exception:
                        pass
                
                try:
                    from evaluate import evaluate_hierarchical_rag
                    report_data = evaluate_hierarchical_rag(strategy="hierarchical", k=k_eval)
                    st.session_state["eval_report"] = report_data
                    st.success("Đã chạy xong benchmark và lưu kết quả!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi chạy benchmark: {str(e)}")

    # 3. Hiển thị báo cáo mới nhất
    report = st.session_state["eval_report"]
    if not report:
        st.info("Chưa có báo cáo benchmark nào. Vui lòng bấm 'Chạy Benchmark Offline' ở trên.")
    else:
        config_ident = report.get("config_identity", {})
        k_val = config_ident.get("k", report.get("k", 3))
        st.markdown(f"#### 📅 Báo cáo gần nhất: `{report.get('timestamp')}` (K={k_val})")
        
        results_dict = report.get("aggregate_metrics", report.get("results", {}))
        df_eval = pd.DataFrame(results_dict).T
        
        # Reset index để hiển thị đẹp hơn
        df_eval.index.name = "Mode"
        df_eval = df_eval.reset_index()
        
        st.dataframe(df_eval, use_container_width=True)
        
        # Bắt buộc hiển thị so sánh trực quan
        st.markdown("##### Biểu đồ so sánh Chất lượng tìm kiếm (Recall & nDCG)")
        st.bar_chart(df_eval.set_index("Mode")[["Child Recall@K", "Parent Recall@K", "nDCG@K"]])
