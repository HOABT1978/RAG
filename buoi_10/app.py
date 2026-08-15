"""
Streamlit Dashboard - Buổi 10 & 11: Multi-hop Graph RAG & QA
Giao diện trực quan hóa tìm kiếm đồ thị đa bước và so sánh mức độ cải thiện của ngữ cảnh.
"""

import streamlit as st
import pandas as pd
import json
import time
import re
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModel
from neo4j import GraphDatabase
from google import genai
from google.genai import types

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Graph RAG Explorer — Buổi 10 & 11",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện tối giản hiện đại (Premium Dark Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .logo-text {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ff4b4b, #8a2be2, #00bfff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .card {
        background-color: rgba(22, 26, 37, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
    }
    
    .badge-0 { background-color: rgba(255, 75, 75, 0.15); color: #ff4b4b; border: 1px solid rgba(255, 75, 75, 0.3); }
    .badge-1 { background-color: rgba(0, 191, 255, 0.15); color: #00bfff; border: 1px solid rgba(0, 191, 255, 0.3); }
    .badge-2 { background-color: rgba(138, 43, 226, 0.15); color: #8a2be2; border: 1px solid rgba(138, 43, 226, 0.3); }
    
    .citation-container {
        font-size: 0.9rem;
        border-left: 3px solid #8a2be2;
        padding-left: 15px;
        margin-bottom: 12px;
        background-color: rgba(138, 43, 226, 0.03);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 1. TẢI RESOURCE LÀM SẠCH VÀ VECTOR NHÚNG (LAZY LOADING)
# ---------------------------------------------------------------------------

@st.cache_resource
def load_embedding_model():
    """Tải model thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5 một lần duy nhất."""
    model_name = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    return tokenizer, model

def embed_text(text, tokenizer, model):
    """Trích xuất dense embedding vector (384 dimensions) của câu hỏi trên CPU."""
    encoded_input = tokenizer([text], padding=True, truncation=True, max_length=512, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
    token_embeddings = model_output[0]
    attention_mask = encoded_input['attention_mask']
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    emb = sum_embeddings / sum_mask
    emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb[0].cpu().numpy().tolist()

# ---------------------------------------------------------------------------
# 2. TRUY VẤN MULTI-HOP TRÊN NEO4J
# ---------------------------------------------------------------------------

def run_multihop_search(driver, db_name, query_vector, k=5, hops=0):
    """
    Truy vấn vector kết hợp duyệt quan hệ đa bước (multi-hop) giữa các tài liệu.
    Hops = 0: Tìm kiếm vector trên Chunks thô thông thường.
    Hops = 1: Tìm kiếm vector + lấy Chunks của các Document liên kết trực tiếp (1 bước).
    Hops = 2: Tìm kiếm vector + lấy Chunks của các Document liên kết chéo cấp 2 (2 bước).
    """
    if hops == 0:
        cypher = """
        CALL db.index.vector.queryNodes('chunk_embeddings_idx', $k, $query_vector)
        YIELD node, score
        MATCH (node)-[:PART_OF]->(d:Document)
        RETURN node.chunk_id AS chunk_id, node.text AS text, node.type AS type,
               d.id AS doc_id, d.title AS doc_title, score AS similarity,
               [] AS paths
        ORDER BY similarity DESC
        """
    elif hops == 1:
        cypher = """
        CALL db.index.vector.queryNodes('chunk_embeddings_idx', $k, $query_vector)
        YIELD node, score
        MATCH (node)-[:PART_OF]->(d1:Document)
        OPTIONAL MATCH (d1)-[r]-(d2:Document)
        WHERE type(r) IN ['CAN_CU', 'THAY_THE', 'HOP_NHAT', 'SUA_DOI_BO_SUNG', 'VAN_BAN_BO_SUNG']
        WITH node, d1, d2, type(r) AS rel_type, r.relationship AS rel_desc
        WITH collect(distinct d1) + collect(distinct d2) AS docs,
             collect({seed_chunk: node.chunk_id, from_doc: d1.id, rel: rel_type, desc: rel_desc, to_doc: d2.id}) AS path_details
        UNWIND docs AS doc
        MATCH (c:Chunk)-[:PART_OF]->(doc)
        WITH c, doc, vector.similarity.cosine(c.embedding, $query_vector) AS similarity, path_details
        ORDER BY similarity DESC
        LIMIT $k
        WITH c, doc, similarity,
             [p in path_details WHERE p.to_doc = doc.id or p.from_doc = doc.id] AS paths
        RETURN c.chunk_id AS chunk_id, c.text AS text, c.type AS type,
               doc.id AS doc_id, doc.title AS doc_title, similarity,
               paths
        ORDER BY similarity DESC
        """
    else:  # hops = 2
        cypher = """
        CALL db.index.vector.queryNodes('chunk_embeddings_idx', $k, $query_vector)
        YIELD node, score
        MATCH (node)-[:PART_OF]->(d1:Document)
        OPTIONAL MATCH p_path = (d1)-[r*1..2]-(d2:Document)
        WHERE all(x in relationships(p_path) WHERE type(x) IN ['CAN_CU', 'THAY_THE', 'HOP_NHAT', 'SUA_DOI_BO_SUNG', 'VAN_BAN_BO_SUNG'])
        WITH node, d1, d2, relationships(p_path) AS rels
        WITH collect(distinct d1) + collect(distinct d2) AS docs,
             collect({seed_chunk: node.chunk_id, from_doc: d1.id, to_doc: d2.id}) AS path_details
        UNWIND docs AS doc
        MATCH (c:Chunk)-[:PART_OF]->(doc)
        WITH c, doc, vector.similarity.cosine(c.embedding, $query_vector) AS similarity, path_details
        ORDER BY similarity DESC
        LIMIT $k
        WITH c, doc, similarity,
             [p in path_details WHERE p.to_doc = doc.id or p.from_doc = doc.id] AS paths
        RETURN c.chunk_id AS chunk_id, c.text AS text, c.type AS type,
               doc.id AS doc_id, doc.title AS doc_title, similarity,
               paths
        ORDER BY similarity DESC
        """
        
    try:
        with driver.session(database=db_name) as session:
            result = session.run(cypher, {"query_vector": query_vector, "k": k})
            records = []
            for rec in result:
                records.append({
                    "chunk_id": rec["chunk_id"],
                    "text": rec["text"],
                    "type": rec["type"],
                    "doc_id": rec["doc_id"],
                    "doc_title": rec["doc_title"],
                    "similarity": rec["similarity"],
                    "paths": rec["paths"]
                })
            return records
    except Exception as e:
        st.error(f"Lỗi chạy truy vấn Cypher: {e}")
        return []

# ---------------------------------------------------------------------------
# 3. KẾT NỐI GEMINI API SINH CÂU TRẢ LỜI
# ---------------------------------------------------------------------------

def generate_rag_answer(api_key, model_name, query, context_items):
    """Gọi Gemini API sử dụng SDK mới 'google-genai' để tổng hợp câu trả lời."""
    if not api_key:
        return "⚠️ Vui lòng nhập Gemini API Key ở thanh Sidebar để sinh câu trả lời tự động."
        
    context_str = ""
    for idx, item in enumerate(context_items):
        context_str += f"[{idx+1}] Phân đoạn {item['chunk_id']} (Tài liệu: {item['doc_title']}):\n{item['text']}\n\n"
        
    prompt = f"""Bạn là một trợ lý tư vấn pháp luật chuyên nghiệp. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng dựa trên các ngữ cảnh pháp luật được cung cấp dưới đây.

Ngữ cảnh cung cấp:
{context_str}

Câu hỏi của người dùng: {query}

Yêu cầu trả lời:
1. Trả lời rõ ràng, đúng trọng tâm pháp lý bằng tiếng Việt.
2. Trích dẫn rõ nguồn gốc thông tin bằng cách gắn số hiệu nguồn ngữ cảnh (ví dụ: [1], [2]) ở cuối các câu khẳng định tương ứng.
3. Chỉ sử dụng thông tin trong ngữ cảnh được cung cấp. Nếu ngữ cảnh không đủ thông tin, hãy trả lời: 'Dựa trên ngữ cảnh cung cấp, tôi không tìm thấy đủ thông tin để trả lời câu hỏi này.' Không tự suy đoán hoặc tự sinh thông tin.
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ Lỗi gọi Gemini API: {e}"

# ---------------------------------------------------------------------------
# 4. GIAO DIỆN CHÍNH
# ---------------------------------------------------------------------------

def main():
    st.markdown('<div class="logo-text">Graph RAG Dashboard</div>', unsafe_allow_html=True)
    st.markdown("##### Phân tích Truy vấn Đồ thị Đa bước & Hỏi đáp Pháp luật (Buổi 10 & 11)")
    st.write("---")

    # SIDEBAR: CẤU HÌNH KẾT NỐI & THÔNG SỐ
    st.sidebar.markdown("### 🔌 Kết nối Neo4j")
    neo4j_uri = st.sidebar.text_input("Bolt Connection URL", value=NEO4J_URI)
    neo4j_user = st.sidebar.text_input("User Name", value=NEO4J_USER)
    neo4j_password = st.sidebar.text_input("Password", type="password", value=NEO4J_PASSWORD)
    neo4j_db = st.sidebar.text_input("Database Name", value=NEO4J_DB)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 Cấu hình Gemini")
    gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
    gemini_model = st.sidebar.selectbox("Gemini Model", options=["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro"])

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Tham số Retrieval")
    k_val = st.sidebar.slider("Số lượng Chunks phù hợp nhất (K)", min_value=1, max_value=20, value=5)

    # Khởi tạo mô hình embedding (lazy-loaded)
    try:
        tokenizer, model = load_embedding_model()
        st.sidebar.success("✅ Đã tải Model Embedding thành công (CPU).")
    except Exception as e:
        st.sidebar.error(f"❌ Lỗi tải Model Embedding: {e}")
        return

    # Kết nối Driver Neo4j
    driver = None
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        driver.verify_connectivity()
        st.sidebar.success("✅ Đã kết nối Neo4j Instance thành công!")
    except Exception as e:
        st.sidebar.error(f"❌ Neo4j Offline: {e}")
        st.sidebar.info("💡 Vui lòng bật Neo4j Desktop và Start Database Instance của bạn.")

    # TABS CHỨC NĂNG
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Hỏi đáp Graph RAG",
        "⚖️ So sánh Hop Levels (0-1-2)",
        "📋 5 Câu hỏi Kiểm thử (Lab 2)",
        "🌲 Khám phá Đồ thị (Graph Explorer)"
    ])

    # -----------------------------------------------------------------------
    # TAB 1: HỎI ĐÁP GRAPH RAG
    # -----------------------------------------------------------------------
    with tab1:
        st.markdown("### 🔍 Truy vấn Đồ thị Đa bước nâng cao")
        
        col_q, col_h = st.columns([4, 1])
        with col_q:
            query_input = st.text_input("Nhập câu hỏi pháp lý của bạn:", value="Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào?")
        with col_h:
            hops_val = st.selectbox("Số bước nhảy (Hops)", options=[0, 1, 2], index=1)
            
        if st.button("Truy vấn & Trả lời"):
            if not query_input.strip():
                st.warning("Vui lòng nhập câu hỏi.")
            elif not driver:
                st.error("Neo4j chưa được kết nối.")
            else:
                with st.spinner("Đang sinh vector nhúng và truy vấn Neo4j..."):
                    # 1. Embed query
                    t_emb_0 = time.time()
                    q_vector = embed_text(query_input, tokenizer, model)
                    t_emb = time.time() - t_emb_0
                    
                    # 2. Run multi-hop retrieval
                    t_ret_0 = time.time()
                    retrieved_chunks = run_multihop_search(driver, neo4j_db, q_vector, k=k_val, hops=hops_val)
                    t_ret = time.time() - t_ret_0
                    
                if not retrieved_chunks:
                    st.info("Không tìm thấy kết quả nào phù hợp.")
                else:
                    st.success(f"Đã tìm thấy {len(retrieved_chunks)} phân đoạn phù hợp.")
                    
                    # 3. Call Gemini
                    with st.spinner("Gemini đang tổng hợp câu trả lời từ ngữ cảnh..."):
                        t_gen_0 = time.time()
                        answer = generate_rag_answer(gemini_key, gemini_model, query_input, retrieved_chunks)
                        t_gen = time.time() - t_gen_0
                        
                    # Hiển thị câu trả lời sinh bởi Gemini
                    st.markdown("#### 💬 Trả lời từ Trợ lý:")
                    st.write(answer)
                    
                    # Hiển thị thống kê thời gian
                    st.markdown("---")
                    st.markdown("#### ⏱️ Thống kê hiệu năng:")
                    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
                    col_t1.metric("Tổng thời gian", f"{t_emb + t_ret + t_gen:.3f} s")
                    col_t2.metric("Thời gian Nhúng", f"{t_emb:.3f} s")
                    col_t3.metric("Truy vấn Đồ thị", f"{t_ret:.3f} s")
                    col_t4.metric("Thời gian LLM", f"{t_gen:.3f} s")
                    
                    # Hiển thị các phân đoạn ngữ cảnh (Citations)
                    st.markdown("#### 📖 Ngữ cảnh chi tiết (Citations):")
                    for idx, item in enumerate(retrieved_chunks):
                        with st.expander(f"[{idx+1}] Chunks {item['chunk_id']} - {item['doc_title']} (Độ tương đồng: {item['similarity']:.4f})"):
                            # Minh họa đường đi (Hop Path)
                            if item["paths"]:
                                st.markdown("**Đường đi đa bước trên đồ thị:**")
                                for p in item["paths"]:
                                    if p.get("rel"):
                                        st.markdown(f"`[Seed Chunk: {p['seed_chunk']}]` ➔ (Tài liệu gốc: `{p['from_doc']}`) ➔ `[:{p['rel']} ({p['desc']})]` ➔ (Tài liệu liên quan: `{p['to_doc']}`) ➔ `[Chunk này]`")
                                    else:
                                        st.markdown(f"`[Seed Chunk: {p['seed_chunk']}]` ➔ (Tài liệu gốc: `{p['from_doc']}`) ➔ (Tài liệu này)")
                            
                            st.markdown("**Nội dung đoạn văn:**")
                            st.write(item["text"])

    # -----------------------------------------------------------------------
    # TAB 2: SO SÁNH HOP LEVELS (0-1-2)
    # -----------------------------------------------------------------------
    with tab2:
        st.markdown("### ⚖️ So sánh hiệu quả ngữ cảnh đa bước (Multi-hop)")
        st.write("Dịch chuyển số lượng bước nhảy giúp thu thập các văn bản luật liên đới từ các tài liệu khác nhau. Hãy kiểm thử sự khác biệt:")
        
        compare_query = st.text_input("Nhập câu hỏi để so sánh:", value="Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào và hồ sơ cấp phép gồm gì?")
        
        if st.button("Bắt đầu So sánh Hop Levels"):
            if not compare_query.strip():
                st.warning("Vui lòng nhập câu hỏi.")
            elif not driver:
                st.error("Neo4j chưa được kết nối.")
            else:
                q_vector = embed_text(compare_query, tokenizer, model)
                
                cols = st.columns(3)
                hop_levels = [0, 1, 2]
                
                for col, hop in zip(cols, hop_levels):
                    with col:
                        st.markdown(f"#### <span class='badge badge-{hop}'>{hop}-Hop Retrieval</span>", unsafe_allow_html=True)
                        t0 = time.time()
                        retrieved = run_multihop_search(driver, neo4j_db, q_vector, k=k_val, hops=hop)
                        t_ret = time.time() - t0
                        
                        unique_docs = len(set(r["doc_id"] for r in retrieved))
                        total_chars = sum(len(r["text"]) for r in retrieved)
                        
                        st.metric("Thời gian truy vấn", f"{t_ret:.3f} s")
                        st.write(f"• Số tài liệu khác nhau: **{unique_docs}**")
                        st.write(f"• Tổng số ký tự ngữ cảnh: **{total_chars}**")
                        
                        # Hiển thị danh sách tài liệu lấy được
                        doc_titles = list(set(r["doc_title"] for r in retrieved))
                        st.markdown("**Tài liệu tham chiếu:**")
                        for d in doc_titles:
                            st.write(f"- *{d}*")
                            
                        # Gọi Gemini sinh câu trả lời
                        st.markdown("**Câu trả lời sinh ra:**")
                        with st.spinner("Gemini đang trả lời..."):
                            ans = generate_rag_answer(gemini_key, gemini_model, compare_query, retrieved)
                        st.write(ans)
                        st.write("---")

    # -----------------------------------------------------------------------
    # TAB 3: 5 CÂU HỎI KIỂM THỬ (LAB 2)
    # -----------------------------------------------------------------------
    with tab3:
        st.markdown("### 📋 5 Câu hỏi tra cứu luật phức tạp (Buổi 11)")
        st.write("Đây là 5 câu hỏi tình huống mẫu cần thông tin liên kết đa bước để trả lời đầy đủ:")
        
        test_questions = [
            "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?",
            "Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?",
            "Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?",
            "Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?",
            "Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?"
        ]
        
        selected_q = st.selectbox("Chọn câu hỏi kiểm thử:", options=test_questions)
        
        if st.button("Chạy câu hỏi này trên cả 3 mức Hops và xuất báo cáo"):
            if not driver:
                st.error("Neo4j chưa được kết nối.")
            else:
                q_vector = embed_text(selected_q, tokenizer, model)
                
                st.markdown(f"#### Câu hỏi: *{selected_q}*")
                
                results_comparison = []
                
                for hop in [0, 1, 2]:
                    st.write(f"⏳ Đang chạy truy vấn với {hop}-Hop...")
                    retrieved = run_multihop_search(driver, neo4j_db, q_vector, k=k_val, hops=hop)
                    ans = generate_rag_answer(gemini_key, gemini_model, selected_q, retrieved)
                    
                    doc_ids = set(r["doc_id"] for r in retrieved)
                    total_chars = sum(len(r["text"]) for r in retrieved)
                    
                    results_comparison.append({
                        "hop": hop,
                        "docs": doc_ids,
                        "chars": total_chars,
                        "answer": ans
                    })
                    
                # Vẽ so sánh
                st.markdown("### Kết quả so sánh đối chứng:")
                for r in results_comparison:
                    st.markdown(f"##### Mức độ: **{r['hop']}-Hop** (Ng ngữ cảnh: {r['chars']} ký tự, từ {len(r['docs'])} tài liệu)")
                    st.write(r['answer'])
                    st.write("---")
                    
        st.write("---")
        st.markdown("#### 📝 Xuất báo cáo tự động (`qa_comparison.md`)")
        st.write("Nhấn nút dưới đây để hệ thống tự động chạy toàn bộ 5 câu hỏi này qua các mức Hops (0, 1, 2) và xuất báo cáo đối chứng chi tiết vào thư mục dự án.")
        
        if st.button("Chạy toàn bộ 5 câu hỏi & Xuất file qa_comparison.md"):
            if not driver:
                st.error("Neo4j chưa được kết nối.")
            elif not gemini_key:
                st.error("Vui lòng cung cấp Gemini API Key để thực hiện sinh câu trả lời đánh giá.")
            else:
                progress_bar = st.progress(0)
                report_content = f"# Báo cáo đánh giá và so sánh chất lượng ngữ cảnh Đa bước (Multi-hop Graph RAG)\n"
                report_content += f"Thời gian thực hiện: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                report_content += "Báo cáo này so sánh câu trả lời nhận được khi thay đổi số bước nhảy (0-hop, 1-hop, 2-hop) trên 5 câu hỏi kiểm thử mẫu.\n\n"
                
                for idx, q in enumerate(test_questions):
                    st.write(f" đang xử lý Câu hỏi {idx+1}...")
                    q_vector = embed_text(q, tokenizer, model)
                    
                    report_content += f"## Câu hỏi {idx+1}: {q}\n\n"
                    report_content += "| Chỉ số | 0-Hop (Không nhảy) | 1-Hop (1 Bước nhảy) | 2-Hop (2 Bước nhảy) |\n"
                    report_content += "| --- | --- | --- | --- |\n"
                    
                    hops_data = {}
                    for hop in [0, 1, 2]:
                        retrieved = run_multihop_search(driver, neo4j_db, q_vector, k=k_val, hops=hop)
                        ans = generate_rag_answer(gemini_key, gemini_model, q, retrieved)
                        
                        unique_docs = len(set(r["doc_id"] for r in retrieved))
                        total_chars = sum(len(r["text"]) for r in retrieved)
                        
                        hops_data[hop] = {
                            "docs": unique_docs,
                            "chars": total_chars,
                            "answer": ans
                        }
                        
                    report_content += f"| **Số tài liệu tham chiếu** | {hops_data[0]['docs']} | {hops_data[1]['docs']} | {hops_data[2]['docs']} |\n"
                    report_content += f"| **Tổng ký tự ngữ cảnh** | {hops_data[0]['chars']} | {hops_data[1]['chars']} | {hops_data[2]['chars']} |\n\n"
                    
                    for hop in [0, 1, 2]:
                        report_content += f"### Câu trả lời với {hop}-Hop:\n{hops_data[hop]['answer']}\n\n"
                        
                    report_content += "---\n\n"
                    progress_bar.progress((idx + 1) / len(test_questions))
                    
                # Ghi báo cáo ra đĩa
                output_report_path = Path("d:/Rag_thuchanh/RAG/qa_comparison.md")
                with open(output_report_path, "w", encoding="utf-8") as f:
                    f.write(report_content)
                    
                st.success(f"🎉 Xuất báo cáo thành công! Tệp tin đã được lưu tại: **[qa_comparison.md](file:///d:/Rag_thuchanh/RAG/qa_comparison.md)**")

    # -----------------------------------------------------------------------
    # TAB 4: GRAPH EXPLORER
    # -----------------------------------------------------------------------
    with tab4:
        st.markdown("### 🌲 Khám phá trực quan cơ sở dữ liệu đồ thị Neo4j")
        
        if not driver:
            st.info("Kết nối Neo4j đang offline.")
        else:
            with driver.session(database=neo4j_db) as session:
                st.markdown("#### 📊 Thống kê nhanh cơ sở dữ liệu `kb-hops`:")
                col_st1, col_st2, col_st3 = st.columns(3)
                
                doc_count = session.run("MATCH (d:Document) RETURN count(d) AS count").single()["count"]
                chunk_count = session.run("MATCH (c:Chunk) RETURN count(c) AS count").single()["count"]
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
                
                col_st1.metric("Số nút Document", doc_count)
                col_st2.metric("Số nút Chunk", chunk_count)
                col_st3.metric("Tổng số mối quan hệ", rel_count)
                
            st.markdown("---")
            st.markdown("#### 💻 Chạy truy vấn Cypher tùy biến:")
            cypher_input = st.text_area("Nhập mã Cypher của bạn:", value="MATCH (d1:Document)-[r]->(d2:Document) RETURN d1.id AS `Từ ID`, type(r) AS `Loại liên kết`, d2.id AS `Tới ID`, r.relationship AS `Mô tả` LIMIT 10")
            
            if st.button("Thực thi Cypher"):
                with driver.session(database=neo4j_db) as session:
                    try:
                        result = session.run(cypher_input)
                        records = [dict(rec) for rec in result]
                        if records:
                            df = pd.DataFrame(records)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.info("Truy vấn thành công nhưng không trả về dữ liệu.")
                    except Exception as e:
                        st.error(f"Lỗi thực thi Cypher: {e}")

    if driver:
        driver.close()

# Biến môi trường mặc định nếu chưa được định nghĩa
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Mquan"  # default value for helper
NEO4J_DB = "kb-hops"

if __name__ == "__main__":
    # Đọc mật khẩu thực tế nếu có cấu hình từ file load_neo4j
    load_neo4j_path = Path(__file__).resolve().parent / "load_neo4j.py"
    if load_neo4j_path.exists():
        with open(load_neo4j_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'NEO4J_PASSWORD\s*=\s*"([^"]+)"', content)
            if match:
                NEO4J_PASSWORD = match.group(1)
            match_db = re.search(r'NEO4J_DB\s*=\s*"([^"]+)"', content)
            if match_db:
                NEO4J_DB = match.group(1)
                
    main()
