import os
import sys
import re
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Configure imports from local directory
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

from src.secure_retriever import SecureRetriever
from src.config import VALID_ROLES

# Set Page Config
st.set_page_config(
    page_title="Secure RAG System with RBAC — Buổi 15",
    page_icon="🛡️",
    layout="wide"
)

# Load env variables
load_dotenv(dotenv_path=script_dir / ".env", override=True)
api_key = os.getenv("GEMINI_API_KEY")

# Resource caching for secure retriever
@st.cache_resource
def init_secure_retriever():
    secure_csv_path = script_dir / "data" / "processed" / "chunks_secure.csv"
    embeddings_path = script_dir.parent / "kb+hops" / "chunks_embedded.json"
    
    if not secure_csv_path.exists():
        st.error(f"Error: Secure corpus not found at {secure_csv_path}. Please run assign_security_tags.py first.")
        st.stop()
        
    return SecureRetriever(secure_csv_path, embeddings_path, api_key)

# Initialize retriever
try:
    retriever = init_secure_retriever()
except Exception as e:
    st.error(f"Failed to initialize SecureRetriever: {e}")
    st.stop()

# Title
st.title("🛡️ Secure RAG & RBAC Pipeline — Buổi 15")
st.markdown("---")

if not api_key:
    st.warning("⚠️ Cảnh báo: `GEMINI_API_KEY` chưa được cấu hình. Bộ tìm kiếm ngữ nghĩa sẽ hoạt động ở chế độ fallback Jaccard.")

