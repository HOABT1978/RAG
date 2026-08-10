"""
Load to Neo4j - Buổi 10
Vector nhúng bằng thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5.
Nạp Nodes (:Document), (:Chunk) và Relationships [:PART_OF], [:PARENT_OF], [:NEXT], và liên kết văn bản.
"""

import csv
import sys
import os
import re
import json
import time
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModel
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình đường dẫn
DATA_DIR = Path("d:/Rag_thuchanh/RAG/kb+hops")
CHUNKS_PARSED_PATH = DATA_DIR / "chunks_parsed.json"
CHUNKS_EMBEDDED_PATH = DATA_DIR / "chunks_embedded.json"
METADATA_CSV_PATH = DATA_DIR / "metadata.csv"
RELATIONSHIPS_CSV_PATH = DATA_DIR / "relationships.csv"

# Cấu hình Neo4j
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Mquan@2004"
NEO4J_DB = "kb-hops"

# Cấu hình model Embedding
MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

# ---------------------------------------------------------------------------
# 1. TẠO VECTOR EMBEDDINGS (BƯỚC 2)
# ---------------------------------------------------------------------------

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def generate_embeddings(chunks, batch_size=64):
    """Tạo embeddings bằng model thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5."""
    if CHUNKS_EMBEDDED_PATH.exists():
        print(f"🔄 Tìm thấy tệp cache embeddings: {CHUNKS_EMBEDDED_PATH}. Đang tải...")
        with open(CHUNKS_EMBEDDED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
            
    print(f"⏳ Đang tải mô hình embedding '{MODEL_NAME}' lên CPU...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    model.eval()
    
    texts = [c["text"] for c in chunks]
    total = len(texts)
    embeddings = []
    
    print(f"🚀 Bắt đầu nhúng {total} chunks...")
    t0 = time.time()
    
    for i in range(0, total, batch_size):
        batch_texts = texts[i:i+batch_size]
        encoded_input = tokenizer(batch_texts, padding=True, truncation=True, max_length=512, return_tensors='pt')
        
        with torch.no_grad():
            model_output = model(**encoded_input)
            
        batch_emb = mean_pooling(model_output, encoded_input['attention_mask'])
        batch_emb = torch.nn.functional.normalize(batch_emb, p=2, dim=1)
        embeddings.extend(batch_emb.cpu().numpy().tolist())
        
        if (i + batch_size) % 500 == 0 or (i + batch_size) >= total:
            elapsed = time.time() - t0
            current_count = min(i + batch_size, total)
            speed = current_count / elapsed
            print(f"  - Đã nhúng {current_count}/{total} chunks (Tốc độ: {speed:.1f} chunks/s)...")
            
    # Gán vector nhúng vào từng chunk
    for c, emb in zip(chunks, embeddings):
        c["embedding"] = emb
        
    # Ghi cache ra đĩa
    with open(CHUNKS_EMBEDDED_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Đã lưu cache chunks embedded tại: {CHUNKS_EMBEDDED_PATH}")
    return chunks

# ---------------------------------------------------------------------------
# 2. NẠP DỮ LIỆU VÀO NEO4J (BƯỚC 3 & BƯỚC 4)
# ---------------------------------------------------------------------------

def run_cypher_in_batches(session, query, data_list, batch_size=200):
    """Chạy câu lệnh Cypher theo từng batch để tối ưu hóa hiệu năng."""
    total = len(data_list)
    for i in range(0, total, batch_size):
        batch = data_list[i:i+batch_size]
        session.run(query, {"batch": batch})

def main():
    # 1. Chuẩn bị dữ liệu Chunks + Embeddings
    if not CHUNKS_PARSED_PATH.exists():
        print(f"❌ Không tìm thấy chunks_parsed.json. Vui lòng chạy chunker.py trước.")
        return
        
    with open(CHUNKS_PARSED_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    chunks_with_emb = generate_embeddings(chunks)
    
    # 2. Kết nối Neo4j
    print(f"🔌 Đang kết nối tới Neo4j tại {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # Kiểm tra xác thực và kết nối
    try:
        driver.verify_connectivity()
        print("✅ Kết nối Neo4j thành công!")
    except Exception as e:
        print(f"❌ Lỗi kết nối Neo4j: {str(e)}")
        print("💡 Vui lòng đảm bảo Neo4j Desktop đang chạy và Instance đã được kích hoạt.")
        return

    # Tạo database kb-hops nếu có quyền hệ thống
    try:
        with driver.session(database="system") as session:
            session.run(f"CREATE DATABASE `{NEO4J_DB}` IF NOT EXISTS")
            print(f"✅ Đã đảm bảo tồn tại cơ sở dữ liệu '{NEO4J_DB}' trên máy chủ.")
    except Exception as e:
        print(f"⚠️ Không thể tạo cơ sở dữ liệu qua system session (có thể dùng bản Community). Đang chạy trên DB mặc định. Lỗi: {e}")

    # Xác định db_name để dùng cho các session sau
    db_name = NEO4J_DB
    try:
        with driver.session(database=NEO4J_DB) as session:
            session.run("RETURN 1")
            print(f"📂 Đang sử dụng database: '{NEO4J_DB}'")
    except Exception:
        db_name = None
        print("📂 Đang sử dụng database mặc định của Neo4j.")

    # 3. Tạo Constraints & Indexes
    print("⚙️ Đang thiết lập ràng buộc duy nhất (Constraints & Indexes)...")
    with driver.session(database=db_name) as session:
        # Node Document
        session.run("CREATE CONSTRAINT FOR (d:Document) REQUIRE d.id IS UNIQUE")
        # Node Chunk
        session.run("CREATE CONSTRAINT FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE")
        session.run("CREATE INDEX FOR (c:Chunk) ON (c.type)")
        print("✅ Thiết lập Constraints/Indexes thành công.")

    # 4. Nạp dữ liệu Document từ metadata.csv
    documents = []
    if METADATA_CSV_PATH.exists():
        print(f"📄 Đang đọc siêu dữ liệu từ {METADATA_CSV_PATH.name}...")
        with open(METADATA_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                documents.append(row)
                
        # Nạp Document vào Neo4j
        print(f"💾 Đang nạp {len(documents)} nút Document vào Neo4j...")
        doc_query = """
        UNWIND $batch AS doc
        MERGE (d:Document {id: doc.id})
        SET d.title = doc.title,
            d.so_ky_hieu = doc.so_ky_hieu,
            d.ngay_ban_hanh = doc.ngay_ban_hanh,
            d.loai_van_ban = doc.loai_van_ban,
            d.ngay_co_hieu_luc = doc.ngay_co_hieu_luc,
            d.ngay_het_hieu_luc = doc.ngay_het_hieu_luc,
            d.nguon_thu_thap = doc.nguon_thu_thap,
            d.ngay_dang_cong_bao = doc.ngay_dang_cong_bao,
            d.nganh = doc.nganh,
            d.linh_vuc = doc.linh_vuc,
            d.co_quan_ban_hanh = doc.co_quan_ban_hanh,
            d.chuc_danh = doc.chuc_danh,
            d.nguoi_ky = doc.nguoi_ky,
            d.pham_vi = doc.pham_vi,
            d.thong_tin_ap_dung = doc.thong_tin_ap_dung,
            d.tinh_trang_hieu_luc = doc.tinh_trang_hieu_luc
        """
        with driver.session(database=db_name) as session:
            run_cypher_in_batches(session, doc_query, documents)
        print("✅ Đã nạp xong các Document nodes.")
    else:
        print(f"⚠️ Không tìm thấy tệp {METADATA_CSV_PATH.name}. Bỏ qua nạp Document.")

    # 5. Nạp dữ liệu Chunks vào Neo4j
    print(f"💾 Đang nạp {len(chunks_with_emb)} nút Chunk vào Neo4j...")
    chunk_query = """
    UNWIND $batch AS chunk
    MERGE (c:Chunk {chunk_id: chunk.chunk_id})
    SET c.text = chunk.text,
        c.type = chunk.type,
        c.embedding = chunk.embedding
    """
    with driver.session(database=db_name) as session:
        run_cypher_in_batches(session, chunk_query, chunks_with_emb)
    print("✅ Đã nạp xong các Chunk nodes.")

    # 6. Thiết lập quan hệ PART_OF (Chunk -> Document)
    print("🔗 Đang liên kết các Chunks về Document gốc ([:PART_OF])...")
    part_of_query = """
    UNWIND $batch AS chunk
    MATCH (c:Chunk {chunk_id: chunk.chunk_id})
    MATCH (d:Document {id: chunk.doc_id})
    MERGE (c)-[:PART_OF]->(d)
    """
    with driver.session(database=db_name) as session:
        run_cypher_in_batches(session, part_of_query, chunks_with_emb)
    print("✅ Thiết lập quan hệ [:PART_OF] thành công.")

    # 7. Thiết lập quan hệ PARENT_OF (Parent Chunk -> Child Chunk)
    print("🔗 Đang liên kết phân cấp cha-con ([:PARENT_OF])...")
    # Lọc những chunk có parent_type không phải document
    parent_of_data = [c for c in chunks_with_emb if c['parent_type'] != 'document']
    parent_of_query = """
    UNWIND $batch AS chunk
    MATCH (c:Chunk {chunk_id: chunk.chunk_id})
    MATCH (p:Chunk {chunk_id: chunk.parent_id})
    MERGE (p)-[:PARENT_OF]->(c)
    """
    with driver.session(database=db_name) as session:
        run_cypher_in_batches(session, parent_of_query, parent_of_data)
    print("✅ Thiết lập quan hệ [:PARENT_OF] thành công.")

    # 8. Thiết lập quan hệ NEXT (Sibling -> Sibling)
    print("🔗 Đang liên kết tuần tự các phân đoạn anh em ([:NEXT])...")
    next_data = [c for c in chunks_with_emb if 'next_sibling_id' in c]
    next_query = """
    UNWIND $batch AS chunk
    MATCH (c1:Chunk {chunk_id: chunk.chunk_id})
    MATCH (c2:Chunk {chunk_id: chunk.next_sibling_id})
    MERGE (c1)-[:NEXT]->(c2)
    """
    with driver.session(database=db_name) as session:
        run_cypher_in_batches(session, next_query, next_data)
    print("✅ Thiết lập quan hệ [:NEXT] thành công.")

    # 9. Thiết lập liên kết chéo giữa các Document từ relationships.csv
    if RELATIONSHIPS_CSV_PATH.exists():
        print(f"📄 Đang nạp quan hệ chéo giữa các tài liệu từ {RELATIONSHIPS_CSV_PATH.name}...")
        doc_rels = []
        with open(RELATIONSHIPS_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                doc_rels.append(row)
                
        # Nạp động theo loại quan hệ
        with driver.session(database=db_name) as session:
            count_rel = 0
            for rel in doc_rels:
                doc_id = rel['doc_id']
                other_doc_id = rel['other_doc_id']
                rel_desc = rel['relationship']
                rel_type = rel['relationship_type'].strip()
                
                # Tránh các ký tự đặc biệt trong tên quan hệ Cypher
                rel_type = re.sub(r"[^a-zA-Z0-9_]", "_", rel_type)
                
                query = f"""
                MATCH (d1:Document {{id: $doc_id}})
                MATCH (d2:Document {{id: $other_doc_id}})
                MERGE (d1)-[r:{rel_type}]->(d2)
                SET r.relationship = $rel_desc
                """
                session.run(query, {"doc_id": doc_id, "other_doc_id": other_doc_id, "rel_desc": rel_desc})
                count_rel += 1
        print(f"✅ Đã nạp thành công {count_rel} quan hệ liên kết giữa các tài liệu.")
    else:
        print(f"⚠️ Không tìm thấy tệp {RELATIONSHIPS_CSV_PATH.name}. Bỏ qua nạp quan hệ tài liệu.")

    driver.close()
    print("\n🎉 HOÀN THÀNH TOÀN BỘ QUÁ TRÌNH NẠP DỮ LIỆU LÊN NEO4J!")

if __name__ == "__main__":
    main()
