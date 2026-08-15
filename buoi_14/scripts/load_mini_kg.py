import os
import sys
import io
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Paths
script_dir = Path(__file__).resolve().parent
buoi_14_dir = script_dir.parent

def clean_value(val):
    if pd.isna(val):
        return None
    return str(val).strip()

def main():
    # Load env
    load_dotenv(dotenv_path=buoi_14_dir / ".env")
    uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "BUOI_13")
    password = os.getenv("NEO4J_PASSWORD", "12345678")
    db_name = os.getenv("NEO4J_DATABASE", "neo4j")
    
    print(f"Connecting to Neo4j at {uri}...")
    driver = None
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception as e:
        print(f"⚠️ Initial connection failed: {e}")
        # Try fallback from neo4j:// to bolt://
        if uri.startswith("neo4j://"):
            fallback_uri = uri.replace("neo4j://", "bolt://")
            print(f"Retrying connection using direct fallback URI: {fallback_uri}...")
            try:
                driver = GraphDatabase.driver(fallback_uri, auth=(user, password))
                driver.verify_connectivity()
                print("Connected successfully using direct Bolt protocol!")
            except Exception as fe:
                print(f"❌ Fallback connection failed: {fe}")
                print("Please verify that Neo4j is running and your credentials are correct.")
                sys.exit(0)
        else:
            print("Please verify that Neo4j is running and your credentials are correct.")
            sys.exit(0)
        
    # Read files
    metadata_path = buoi_14_dir.parent / "kb+hops" / "metadata.csv"
    chunks_path = buoi_14_dir / "data" / "processed" / "chunks_normalized.csv"
    relationships_path = buoi_14_dir.parent / "kb+hops" / "relationships.csv"
    
    df_meta = pd.read_csv(metadata_path)
    df_chunks = pd.read_csv(chunks_path)
    df_rels = pd.read_csv(relationships_path)
    
    with driver.session(database=db_name) as session:
        # 1. Clean up old lab session data to remain idempotent
        print("Cleaning up old 'buoi_14' session nodes and relationships...")
        session.run("MATCH (n {lab_session: 'buoi_14'}) DETACH DELETE n")
        
        # 2. Apply uniqueness constraints
        print("Creating uniqueness constraints...")
        session.run("CREATE CONSTRAINT unique_vanban_id IF NOT EXISTS FOR (v:VanBan) REQUIRE v.id IS UNIQUE")
        session.run("CREATE CONSTRAINT unique_dieukhoan_id IF NOT EXISTS FOR (d:DieuKhoan) REQUIRE d.id IS UNIQUE")
        
        # 3. Import VanBan nodes
        print("Importing VanBan nodes...")
        vanban_query = """
        MERGE (v:VanBan {id: $id})
        SET v.title = $title,
            v.so_ky_hieu = $so_ky_hieu,
            v.ngay_ban_hanh = $ngay_ban_hanh,
            v.loai_van_ban = $loai_van_ban,
            v.ngay_co_hieu_luc = $ngay_co_hieu_luc,
            v.ngay_het_hieu_luc = $ngay_het_hieu_luc,
            v.nguon_thu_thap = $nguon_thu_thap,
            v.nganh = $nganh,
            v.linh_vuc = $linh_vuc,
            v.co_quan_ban_hanh = $co_quan_ban_hanh,
            v.chuc_danh = $chuc_danh,
            v.nguoi_ky = $nguoi_ky,
            v.pham_vi = $pham_vi,
            v.tinh_trang_hieu_luc = $tinh_trang_hieu_luc,
            v.lab_session = "buoi_14"
        """
        for _, row in df_meta.iterrows():
            params = {
                'id': clean_value(row['id']),
                'title': clean_value(row.get('title')),
                'so_ky_hieu': clean_value(row.get('so_ky_hieu')),
                'ngay_ban_hanh': clean_value(row.get('ngay_ban_hanh')),
                'loai_van_ban': clean_value(row.get('loai_van_ban')),
                'ngay_co_hieu_luc': clean_value(row.get('ngay_co_hieu_luc')),
                'ngay_het_hieu_luc': clean_value(row.get('ngay_het_hieu_luc')),
                'nguon_thu_thap': clean_value(row.get('nguon_thu_thap')),
                'nganh': clean_value(row.get('nganh')),
                'linh_vuc': clean_value(row.get('linh_vuc')),
                'co_quan_ban_hanh': clean_value(row.get('co_quan_ban_hanh')),
                'chuc_danh': clean_value(row.get('chuc_danh')),
                'nguoi_ky': clean_value(row.get('nguoi_ky')),
                'pham_vi': clean_value(row.get('pham_vi')),
                'tinh_trang_hieu_luc': clean_value(row.get('tinh_trang_hieu_luc'))
            }
            session.run(vanban_query, **params)
            
        # 4. Import DieuKhoan nodes & CONTAINS relations
        print("Importing DieuKhoan nodes and CONTAINS relationships...")
        dieukhoan_query = """
        MERGE (d:DieuKhoan {id: $id})
        SET d.document_id = $document_id,
            d.text = $text,
            d.chapter = $chapter,
            d.section = $section,
            d.article = $article,
            d.clause = $clause,
            d.lab_session = "buoi_14"
        """
        contains_query = """
        MATCH (v:VanBan {id: $document_id})
        MATCH (d:DieuKhoan {id: $id})
        MERGE (v)-[r:CONTAINS]->(d)
        SET r.lab_session = "buoi_14"
        """
        for _, row in df_chunks.iterrows():
            cid = clean_value(row['chunk_id'])
            doc_id = clean_value(row['document_id'])
            
            d_params = {
                'id': cid,
                'document_id': doc_id,
                'text': clean_value(row.get('text')),
                'chapter': clean_value(row.get('chapter')),
                'section': clean_value(row.get('section')),
                'article': clean_value(row.get('article')),
                'clause': clean_value(row.get('clause'))
            }
            session.run(dieukhoan_query, **d_params)
            session.run(contains_query, id=cid, document_id=doc_id)
            
        # 5. Create structural NEXT relationships between successive chunks of the same document
        print("Creating NEXT relationships...")
        next_query = """
        MATCH (d1:DieuKhoan {id: $id1})
        MATCH (d2:DieuKhoan {id: $id2})
        MERGE (d1)-[r:NEXT]->(d2)
        SET r.lab_session = "buoi_14"
        """
        # Group by document_id and sort chunks by chunk_id
        for doc_id, group in df_chunks.groupby('document_id'):
            sorted_chunks = group.sort_values('chunk_id')['chunk_id'].tolist()
            for i in range(len(sorted_chunks) - 1):
                session.run(next_query, id1=sorted_chunks[i], id2=sorted_chunks[i+1])
                
        # 6. Import document relationships from relationships.csv
        print("Importing document relationships...")
        allowed_types = {"SUA_DOI_BO_SUNG", "CAN_CU", "VAN_BAN_BO_SUNG", "THAY_THE", "HOP_NHAT"}
        for _, row in df_rels.iterrows():
            doc_id = clean_value(row['doc_id'])
            other_doc_id = clean_value(row['other_doc_id'])
            rel_type = str(row['relationship_type']).strip().upper()
            
            if rel_type in allowed_types:
                rel_query = f"""
                MATCH (v1:VanBan {{id: $doc_id}})
                MATCH (v2:VanBan {{id: $other_doc_id}})
                MERGE (v1)-[r:{rel_type}]->(v2)
                SET r.lab_session = "buoi_14"
                """
                session.run(rel_query, doc_id=doc_id, other_doc_id=other_doc_id)
            else:
                print(f"Skipped relationship of unmapped type: {rel_type}")
                
        # 7. Auditing & Counting
        print("Auditing imported Graph...")
        num_vanban = session.run("MATCH (v:VanBan {lab_session: 'buoi_14'}) RETURN count(v) AS c").single()['c']
        num_dieukhoan = session.run("MATCH (d:DieuKhoan {lab_session: 'buoi_14'}) RETURN count(d) AS c").single()['c']
        
        rel_counts_cursor = session.run("""
        MATCH (n {lab_session: 'buoi_14'})-[r]->(m {lab_session: 'buoi_14'})
        RETURN type(r) AS t, count(r) AS c
        """)
        rel_counts = {record['t']: record['c'] for record in rel_counts_cursor}
        
        # Orphan checks
        # A: Chunks without CONTAINS incoming relationship
        orphan_chunks_cursor = session.run("""
        MATCH (d:DieuKhoan {lab_session: 'buoi_14'})
        WHERE NOT (:VanBan)-[:CONTAINS]->(d)
        RETURN count(d) AS c
        """)
        orphan_chunks = orphan_chunks_cursor.single()['c']
        
        # B: Documents without CONTAINS outgoing relationship
        empty_docs_cursor = session.run("""
        MATCH (v:VanBan {lab_session: 'buoi_14'})
        WHERE NOT (v)-[:CONTAINS]->(:DieuKhoan)
        RETURN count(v) AS c
        """)
        empty_docs = empty_docs_cursor.single()['c']
        
        # 8. Generate outputs/kg_build_report.md
        report = []
        report.append("# BÁO CÁO THIẾT LẬP KNOWLEDGE GRAPH MINI (BUỔI 14)")
        report.append("")
        report.append("Đồ thị tri thức mini biểu diễn mối liên kết cấu trúc giữa các Văn bản pháp lý và các Điều khoản phân đoạn đã được nạp thành công vào cơ sở dữ liệu Neo4j.")
        report.append("")
        report.append("## 1. Thống kê số lượng Nodes")
        report.append(f"- **Số node `:VanBan`**: `{num_vanban}`")
        report.append(f"- **Số node `:DieuKhoan`**: `{num_dieukhoan}`")
        report.append("")
        
        report.append("## 2. Thống kê số lượng Cạnh (Relationships)")
        report.append("| Tên quan hệ (Type) | Số lượng bản ghi | Mô tả ý nghĩa |")
        report.append("| :--- | :--- | :--- |")
        for r_type, count in sorted(rel_counts.items()):
            desc = ""
            if r_type == 'CONTAINS':
                desc = "Văn bản chứa Điều khoản"
            elif r_type == 'NEXT':
                desc = "Liên kết chuỗi điều khoản kế tiếp"
            elif r_type in allowed_types:
                desc = f"Quan hệ nghiệp vụ văn bản ({r_type.lower().replace('_', ' ')})"
            report.append(f"| `{r_type}` | `{count}` | {desc} |")
        report.append("")
        
        report.append("## 3. Kiểm thử tính toàn vẹn (Integrity Audit)")
        report.append(f"- **Số điều khoản mồ côi (không thuộc văn bản nào)**: `{orphan_chunks}`")
        report.append(f"- **Số văn bản rỗng (không chứa điều khoản nào)**: `{empty_docs}`")
        report.append("")
        if orphan_chunks == 0 and empty_docs == 0:
            report.append("✅ **Kết luận**: Đồ thị tri thức hoàn toàn nhất quán. Không phát hiện điều khoản mồ côi hoặc văn bản rỗng.")
        else:
            report.append("⚠️ **Cảnh báo**: Phát hiện bất thường về cấu trúc trong liên kết điều khoản.")
        report.append("")
        
        # Save report
        outputs_dir = buoi_14_dir / "outputs"
        report_path = outputs_dir / "kg_build_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report) + '\n')
        print(f"Knowledge Graph report written to {report_path}")
        
    driver.close()

if __name__ == '__main__':
    main()
