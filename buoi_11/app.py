"""
Web App Backend for Graph RAG QA - Buổi 11
Cung cấp API phục vụ giao diện HTML hỏi đáp tương tác.
"""

import os
import sys
import re
import json
import time
from pathlib import Path
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from neo4j import GraphDatabase
from google import genai
from google.genai import types
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Cấu hình encoding utf-8
sys.stdout.reconfigure(encoding='utf-8')

# Load variables from .env file
load_dotenv()

# Cấu hình đường dẫn
BASE_DIR = Path(__file__).resolve().parent

# Khởi tạo Flask
app = Flask(__name__)
CORS(app)

# Cấu hình Neo4j
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Mquan@2004"
NEO4J_DB = "kb-hops"

# Cấu hình mô hình nhúng
MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

# Khởi tạo mô hình nhúng trên CPU
print(f"⏳ Đang tải mô hình nhúng '{MODEL_NAME}' lên CPU...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
model.eval()

# Khởi tạo Neo4j driver
print(f"🔌 Kết nối tới Neo4j tại {NEO4J_URI}...")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Xác định database tồn tại thực tế
db_name = NEO4J_DB
try:
    with driver.session(database=NEO4J_DB) as session:
        session.run("RETURN 1")
except Exception:
    db_name = None

# Đảm bảo có Vector Index
with driver.session(database=db_name) as session:
    try:
        session.run("""
        CREATE VECTOR INDEX chunk_embeddings_idx IF NOT EXISTS
        FOR (c:Chunk) ON (c.embedding)
        OPTIONS {
          indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
          }
        }
        """)
        print("✅ Đảm bảo tồn tại Vector Index 'chunk_embeddings_idx'.")
    except Exception as e:
        print(f"⚠️ Cảnh báo khởi tạo Vector Index: {e}")

# Khởi tạo Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def embed_query(query_text):
    """Mã hóa câu hỏi thành vector nhúng L2-normalized."""
    encoded_input = tokenizer([query_text], padding=True, truncation=True, max_length=512, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
    token_embeddings = model_output[0]
    input_mask_expanded = encoded_input['attention_mask'].unsqueeze(-1).expand(token_embeddings.size()).float()
    emb = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb[0].cpu().numpy().tolist()

def retrieve_multihop_context(query_vector, k=8, n_hops=1, m_best=10):
    """Duyệt đồ thị đa bước để tìm các chunk liên quan."""
    with driver.session(database=db_name) as session:
        # 1. Tìm các chunk khớp trực tiếp qua Vector Search
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
            print(f"❌ Lỗi truy vấn vector Neo4j: {e}")
            return [], []

        if not matched_doc_ids:
            return [], []

        # 2. Duyệt đồ thị lấy các tài liệu liên kết chéo
        rel_types = "SUA_DOI_BO_SUNG|CAN_CU|VAN_BAN_BO_SUNG|THAY_THE|HOP_NHAT"
        if n_hops > 0:
            hop_query = f"""
            MATCH (d:Document) WHERE d.id IN $matched_doc_ids
            MATCH (d)-[:{rel_types}*1..{n_hops}]-(related:Document)
            RETURN DISTINCT related.id AS doc_id, related.title AS title
            """
            hop_result = session.run(hop_query, {"matched_doc_ids": matched_doc_ids})
            related_docs = [{"id": r["doc_id"], "title": r["title"]} for r in hop_result]
            related_doc_ids = [r["doc_id"] for r in hop_result]
            all_doc_ids = list(set(matched_doc_ids + related_doc_ids))
        else:
            all_doc_ids = matched_doc_ids
            related_docs = []

        # 3. Lấy tất cả các chunks thuộc về các tài liệu này
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

        # 4. Tính toán tương đồng Cosine trong Python và chọn ra m_best chunks
        q_vec = np.array(query_vector)
        scored_chunks = []
        for c in candidate_chunks:
            c_vec = np.array(c["embedding"])
            score = np.dot(q_vec, c_vec)
            scored_chunks.append((c, score))
            
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        best_chunks = [item[0] for item in scored_chunks[:m_best]]
        
        # Tạo danh sách các tài liệu đã duyệt để trả về UI
        docs_info = []
        for doc_id in all_doc_ids:
            # Tìm tiêu đề tương ứng trong candidate_chunks
            title = "Tài liệu luật"
            for c in candidate_chunks:
                if c["doc_id"] == doc_id:
                    title = c["doc_title"]
                    break
            docs_info.append({"id": doc_id, "title": title, "is_direct": doc_id in matched_doc_ids})
            
        return best_chunks, docs_info

def generate_answer(query, context_chunks):
    """Gọi Gemini API để tạo câu trả lời dựa trên ngữ cảnh."""
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
# ROUTES FLASK
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    """Phục vụ file index.html."""
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/api/query', methods=['POST'])
def query_api():
    """Endpoint nhận câu hỏi RAG."""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Vui lòng cung cấp tham số 'query'"}), 400
        
    query_text = data['query']
    n_hops = int(data.get('n_hops', 1))
    k = int(data.get('k', 8))
    m_best = int(data.get('m_best', 10))
    
    try:
        t0 = time.time()
        # 1. Nhúng câu hỏi
        q_emb = embed_query(query_text)
        
        # 2. Truy vấn RAG đa bước từ Neo4j
        context_chunks, docs_info = retrieve_multihop_context(q_emb, k=k, n_hops=n_hops, m_best=m_best)
        
        # 3. Gọi LLM sinh câu trả lời
        answer = generate_answer(query_text, context_chunks)
        
        elapsed = time.time() - t0
        
        # Loại bỏ trường embedding để JSON trả về gọn nhẹ
        clean_chunks = []
        for c in context_chunks:
            clean_c = c.copy()
            if 'embedding' in clean_c:
                del clean_c['embedding']
            clean_chunks.append(clean_c)
            
        return jsonify({
            "query": query_text,
            "n_hops": n_hops,
            "answer": answer,
            "retrieved_docs": docs_info,
            "context_chunks": clean_chunks,
            "time_taken_seconds": round(elapsed, 2)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Lỗi máy chủ: {str(e)}"}), 500

if __name__ == '__main__':
    # Chạy cục bộ trên cổng 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
