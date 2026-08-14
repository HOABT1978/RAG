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
    print("💾 BƯỚC 8: IMPORT KNOWLEDGE GRAPH VÀO NEO4J")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parents[1]
    env_path = root_dir / "buoi_12" / ".env"
    
    docs_path = root_dir / "ner_kb" / "cleaned_documents.csv"
    metadata_path = root_dir / "ner_kb" / "enriched_metadata.csv"
    entities_path = root_dir / "ner_kb" / "entities.csv"
    rels_path = root_dir / "ner_kb" / "relationships.csv"
    
    # Check inputs
    for p in [docs_path, metadata_path, entities_path, rels_path]:
        if not p.exists():
            print(f"❌ Không tìm thấy file đầu vào: {p}")
            sys.exit(1)
            
    # Load configuration
    load_dotenv(env_path)
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    db_name = os.getenv("NEO4J_DATABASE") or "neo4j"
    
    if not uri or not user or not password:
        print("❌ Thiếu thông tin cấu hình Neo4j trong file .env.")
        sys.exit(1)
        
    print(f"📡 Đang kết nối tới Neo4j tại: {uri} (Database: {db_name})")
    
    driver = None
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        
        # 1. Đọc dữ liệu từ file csv
        print("📖 Đang đọc dữ liệu từ CSV...")
        df_docs_raw = pd.read_csv(docs_path)[['id', 'content_clean']]
        df_meta_raw = pd.read_csv(metadata_path)
        df_docs = pd.merge(df_meta_raw, df_docs_raw, on='id', how='inner')
        
        df_entities = pd.read_csv(entities_path)
        df_rels = pd.read_csv(rels_path)
        
        valid_doc_ids = set(df_docs['id'].astype(str))
        valid_entity_ids = set(df_entities['entity_id'].astype(str))
        
        # 3. Tạo uniqueness constraint hợp lý trước khi import
        print("⚙️ Thiết lập uniqueness constraints (Ràng buộc duy nhất)...")
        with driver.session(database=db_name) as session:
            # Document constraint
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
            
            # Entity constraints
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:CoQuan) REQUIRE e.entity_id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:NguoiKy) REQUIRE e.entity_id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:DoiTuongApDung) REQUIRE e.entity_id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:LinhVuc) REQUIRE e.entity_id IS UNIQUE")
            print("✅ Đã thiết lập xong các Constraints.")
            
        # 4. Import Document nodes
        print(f"💾 Đang nạp {len(df_docs)} Document nodes...")
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
            d.tinh_trang_hieu_luc = doc.tinh_trang_hieu_luc,
            d.content_clean = doc.content_clean
        """
        # Convert DataFrame to list of dicts and handle NaN values
        df_docs_clean = df_docs.where(pd.notnull(df_docs), None)
        docs_batch = df_docs_clean.to_dict(orient='records')
        
        # Keep id as string to match lookup
        for d in docs_batch:
            d['id'] = str(d['id'])
            
        with driver.session(database=db_name) as session:
            session.run(doc_query, {"batch": docs_batch})
        print("✅ Nạp Document nodes thành công.")
        
        # 5. Import Entity nodes
        # Extract unique entities from entities.csv
        unique_entities = df_entities.drop_duplicates(subset=["entity_id", "entity_type", "canonical_name"])
        print(f"💾 Đang nạp {len(unique_entities)} Entity nodes...")
        
        # We process entities in batch groups depending on their type
        with driver.session(database=db_name) as session:
            for etype in ["CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"]:
                type_batch = unique_entities[unique_entities["entity_type"] == etype].to_dict(orient="records")
                if not type_batch:
                    continue
                
                # Dynamic cypher query template per entity type
                query = f"""
                UNWIND $batch AS ent
                MERGE (e:{etype} {{entity_id: ent.entity_id}})
                SET e.name = ent.canonical_name
                """
                session.run(query, {"batch": type_batch})
        print("✅ Nạp Entity nodes thành công.")
        
        # 6. Import Relationships
        print(f"💾 Đang nạp {len(df_rels)} Relationships...")
        
        import_errors = []
        doc_doc_count = 0
        doc_ent_count = 0
        
        allowed_doc_doc_types = {"THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI"}
        allowed_doc_ent_types = {"BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"}
        
        # Map entity type to node label
        entity_label_map = {
            "BAN_HANH_BOI": "CoQuan",
            "KY_BOI": "NguoiKy",
            "AP_DUNG_CHO": "DoiTuongApDung",
            "THUOC_LINH_VUC": "LinhVuc"
        }
        
        # Import one by one or batch.
        # Since we need to check existence of source and target to count errors, we check locally first.
        valid_rels = []
        for idx, row in df_rels.iterrows():
            source = str(row['source']).strip()
            target = str(row['target']).strip()
            rel_type = str(row['relationship_type']).strip()
            evidence = str(row['evidence']).strip() if pd.notna(row['evidence']) else ""
            confidence = float(row['confidence'])
            method = str(row['method']).strip()
            
            # Rule 7: Kiểm tra source và target trước khi nạp
            if source not in valid_doc_ids:
                import_errors.append(f"Không tìm thấy Source Document ID: '{source}' cho quan hệ {rel_type} -> '{target}'")
                continue
                
            if rel_type in allowed_doc_doc_types:
                if target not in valid_doc_ids:
                    import_errors.append(f"Không tìm thấy Target Document ID: '{target}' cho quan hệ '{source}' -> {rel_type}")
                    continue
                valid_rels.append((source, target, rel_type, evidence, confidence, method, "doc_doc"))
                doc_doc_count += 1
            elif rel_type in allowed_doc_ent_types:
                if target not in valid_entity_ids:
                    import_errors.append(f"Không tìm thấy Target Entity ID: '{target}' cho quan hệ '{source}' -> {rel_type}")
                    continue
                valid_rels.append((source, target, rel_type, evidence, confidence, method, "doc_ent"))
                doc_ent_count += 1
                
        # Now run Cypher queries to merge validated relations
        with driver.session(database=db_name) as session:
            for source, target, rel_type, evidence, confidence, method, rgroup in valid_rels:
                if rgroup == "doc_doc":
                    query = f"""
                    MATCH (s:Document {{id: $source}})
                    MATCH (t:Document {{id: $target}})
                    MERGE (s)-[r:{rel_type}]->(t)
                    SET r.evidence = $evidence, r.confidence = $confidence, r.method = $method
                    """
                else: # doc_ent
                    elabel = entity_label_map[rel_type]
                    query = f"""
                    MATCH (s:Document {{id: $source}})
                    MATCH (t:{elabel} {{entity_id: $target}})
                    MERGE (s)-[r:{rel_type}]->(t)
                    SET r.evidence = $evidence, r.confidence = $confidence, r.method = $method
                    """
                session.run(query, {"source": source, "target": target, "evidence": evidence, "confidence": confidence, "method": method})
                
        print(f"✅ Nạp Relationships thành công: {doc_doc_count} Doc-Doc, {doc_ent_count} Doc-Entity.")
        
        # 9. Đọc đếm cơ sở dữ liệu để in kết quả
        print("\n🔍 Đang truy vấn cơ sở dữ liệu để thống kê...")
        node_counts = {}
        rel_counts = {}
        
        with driver.session(database=db_name) as session:
            # Count nodes by label
            for label in ["Document", "CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"]:
                res = session.run(f"MATCH (n:{label}) RETURN count(n) AS count")
                node_counts[label] = res.single()["count"]
                
            # Count relationships by type
            for rtype in ["THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI", "BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"]:
                res = session.run(f"MATCH ()-[r:{rtype}]->() RETURN count(r) AS count")
                rel_counts[rtype] = res.single()["count"]
                
        # Print summary
        print("\n" + "="*50)
        print("📊 BÁO CÁO NHẬP ĐỒ THỊ KNOWLEDGE GRAPH:")
        print("="*50)
        print("📈 Số lượng NODES theo Label:")
        for label, count in node_counts.items():
            print(f"  - (:{label}): {count}")
            
        print("\n📈 Số lượng RELATIONSHIPS theo Type:")
        for rtype, count in rel_counts.items():
            print(f"  - [:{rtype}]: {count}")
            
        print(f"\n❌ Số lỗi import ghi nhận: {len(import_errors)}")
        if import_errors:
            print("\n🔍 CHI TIẾT CÁC LỖI IMPORT:")
            for err in import_errors[:10]:
                print(f"  - {err}")
            if len(import_errors) > 10:
                print(f"  - ... và {len(import_errors) - 10} lỗi khác.")
                
        print("==================================================")
        print("🎉 KẾT QUẢ BƯỚC 8: [PASS]")
        
    except Exception as e:
        print("\n==================================================")
        print("❌ KẾT QUẢ BƯỚC 8: [FAIL]")
        print(f"Gặp lỗi trong quá trình import: {str(e)}")
        print("==================================================")
        if driver:
            try:
                driver.close()
            except:
                pass
        sys.exit(1)
        
    finally:
        # 10. Đóng Neo4j driver đúng cách
        if driver:
            driver.close()
            print("🔒 Đã đóng kết nối driver Neo4j thành công.")

if __name__ == "__main__":
    main()
