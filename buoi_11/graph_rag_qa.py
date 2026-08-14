"""
Graph RAG QA & Evaluation - Buổi 11
Thực hiện tìm kiếm ngữ cảnh đa bước (multi-hop) từ đồ thị Neo4j và hỏi đáp bằng Gemini API.
So sánh chất lượng câu trả lời giữa các bước nhảy 0, 1, và 2.
"""

import os
import sys
import re
import json
import time
import csv
from pathlib import Path
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from neo4j import GraphDatabase
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Cấu hình encoding utf-8 để in ra console Windows không bị lỗi
sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình đường dẫn
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path("d:/Rag_thuchanh/RAG/kb+hops")
OUTPUT_COMPARISON_PATH = BASE_DIR / "qa_comparison.md"

# Cấu hình Neo4j
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Mquan@2004"
NEO4J_DB = "kb-hops"

# Cấu hình mô hình nhúng
MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

# ---------------------------------------------------------------------------
# 1. KHỞI TẠO MÔ HÌNH NHÚNG TRÊN CPU
# ---------------------------------------------------------------------------

print(f"⏳ Đang tải mô hình nhúng '{MODEL_NAME}' lên CPU...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
model.eval()

def embed_query(query_text):
    """Tạo vector nhúng cho câu hỏi truy vấn của người dùng (chuẩn hóa L2)."""
    encoded_input = tokenizer([query_text], padding=True, truncation=True, max_length=512, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
        
    # Mean pooling
    token_embeddings = model_output[0]
    input_mask_expanded = encoded_input['attention_mask'].unsqueeze(-1).expand(token_embeddings.size()).float()
    emb = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    # Chuẩn hóa L2
    emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb[0].cpu().numpy().tolist()

# ---------------------------------------------------------------------------
# 2. THIẾT LẬP VECTOR INDEX TRÊN NEO4J
# ---------------------------------------------------------------------------

def setup_vector_index(driver, db_name):
    """Tạo Vector Index cho thuộc tính embedding của nhãn Chunk nếu chưa tồn tại."""
    print("⚙️ Đang đảm bảo cấu hình Vector Index trong Neo4j...")
    create_index_query = """
    CREATE VECTOR INDEX chunk_embeddings_idx IF NOT EXISTS
    FOR (c:Chunk) ON (c.embedding)
    OPTIONS {
      indexConfig: {
        `vector.dimensions`: 384,
        `vector.similarity_function`: 'cosine'
      }
    }
    """
    with driver.session(database=db_name) as session:
        try:
            session.run(create_index_query)
            print("✅ Đã thiết lập thành công/đảm bảo tồn tại Vector Index 'chunk_embeddings_idx'.")
            # Đợi index được xây dựng xong
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Cảnh báo khi tạo Vector Index: {e}")

# ---------------------------------------------------------------------------
# 3. TRUY VẤN GRAPH RAG ĐA BƯỚC (MULTI-HOP RETRIEVAL)
# ---------------------------------------------------------------------------

def retrieve_multihop_context(driver, db_name, query_vector, k=8, n_hops=1, m_best=10):
    """
    Tìm kiếm ngữ cảnh đa bước (Multi-hop Graph RAG):
    - k: Số lượng chunk khớp trực tiếp bằng tìm kiếm vector.
    - n_hops: Số bước nhảy duyệt đồ thị để tìm các tài liệu liên kết liên quan.
    - m_best: Số lượng chunks phù hợp nhất được trả về làm ngữ cảnh cuối cùng sau khi Re-rank.
    """
    with driver.session(database=db_name) as session:
        # Bước 1: Tìm các chunks khớp trực tiếp bằng Vector Search
        direct_vector_query = """
        CALL db.index.vector.queryNodes('chunk_embeddings_idx', $k, $query_vector)
        YIELD node, score
        MATCH (node)-[:PART_OF]->(d:Document)
        RETURN DISTINCT d.id AS doc_id
        """
        try:
            result = session.run(direct_vector_query, {"k": k, "query_vector": query_vector})
            matched_doc_ids = [record["doc_id"] for record in result]
        except Exception as e:
            print(f"❌ Lỗi khi thực hiện tìm kiếm vector trong Neo4j: {e}")
            print("💡 Đảm bảo bạn đã nạp dữ liệu thành công trước khi chạy truy vấn RAG.")
            return [], []

        if not matched_doc_ids:
            return [], []

        # Bước 2: Duyệt đồ thị để thu thập các Document liên quan (Multi-hop)
        # Các quan hệ liên kết chéo giữa các văn bản luật
        rel_types = "SUA_DOI_BO_SUNG|CAN_CU|VAN_BAN_BO_SUNG|THAY_THE|HOP_NHAT"
        
        if n_hops > 0:
            # Tìm các tài liệu liên kết chéo trong vòng tối đa n_hops bước nhảy (duyệt vô hướng)
            hop_query = f"""
            MATCH (d:Document) WHERE d.id IN $matched_doc_ids
            MATCH (d)-[:{rel_types}*1..{n_hops}]-(related:Document)
            RETURN DISTINCT related.id AS doc_id, related.title AS title
            """
            hop_result = session.run(hop_query, {"matched_doc_ids": matched_doc_ids})
            related_doc_ids = [r["doc_id"] for r in hop_result]
            
            # Tập hợp tất cả tài liệu: khớp trực tiếp + liên quan đa bước
            all_doc_ids = list(set(matched_doc_ids + related_doc_ids))
        else:
            all_doc_ids = matched_doc_ids
            related_doc_ids = []

        # Bước 3: Thu thập toàn bộ các chunks thuộc về tất cả tài liệu này
        chunk_query = """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document)
        WHERE d.id IN $all_doc_ids
        RETURN c.chunk_id AS chunk_id, c.text AS text, c.type AS type, c.embedding AS embedding, d.id AS doc_id, d.title AS doc_title
        """
        chunk_result = session.run(chunk_query, {"all_doc_ids": all_doc_ids})
        
        candidate_chunks = []
        for r in chunk_result:
            if r["embedding"] is not None:
                candidate_chunks.append({
                    "chunk_id": r["chunk_id"],
                    "text": r["text"],
                    "type": r["type"],
                    "embedding": r["embedding"],
                    "doc_id": r["doc_id"],
                    "doc_title": r["doc_title"]
                })
                
        if not candidate_chunks:
            return [], all_doc_ids

        # Bước 4: Tính toán tương đồng Cosine trong Python để Re-rank và lọc ra m_best chunks
        q_vec = np.array(query_vector)
        scored_chunks = []
        
        for c in candidate_chunks:
            c_vec = np.array(c["embedding"])
            # Tích vô hướng (dot product) chính là cosine similarity vì cả hai vector đã được chuẩn hóa L2
            score = np.dot(q_vec, c_vec)
            scored_chunks.append((c, score))
            
        # Sắp xếp giảm dần theo điểm số tương đồng
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Chọn ra m_best chunks tốt nhất
        best_chunks = [item[0] for item in scored_chunks[:m_best]]
        return best_chunks, all_doc_ids

# ---------------------------------------------------------------------------
# 4. GỌI GEMINI API ĐỂ SINH CÂU TRẢ LỜI
# ---------------------------------------------------------------------------

def generate_answer(client, query, context_chunks):
    """Gọi Gemini API sử dụng dữ liệu ngữ cảnh làm nền tảng câu trả lời."""
    # Định dạng ngữ cảnh đưa vào Prompt
    context_str = ""
    for idx, c in enumerate(context_chunks):
        context_str += f"[{idx+1}] Văn bản: {c['doc_title']} (ID: {c['doc_id']})\n"
        context_str += f"Cấp độ: {c['type'].upper()} | Nội dung: {c['text']}\n"
        context_str += "-" * 50 + "\n"

    system_instruction = """
Bạn là một chuyên gia tư vấn luật pháp Việt Nam giàu kinh nghiệm, có hiểu biết sâu sắc về cấu trúc văn bản pháp luật và hệ thống cơ sở dữ liệu đồ thị luật. Nhiệm vụ của bạn là giải đáp các thắc mắc pháp lý của người dùng một cách chính xác, trung thực và khoa học, dựa trên Ngữ cảnh được cung cấp.

LƯỢC ĐỒ ĐỒ THỊ DỮ LIỆU & CẤU TRÚC VĂN BẢN PHÁP LUẬT VIỆT NAM:
Ngữ cảnh của bạn được trích xuất từ một Cơ sở dữ liệu Đồ thị Luật (Graph Database) có cấu trúc như sau:
1. Các thực thể chính:
   - Nút (:Document): Lưu trữ siêu dữ liệu của một văn bản luật (như số hiệu, ngày ban hành, cơ quan ban hành, tình trạng hiệu lực,...).
   - Nút (:Chunk): Lưu trữ nội dung sạch của các phân đoạn văn bản và vector nhúng tương ứng.
2. Quan hệ phân cấp & trình tự (Hierarchical & Sequential):
   - Mối quan hệ [:PARENT_OF] nối giữa các Chunk thể hiện cấu trúc phân cấp chuẩn của văn bản luật Việt Nam từ lớn đến nhỏ: Chương (Chapter) ➔ Mục (Section) ➔ Tiểu mục (Subsection) ➔ Điều (Article) ➔ Khoản (Clause) ➔ Điểm (Item) ➔ Đoạn văn/Bảng biểu (Content/Table).
   - Mỗi Chunk con đều được liên kết trực tiếp trở lại Document gốc bằng quan hệ [:PART_OF].
   - Các Chunk anh em liền kề trong cùng một cấp phân cấp được liên kết tuần tự qua quan hệ [:NEXT] để giữ vững luồng đọc tự nhiên của văn bản.
3. Quan hệ liên kết chéo giữa các Document (Multi-hop Relations):
   - [:SUA_DOI_BO_SUNG]: Văn bản này sửa đổi, bổ sung điều khoản cho văn bản kia. (Quy định trong văn bản sửa đổi sẽ thay thế hoặc cập nhật quy định tương ứng của văn bản cũ).
   - [:THAY_THE]: Văn bản này thay thế hoàn toàn cho văn bản cũ. (Quy định trong văn bản cũ không còn hiệu lực pháp lý).
   - [:HOP_NHAT]: Văn bản được tạo ra bằng cách hợp nhất các quy định từ nhiều văn bản gốc khác nhau.
   - [:CAN_CU]: Văn bản được ban hành căn cứ trên văn bản pháp lý cấp trên.

HƯỚNG DẪN THỰC THI & PHẢN HỒI:
1. Chỉ được trả lời dựa hoàn toàn vào thông tin có sẵn trong Ngữ cảnh được cung cấp. Không sử dụng kiến thức bên ngoài hoặc tự suy diễn thông tin không có trong văn bản.
2. Nếu Ngữ cảnh cung cấp không có đủ thông tin hoặc không liên quan để trả lời đầy đủ câu hỏi, bạn phải trả lời rõ ràng: "Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này." Tuyệt đối không tự suy đoán hay bịa ra câu trả lời.
3. Trong câu trả lời của bạn, phải trích dẫn rõ tên văn bản luật, số hiệu văn bản, và các điều khoản cụ thể (Điều, Khoản, Điểm) làm căn cứ pháp lý để người dùng có thể đối chiếu trực tiếp.
4. Khi nhận thấy ngữ cảnh có sự kết hợp giữa văn bản sửa đổi/bổ sung/thay thế (được duyệt qua nhiều bước nhảy đồ thị), bạn cần tổng hợp thông tin một cách chính xác để phản ánh quy định pháp lý mới nhất đang có hiệu lực.
5. Trình bày rõ ràng, mạch lạc bằng tiếng Việt.
"""

    prompt = f"""
Ngữ cảnh pháp lý (Context):
{context_str}

Câu hỏi của người dùng (Question):
{query}
"""
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0
            )
        )
        return response.text
    except Exception as e:
        return f"❌ Lỗi khi gọi Gemini API: {str(e)}"

