import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("==================================================")
    print("🔍 BƯỚC 9: KIỂM TRA KẾT QUẢ KNOWLEDGE GRAPH")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parents[1]
    env_path = root_dir / "buoi_12" / ".env"
    
    docs_path = root_dir / "ner_kb" / "cleaned_documents.csv"
    entities_path = root_dir / "ner_kb" / "entities.csv"
    rels_path = root_dir / "ner_kb" / "relationships.csv"
    
    # Check files
    for p in [docs_path, entities_path, rels_path]:
        if not p.exists():
            print(f"❌ Không tìm thấy file: {p}")
            sys.exit(1)
            
    # Read CSV counts
    df_docs = pd.read_csv(docs_path)
    df_entities = pd.read_csv(entities_path)
    df_rels = pd.read_csv(rels_path)
    
    csv_doc_count = len(df_docs)
    csv_entities = df_entities.drop_duplicates(subset=["entity_id", "entity_type"])
    csv_ent_counts = csv_entities['entity_type'].value_counts()
    csv_rel_counts = df_rels['relationship_type'].value_counts()
    
    load_dotenv(env_path)
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    db_name = os.getenv("NEO4J_DATABASE") or "neo4j"
    
    driver = None
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        
        db_nodes = {}
        db_rels = {}
        
        # Query database counts
        with driver.session(database=db_name) as session:
            # 1. Node count by label
            for label in ["Document", "CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"]:
                res = session.run(f"MATCH (n:{label}) RETURN count(n) AS count")
                db_nodes[label] = res.single()["count"]
                
            # 2. Relationship count by type
            for rtype in ["THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI", "BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"]:
                res = session.run(f"MATCH ()-[r:{rtype}]->() RETURN count(r) AS count")
                db_rels[rtype] = res.single()["count"]
                
            # 3. Sample Document -> NguoiKy
            print("\n📈 [Mẫu] Document -> NguoiKy (KY_BOI):")
            res = session.run("""
            MATCH (d:Document)-[r:KY_BOI]->(p:NguoiKy)
            RETURN d.so_ky_hieu AS so_ky_hieu, p.name AS name, r.evidence AS evidence
            LIMIT 3
            """)
            for record in res:
                print(f"  - {record['so_ky_hieu']} ký bởi {record['name']}")
                print(f"    Bằng chứng: {record['evidence'][:100]}...")
                
            # 4. Sample Document -> DoiTuongApDung
            print("\n📈 [Mẫu] Document -> DoiTuongApDung (AP_DUNG_CHO):")
            res = session.run("""
            MATCH (d:Document)-[r:AP_DUNG_CHO]->(o:DoiTuongApDung)
            RETURN d.so_ky_hieu AS so_ky_hieu, o.name AS name, r.evidence AS evidence
            LIMIT 3
            """)
            for record in res:
                print(f"  - {record['so_ky_hieu']} áp dụng cho {record['name']}")
                print(f"    Bằng chứng: {record['evidence'][:100]}...")
                
            # 5. Document -> Document relations
            print("\n📈 [Mẫu] Document -> Document relations (THAM_CHIEU, SUA_DOI_BO_SUNG, THAY_THE_BOI):")
            res = session.run("""
            MATCH (d1:Document)-[r:THAM_CHIEU|SUA_DOI_BO_SUNG|THAY_THE_BOI]->(d2:Document)
            RETURN d1.so_ky_hieu AS doc1, type(r) AS rel_type, d2.so_ky_hieu AS doc2, r.evidence AS evidence
            LIMIT 3
            """)
            for record in res:
                print(f"  - {record['doc1']} -[:{record['rel_type']}]-> {record['doc2']}")
                print(f"    Bằng chứng: {record['evidence'][:100]}...")
                
        # Comparison logic
        print("\n" + "="*50)
        print("📊 ĐỐI CHIẾU SỐ LIỆU (CSV vs Neo4j Database):")
        print("="*50)
        
        mismatches = 0
        
        # Check Document nodes
        neo_doc_count = db_nodes.get("Document", 0)
        doc_status = "MATCH" if csv_doc_count == neo_doc_count else "MISMATCH"
        print(f"🔹 Document nodes: CSV = {csv_doc_count} | Neo4j = {neo_doc_count} -> [{doc_status}]")
        if doc_status == "MISMATCH":
            mismatches += 1
            
        # Check Entity nodes
        for label in ["CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"]:
            csv_count = csv_ent_counts.get(label, 0)
            neo_count = db_nodes.get(label, 0)
            status = "MATCH" if csv_count == neo_count else "MISMATCH"
            print(f"🔹 Entity (:{label}): CSV = {csv_count} | Neo4j = {neo_count} -> [{status}]")
            if status == "MISMATCH":
                mismatches += 1
                
        # Check Relationships
        for rtype in ["THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI", "BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"]:
            csv_count = csv_rel_counts.get(rtype, 0)
            neo_count = db_rels.get(rtype, 0)
            status = "MATCH" if csv_count == neo_count else "MISMATCH"
            print(f"🔹 Relationship [:{rtype}]: CSV = {csv_count} | Neo4j = {neo_count} -> [{status}]")
            if status == "MISMATCH":
                mismatches += 1
                
        print("==================================================")
        if mismatches == 0:
            print("🎉 KẾT QUẢ BƯỚC 9: [PASS]")
            sys.exit(0)
        else:
            print(f"❌ KẾT QUẢ BƯỚC 9: [FAIL] - Phát hiện {mismatches} điểm chênh lệch số liệu.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Gặp lỗi trong quá trình kiểm tra: {str(e)}")
        print("KẾT QUẢ BƯỚC 9: [FAIL]")
        sys.exit(1)
    finally:
        if driver:
            driver.close()

if __name__ == "__main__":
    main()
