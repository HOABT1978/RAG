import os
import streamlit as st
from dotenv import load_dotenv
import rag

load_dotenv()

st.set_page_config(
    page_title="RAG Workshop Demo - Buổi 06",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 RAG System with Evidence Grounding - Buổi 06")
st.caption("Hệ thống RAG kiểm chứng bằng chứng (Evidence), trích dẫn Metadata thật & chống Vector giả")

# --- SIDEBAR: System Status ---
st.sidebar.header("⚙️ Trạng thái Hệ thống")

rag_status = rag.status()
db_storage = rag_status.get("db_storage", "sqlite")
num_chunks = rag_status.get("num_chunks", 0)
num_docs = rag_status.get("num_documents", 0)

# 1. PostgreSQL / SQLite Status
if db_storage == "postgres":
    st.sidebar.success("PostgreSQL: Đang hoạt động (`rag_db`)")
else:
    st.sidebar.info("Database Storage: Local SQLite (`storage/rag.db`)")

# 2. ChromaDB Status
st.sidebar.info("ChromaDB: Persistent Local (`storage/chroma/`)")

# 3. Gemini API Key Status
api_key = os.getenv("GEMINI_API_KEY", "").strip()
has_api_key = bool(api_key)

if has_api_key:
    st.sidebar.success("Gemini API Key: Đã sẵn sàng")
else:
    st.sidebar.error("Gemini API Key: Thiếu (Yêu cầu GEMINI_API_KEY trong .env)")

st.sidebar.divider()
st.sidebar.metric("Số lượng Documents", num_docs)
st.sidebar.metric("Số lượng Chunks trong Vector DB", num_chunks)

# --- MAIN AREA ---

# Indexing Section
col_idx1, col_idx2 = st.columns([1, 4])
with col_idx1:
    if st.button("🚀 Index Data từ Buổi 05", type="primary", use_container_width=True):
        with st.spinner("Đang đọc JSON từ Buổi 05, kiểm tra dữ liệu và tạo embeddings..."):
            try:
                res = rag.index()
                if res.get("status") == "indexed":
                    st.success(f"Đã đánh chỉ mục {res['num_chunks']} chunks từ {res['num_documents']} tài liệu!")
                    st.rerun()
                else:
                    st.error(res.get("message", "Lỗi đánh chỉ mục!"))
            except Exception as e:
                st.error(f"Lỗi khi đánh chỉ mục: {str(e)}")

st.divider()

# Question & Retrieval Section
st.subheader("❓ Đặt câu hỏi RAG")

col_q1, col_q2 = st.columns([4, 1])
with col_q1:
    question = st.text_input("Nhập câu hỏi của bạn:", placeholder="Ví dụ: Quy định về việc cơ cấu lại thời hạn trả nợ theo Thông tư 02?")
with col_q2:
    top_k = st.number_input("Top-k", min_value=1, max_value=10, value=3)

submit_btn = st.button("🔍 Tìm kiếm & Trả lời")

if submit_btn and question.strip():
    with st.spinner("Đang truy vấn Semantic Top-k & Gemini tổng hợp câu trả lời..."):
        result = rag.ask(question.strip(), k=top_k)

    st.divider()

    # 1. Answer Display
    st.subheader("💡 Câu trả lời (Answer & Evidence)")
    if "Tài liệu không đủ thông tin" in result["answer"]:
        st.warning(result["answer"])
    elif result["answer"].startswith("⚠️"):
        st.error(result["answer"])
    else:
        st.markdown(result["answer"])

    st.divider()

    # 2. Top-k Chunks Display
    st.subheader(f"📚 Trích đoạn Bằng chứng (Top-{len(result['chunks'])} Chunks)")

    if result["chunks"]:
        for idx, chunk in enumerate(result["chunks"], 1):
            with st.expander(f"Chunk #{idx} | Nguồn: {chunk.get('source', 'N/A')} | Trang: {chunk.get('page_start')}-{chunk.get('page_end')} | Chunk ID: {chunk.get('chunk_id')}"):
                st.markdown(f"**Strategy:** `{chunk.get('strategy', 'N/A')}` | **File:** `{chunk.get('source')}` | **Pages:** `{chunk.get('page_start')}-{chunk.get('page_end')}`")
                st.text_area(f"Nội dung Chunk #{idx}", chunk.get("text", ""), height=150, disabled=True, key=f"chunk_{idx}")
    else:
        st.info("Không tìm thấy chunk bằng chứng phù hợp trong cơ sở dữ liệu. Hãy đảm bảo dữ liệu đã được Index.")