# ---------------------------------------------------------------------------
# 5. PIPELINE CHẠY ĐÁNH GIÁ SO SÁNH (EVALUATION & COMPARISON)
# ---------------------------------------------------------------------------

def main():
    # Khởi tạo Gemini client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ Cảnh báo: Biến môi trường GEMINI_API_KEY chưa được thiết lập!")
        print("💡 Vui lòng thiết lập biến môi trường này hoặc nhập trực tiếp API Key của bạn.")
        api_key = input("Nhập Gemini API Key của bạn: ").strip()
        if not api_key:
            print("❌ Không có API Key. Chương trình kết thúc.")
            return

    client = genai.Client(api_key=api_key)

    # Kết nối Neo4j
    print(f"🔌 Kết nối tới Neo4j tại {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # Xác định database
    db_name = NEO4J_DB
    try:
        with driver.session(database=NEO4J_DB) as session:
            session.run("RETURN 1")
    except Exception:
        db_name = None
        
    print(f"📂 Sử dụng database: '{db_name if db_name else 'default'}'")
    setup_vector_index(driver, db_name)

    # 5 câu hỏi kiểm thử từ yêu cầu
    test_questions = [
        "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?",
        "Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?",
        "Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?",
        "Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?",
        "Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?"
    ]

    # Cấu hình lưu trữ kết quả so sánh dạng Markdown
    markdown_report = []
    markdown_report.append("# Báo cáo so sánh Hiệu quả Đồ thị RAG Đa bước (Multi-hop Graph RAG)")
    markdown_report.append(f"\n*Ngày thực hiện: {time.strftime('%Y-%m-%d %H:%M:%S')}*")
    markdown_report.append("\nBáo cáo này trình bày so sánh chi tiết chất lượng câu trả lời của LLM khi thay đổi số lượng bước nhảy ($N$) trong đồ thị RAG:\n- **0 bước nhảy (N=0)**: Chỉ sử dụng tìm kiếm vector trực tiếp.\n- **1 bước nhảy (N=1)**: Mở rộng ngữ cảnh sang các tài liệu liên kết trực tiếp.\n- **2 bước nhảy (N=2)**: Mở rộng ngữ cảnh sang các tài liệu liên kết 2 tầng.\n")

    for i, q in enumerate(test_questions):
        print(f"\n==========================================================================")
        print(f"🚀 ĐANG XỬ LÝ CÂU HỎI {i+1}: {q}")
        print(f"==========================================================================")
        
        # Nhúng câu hỏi
        print("🔍 Đang tạo vector nhúng câu hỏi...")
        q_emb = embed_query(q)
        
        # Chạy thử nghiệm với N = 0, 1, 2 bước nhảy
        answers = {}
        retrieved_docs_map = {}
        
        for hops in [0, 1, 2]:
            print(f"\n  [Hops = {hops}] Đang truy vấn ngữ cảnh...")
            context_chunks, doc_ids = retrieve_multihop_context(driver, db_name, q_emb, k=8, n_hops=hops, m_best=10)
            
            retrieved_docs_map[hops] = doc_ids
            print(f"  [Hops = {hops}] Đã lấy {len(context_chunks)} chunks từ các tài liệu: {doc_ids}")
            
            print(f"  [Hops = {hops}] Đang gọi Gemini API sinh câu trả lời...")
            answer = generate_answer(client, q, context_chunks)
            answers[hops] = answer
            print(f"  [Hops = {hops}] Hoàn thành câu trả lời.")
            
        # Ghi nhận vào báo cáo so sánh
        markdown_report.append(f"\n## Câu hỏi {i+1}: {q}")
        markdown_report.append(f"\n| Số bước nhảy | Tài liệu ngữ cảnh được duyệt | Tóm tắt câu trả lời |")
        markdown_report.append(f"| --- | --- | --- |")
        
        for hops in [0, 1, 2]:
            doc_str = ", ".join(retrieved_docs_map[hops]) if retrieved_docs_map[hops] else "Không tìm thấy"
            summary_ans = answers[hops].replace("\n", " ").replace("|", "\\|")[:120] + "..."
            markdown_report.append(f"| N={hops} | {doc_str} | {summary_ans} |")
            
        markdown_report.append("\n### So sánh chi tiết nội dung trả lời:")
        
        markdown_report.append(f"""
````carousel
#### Kết quả với N=0 (Vector RAG trực tiếp)
**Tài liệu ngữ cảnh:** {", ".join(retrieved_docs_map[0])}

{answers[0]}
<!-- slide -->
#### Kết quả với N=1 (Graph RAG 1 bước nhảy)
**Tài liệu ngữ cảnh:** {", ".join(retrieved_docs_map[1])}

{answers[1]}
<!-- slide -->
#### Kết quả với N=2 (Graph RAG 2 bước nhảy)
**Tài liệu ngữ cảnh:** {", ".join(retrieved_docs_map[2])}

{answers[2]}
````
""")
        markdown_report.append("\n" + "="*40 + "\n")

    # Lưu báo cáo so sánh ra đĩa
    with open(OUTPUT_COMPARISON_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_report))
        
    print(f"\n🎉 HOÀN THÀNH TOÀN BỘ QUÁ TRÌNH THỬ NGHIỆM ĐÁNH GIÁ!")
    print(f"📂 Đã lưu báo cáo so sánh chất lượng tại: {OUTPUT_COMPARISON_PATH}")
    
    driver.close()

if __name__ == "__main__":
    main()
