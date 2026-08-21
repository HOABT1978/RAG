import streamlit as st

import rag

st.set_page_config(
    page_title="RAG Workshop - Buổi 07",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 RAG System with Evidence Grounding & Citation - Buổi 07")
st.caption("Hệ thống RAG nâng cao với Semantic Indexing, Confidence Gate & Citation Mapping từ Metadata thật")

# ---------------------------------------------------------------------------
# 1. SIDEBAR: SYSTEM CONFIG & STATUS
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ Cấu hình & Trạng thái Buổi 07")

selected_strategy = st.sidebar.selectbox(
    "Chiến lược phân đoạn (Strategy):",
    ["hierarchical", "semantic", "fixed-size"],
    index=0
)

top_k = st.sidebar.number_input(
    "Số lượng Top-k truy vấn:",
    min_value=1,
    max_value=10,
    value=5
)

# Đọc trạng thái hệ thống ở chế độ read-only
st_info = rag.get_status(strategy=selected_strategy)

st.sidebar.divider()
st.sidebar.subheader("📊 Trạng thái Collection")

if st_info["has_api_key"]:
    st.sidebar.success("GEMINI_API_KEY: Đã sẵn sàng")
else:
    st.sidebar.error("GEMINI_API_KEY: Thiếu (Điền API key vào .env)")

st.sidebar.info(f"Embedding Model: `{st_info['embedding_model']}` ({st_info['embedding_dim']}d)")
st.sidebar.info(f"Generation Model: `{st_info['generation_model']}`")
st.sidebar.info(f"Max Distance Threshold: `{st_info['max_distance']}`")

st.sidebar.divider()
st.sidebar.write(f"**Collection Name:** `{st_info['collection_name']}`")
if st_info["collection_exists"]:
    st.sidebar.success(f"Tồn tại ({st_info['record_count']} records)")
else:
    st.sidebar.warning("Chưa tồn tại (0 records)")


# ---------------------------------------------------------------------------
# 2. MAIN AREA: INDEXING
# ---------------------------------------------------------------------------
st.subheader("🚀 Đánh chỉ mục Dữ liệu (Indexing)")

col_idx1, col_idx2 = st.columns([1, 4])
with col_idx1:
    reset_index = st.checkbox("Reset collection trước khi index", value=False)
    index_btn = st.button("🚀 Index Dữ Liệu", type="primary", use_container_width=True)

if index_btn:
    if not st_info["has_api_key"]:
        st.error("⚠️ Thiếu GEMINI_API_KEY trong file .env! Hãy bổ sung API key vào file .env để tiếp tục.")
    else:
        with st.spinner(f"Đang đọc JSON, tạo Gemini Embeddings và index cho strategy '{selected_strategy}'..."):
            try:
                res = rag.run_index(strategy=selected_strategy, reset=reset_index)
                st.session_state["last_index_res"] = res
                st.success(f"Đã index thành công {res['indexed_chunks']} chunks vào collection '{res['collection_name']}'!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi index dữ liệu: {str(e)}")

st.divider()


# ---------------------------------------------------------------------------
# 3. QUESTION AREA
# ---------------------------------------------------------------------------
st.subheader("❓ Đặt câu hỏi RAG")

question_input = st.text_area(
    "Nhập câu hỏi của bạn:",
    placeholder="Ví dụ: Quy định về việc cơ cấu lại thời hạn trả nợ và giữ nguyên nhóm nợ?",
    height=100
)

submit_btn = st.button("🔍 Gửi câu hỏi", type="primary")

if submit_btn:
    if not question_input.strip():
        st.warning("⚠️ Vui lòng nhập câu hỏi trước khi gửi.")
    elif not st_info["has_api_key"]:
        st.error("⚠️ Thiếu GEMINI_API_KEY trong file .env! Không thể gọi API khi thiếu key.")
    elif not st_info["collection_exists"] or st_info["record_count"] == 0:
        st.error(f"⚠️ Collection '{st_info['collection_name']}' chưa tồn tại hoặc rỗng (0 records). Vui lòng bấm 'Index Dữ Liệu' trước.")
    else:
        with st.spinner("Đang truy vấn Semantic Retrieval, Confidence Gate & Gemini Generation..."):
            try:
                q_res = rag.query_rag(
                    question=question_input.strip(),
                    top_k=int(top_k),
                    strategy=selected_strategy
                )
                st.session_state["last_query_res"] = q_res
            except Exception as e:
                st.error(f"Lỗi khi xử lý câu hỏi: {str(e)}")

st.divider()


# ---------------------------------------------------------------------------
# 4. ANSWER DISPLAY & CITATIONS
# ---------------------------------------------------------------------------
last_q = st.session_state.get("last_query_res")

if last_q:
    st.subheader("💡 Câu trả lời (Answer)")
    status = last_q.get("status")

    if status == "answered":
        st.success("Trạng thái: answered (Đã tổng hợp câu trả lời kèm trích dẫn)")
        st.markdown(last_q["answer"])
    elif status == "insufficient_evidence":
        st.warning("Trạng thái: insufficient_evidence (Không đủ bằng chứng đạt ngưỡng)")
        st.warning(last_q["answer"])
    elif status == "retrieval_only":
        st.info("Trạng thái: retrieval_only (Đã truy xuất nguồn nhưng Generation lỗi)")
        st.info(last_q["answer"])

    # Hiển thị Warnings nếu có
    if last_q.get("warnings"):
        with st.expander("⚠️ Cảnh báo trong quá trình xử lý (Warnings)"):
            for w in last_q["warnings"]:
                st.warning(w)

    # Hiển thị Citations đã map từ metadata thật
    if last_q.get("citations"):
        st.write("**📌 Danh sách Nguồn trích dẫn (Citations):**")
        for c in last_q["citations"]:
            st.markdown(f"- **{c['evidence_id']}**: {c['display']}")

    st.divider()

    # ---------------------------------------------------------------------------
    # 5. EVIDENCE DISPLAY
    # ---------------------------------------------------------------------------
    st.subheader("📚 Nguồn tham khảo")
    st.caption("Khoảng cách (Distance) càng thấp thể hiện độ tương đồng ngữ nghĩa càng cao. Khoảng cách không phải là xác suất.")

    evidence_list = last_q.get("evidence", [])
    if not evidence_list:
        st.info("Chưa có trích đoạn tham khảo.")
    else:
        for idx, e in enumerate(evidence_list, 1):
            p_str = f"tr. {e['page_start']}" if e["page_start"] == e["page_end"] else f"tr. {e['page_start']}-{e['page_end']}"
            acc_status = "ACCEPTED" if e["accepted"] else "REJECTED (distance > threshold)"

            title = f"[{e['evidence_id']}] {e['source']} – {p_str} – {e['chunk_id']} | Distance: {e['distance']} ({acc_status})"

            with st.expander(title, expanded=e["accepted"]):
                if e["accepted"]:
                    st.success("✅ ACCEPTED: Trích đoạn đạt ngưỡng khoảng cách RAG_MAX_DISTANCE và được đưa vào Generation Prompt.")
                else:
                    st.error("❌ REJECTED: Trích đoạn không đạt ngưỡng khoảng cách RAG_MAX_DISTANCE (Bị loại khỏi Generation Prompt).")

                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.write(f"**Source File:** `{e['source']}`")
                    st.write(f"**Chunk ID:** `{e['chunk_id']}`")
                with col_e2:
                    st.write(f"**Trang:** `{p_str}`")
                    st.write(f"**Cosine Distance:** `{e['distance']}`")

                st.text_area(
                    f"Nội dung chunk [{e['evidence_id']}]",
                    value=e["text"],
                    height=150,
                    disabled=True,
                    key=f"ev_text_{idx}"
                )