# SIDEBAR: RBAC CONFIGURATION
st.sidebar.header("🔑 Cấu hình Phân quyền (RBAC)")
user_roles = st.sidebar.multiselect(
    "Vai trò hiện tại của bạn:",
    options=VALID_ROLES,
    default=["Guest"],
    help="Chọn một hoặc nhiều vai trò để đóng vai (Impersonate) truy vấn hệ thống."
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Thông số tìm kiếm")

method_label = st.sidebar.selectbox(
    "Phương pháp tìm kiếm",
    ["Hybrid + Rerank", "Hybrid (RRF)", "BM25 (Từ khóa)", "Dense (Ngữ nghĩa)"]
)
method_map = {
    "BM25 (Từ khóa)": "bm25",
    "Dense (Ngữ nghĩa)": "dense",
    "Hybrid (RRF)": "hybrid",
    "Hybrid + Rerank": "hybrid_rerank"
}
method = method_map[method_label]

top_k = st.sidebar.number_input("Top-k hiển thị", min_value=1, max_value=20, value=5)
candidate_k = st.sidebar.number_input("Candidate-k (Số Candidate từ Hybrid)", min_value=1, max_value=100, value=20)

# MAIN WORKSPACE: SEARCH FORM
col_query, col_btn = st.columns([8, 2])
with col_query:
    query = st.text_input("Nhập câu hỏi pháp lý của bạn:", placeholder="Ví dụ: 'Quy trình vận chuyển tiền mặt', 'Kỷ luật nhân viên làm mất chìa khóa'...")

with col_btn:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    search_clicked = st.button("Tìm kiếm an toàn", type="primary", use_container_width=True)

if (search_clicked or query) and query:
    if not user_roles:
        st.error("Vui lòng chọn ít nhất một vai trò ở Sidebar để thực hiện truy vấn.")
    else:
        with st.spinner("Hệ thống đang kiểm tra quyền và truy xuất dữ liệu an toàn..."):
            # 1. Retrieve authorized results
            results = retriever.retrieve(query, user_roles=user_roles, method=method, top_k=top_k, candidate_k=candidate_k)
            
            # 2. Audit check: Calculate if any candidates were filtered out (top 50 check)
            all_candidates = retriever.retrieve(query, user_roles=VALID_ROLES, method=method, top_k=50, candidate_k=max(50, candidate_k))
            user_auth_candidates = retriever.retrieve(query, user_roles=user_roles, method=method, top_k=50, candidate_k=max(50, candidate_k))
            
            auth_chunk_ids = {item['chunk_id'] for item in user_auth_candidates}
            filtered_out_count = sum(1 for item in all_candidates if item['chunk_id'] not in auth_chunk_ids)
            
            # Display warning if documents are filtered out
            if filtered_out_count > 0:
                st.warning(f"🔒 Bảo mật: Đã lọc bỏ **{filtered_out_count}** kết quả phù hợp trong Top 50 do vai trò của bạn ({user_roles}) không đủ quyền truy cập.")
            
            if not results:
                st.info("Không tìm thấy kết quả nào phù hợp với câu hỏi và vai trò hiện tại của bạn.")
            else:
                main_col, side_col = st.columns([7, 3])
                
                with main_col:
                    st.subheader(f"Kết quả Truy xuất ({method_label})")
                    for item in results:
                        # Color coding tags based on allowed_roles length
                        roles_list = item['allowed_roles']
                        if "Guest" in roles_list:
                            badge_color = "#10B981"  # Emerald Green
                            sec_level = "Công cộng"
                        elif "Risk_Manager" in roles_list and not "Guest" in roles_list:
                            badge_color = "#F59E0B"  # Amber Orange
                            sec_level = "Rủi ro tín dụng"
                        else:
                            badge_color = "#EF4444"  # Red
                            sec_level = "Nhân sự / Nội bộ"
                            
                        # Find which of the user's active roles matched
                        matching_roles = [r for r in roles_list if r in user_roles]
                        matching_str = ", ".join(matching_roles) if matching_roles else "Không trùng khớp"
                        
                        header_title = f"Hạng {item['rank']} | Chunk: {item['chunk_id']} | Document: {item['document_id']} (Score: {item['score']:.4f})"
                        with st.expander(header_title, expanded=True):
                            st.markdown(
                                f"🔑 **Yêu cầu quyền**: <span style='color:{badge_color}; font-weight:bold;'>{roles_list} ({sec_level})</span> | "
                                f"✅ **Vai trò khớp của bạn**: <span style='background-color:rgba(16, 185, 129, 0.15); color:#10B981; padding:2px 8px; border-radius:4px; font-weight:bold;'>{matching_str}</span>", 
                                unsafe_allow_html=True
                            )
                            st.markdown(f"**Citation**: `{item['citation']}`")
                            st.write(item['text'])
                            
                with side_col:
                    # Rank comparison for hybrid_rerank
                    if method == 'hybrid_rerank':
                        st.subheader("📊 Reranking Comparison")
                        comparison_data = []
                        for item in results:
                            comparison_data.append({
                                "Chunk ID": item['chunk_id'],
                                "Hạng cũ": item['hybrid_rank'],
                                "Hạng mới": item['rank'],
                                "Điểm Rerank": round(item['score'], 4)
                            })
                        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
                        
                    elif method == 'hybrid':
                        st.subheader("📊 Score Details")
                        comparison_data = []
                        for item in results:
                            comparison_data.append({
                                "Chunk ID": item['chunk_id'],
                                "Hạng BM25": item.get('bm25_rank', '-'),
                                "Hạng Dense": item.get('dense_rank', '-'),
                                "Điểm RRF": round(item['score'], 4)
                            })
                        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
                        
                    # Graph hints section (secured)
                    st.subheader("🕸️ Graph Hints (Bảo mật)")
                    doc_ids = list(set([item['document_id'] for item in results]))
                    chunk_ids = list(set([item['chunk_id'] for item in results]))
                    
                    hints = retriever.get_graph_hints(doc_ids, chunk_ids, user_roles=user_roles)
                    
                    if hints is None:
                        st.info("ℹ️ Neo4j Database chưa sẵn sàng hoặc sai thông tin kết nối.")
                    else:
                        st.markdown("**Mối quan hệ chứa đựng (CONTAINS):**")
                        if hints['contains_relations']:
                            for r in hints['contains_relations']:
                                st.caption(r)
                        else:
                            st.caption("*Không tìm thấy hoặc không có quyền*")
                            
                        st.markdown("**Mối quan hệ liền kề (NEXT):**")
                        if hints['next_relations']:
                            for r in hints['next_relations']:
                                st.caption(r)
                        else:
                            st.caption("*Không tìm thấy hoặc không có quyền*")
                            
                        st.markdown("**Mối quan hệ liên văn bản:**")
                        if hints['doc_relations']:
                            for r in hints['doc_relations']:
                                st.caption(r)
                        else:
                            st.caption("*Không tìm thấy hoặc không có quyền*")
