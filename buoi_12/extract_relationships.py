import sys
import re
import pandas as pd
from pathlib import Path

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

def normalize_ky_hieu_for_lookup(kh):
    """Normalize sign strings for key lookup (removes spaces, mixes case)"""
    if pd.isna(kh) or not isinstance(kh, str):
        return ""
    # Strip, uppercase and remove spaces
    return kh.strip().upper().replace(" ", "")

def main():
    print("==================================================")
    print("🔗 BƯỚC 5: RELATIONSHIP EXTRACTION")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parents[1]
    docs_path = root_dir / "ner_kb" / "cleaned_documents.csv"
    candidates_path = root_dir / "ner_kb" / "relation_candidates.csv"
    entities_path = root_dir / "ner_kb" / "entities.csv"
    metadata_path = root_dir / "ner_kb" / "enriched_metadata.csv"
    output_path = root_dir / "ner_kb" / "relationships_raw.csv"
    
    # Check inputs
    for p in [docs_path, candidates_path, entities_path, metadata_path]:
        if not p.exists():
            print(f"❌ Không tìm thấy file đầu vào: {p}")
            sys.exit(1)
            
    print("📖 Đang đọc dữ liệu đầu vào...")
    df_candidates = pd.read_csv(candidates_path)
    df_entities = pd.read_csv(entities_path)
    df_metadata = pd.read_csv(metadata_path)
    
    # Create lookup map for document signs to IDs
    so_ky_hieu_to_id = {}
    for idx, row in df_metadata.iterrows():
        kh_norm = normalize_ky_hieu_for_lookup(row['so_ky_hieu'])
        if kh_norm:
            so_ky_hieu_to_id[kh_norm] = row['id']
            
    relationships = []
    
    # -------------------------------------------------------------------------
    # 1. Tạo Document -> Document relations
    # -------------------------------------------------------------------------
    print("🔗 Đang xử lý Document -> Document relations...")
    doc_doc_count = 0
    for idx, row in df_candidates.iterrows():
        source_id = str(row['source_id'])
        target_so_ky_hieu = str(row['target_so_ky_hieu'])
        trigger = str(row['trigger'])
        evidence = str(row['evidence'])
        
        # Look up target ID if it exists in our 30 docs
        target_kh_norm = normalize_ky_hieu_for_lookup(target_so_ky_hieu)
        target_id = so_ky_hieu_to_id.get(target_kh_norm)
        
        # If target_id exists in our corpus, use it. Otherwise, use target_so_ky_hieu.
        resolved_target = str(target_id) if target_id else target_so_ky_hieu
        
        # Classify relationship_type
        t = trigger.lower().strip()
        relationship_type = None
        
        if t in ["căn cứ", "tham chiếu"]:
            relationship_type = "THAM_CHIEU"
        elif t in ["sửa đổi, bổ sung", "sửa đổi", "bổ sung", "bãi bỏ"]:
            relationship_type = "SUA_DOI_BO_SUNG"
        elif t in ["thay thế"]:
            relationship_type = "THAY_THE_BOI"
            
        if not relationship_type:
            continue
            
        # Determine direction
        if relationship_type == "THAY_THE_BOI":
            # Rule 4: Thay thế bởi có chiều: Document cũ -> Document mới
            # target (the one being replaced) is old, source (the active scanning doc) is new
            rel_source = resolved_target
            rel_target = source_id
        else:
            rel_source = source_id
            rel_target = resolved_target
            
        relationships.append({
            "source": rel_source,
            "target": rel_target,
            "relationship_type": relationship_type,
            "method": "rule",
            "confidence": 1.0,
            "evidence": evidence
        })
        doc_doc_count += 1
        
    print(f"  - Đã trích xuất {doc_doc_count} quan hệ Document -> Document.")
    
    # -------------------------------------------------------------------------
    # 2. Tạo Document -> Entity relations
    # -------------------------------------------------------------------------
    print("🔗 Đang xử lý Document -> Entity relations...")
    doc_ent_count = 0
    
    # Map entity_type to relationship_type
    entity_rel_map = {
        "CoQuan": "BAN_HANH_BOI",
        "NguoiKy": "KY_BOI",
        "DoiTuongApDung": "AP_DUNG_CHO",
        "LinhVuc": "THUOC_LINH_VUC"
    }
    
    for idx, row in df_entities.iterrows():
        source_doc_id = str(row['source_doc_id'])
        entity_id = str(row['entity_id'])
        entity_type = str(row['entity_type'])
        confidence = row['confidence']
        evidence = str(row['evidence'])
        method = str(row['method'])
        
        relationship_type = entity_rel_map.get(entity_type)
        if not relationship_type:
            # Skip ChucDanh, Nganh, etc.
            continue
            
        relationships.append({
            "source": source_doc_id,
            "target": entity_id,
            "relationship_type": relationship_type,
            "method": method,
            "confidence": confidence,
            "evidence": evidence
        })
        doc_ent_count += 1
        
    print(f"  - Đã trích xuất {doc_ent_count} quan hệ Document -> Entity.")
    
    # Create DataFrame
    df_rels = pd.DataFrame(relationships)
    
    if df_rels.empty:
        df_rels = pd.DataFrame(columns=["source", "target", "relationship_type", "method", "confidence", "evidence"])
    else:
        # Rule 8: Loại duplicate
        # Sort by confidence descending so we keep highest confidence if duplicates exist
        df_rels = df_rels.sort_values(by="confidence", ascending=False)
        prev_len = len(df_rels)
        df_rels = df_rels.drop_duplicates(subset=["source", "target", "relationship_type"])
        print(f"♻️ Đã loại trùng lặp: Giảm từ {prev_len} xuống {len(df_rels)} dòng.")
        
    # Save output
    print(f"💾 Đang lưu {len(df_rels)} quan hệ tại: {output_path}")
    df_rels.to_csv(output_path, index=False, encoding='utf-8')
    
    # 10. In thống kê
    print("\n" + "="*50)
    print("📊 THỐNG KÊ KẾT QUẢ BƯỚC 5:")
    print("="*50)
    print(f"🔹 Tổng số quan hệ trích xuất (sạch): {len(df_rels)}")
    
    if not df_rels.empty:
        print(f"\n📈 Số lượng quan hệ theo loại (relationship_type):")
        type_counts = df_rels['relationship_type'].value_counts()
        for rtype, count in type_counts.items():
            print(f"  - {rtype}: {count}")
            
        print(f"\n🔍 HIỂN THỊ 10 QUAN HỆ MẪU:")
        df_sample = df_rels.head(10)
        for idx, row in df_sample.iterrows():
            print("-" * 50)
            print(f"Quan hệ {idx+1}:")
            print(f"  - Source:             {row['source']}")
            print(f"  - Target:             {row['target']}")
            print(f"  - Type:               {row['relationship_type']}")
            print(f"  - Method/Confidence:  {row['method']} ({row['confidence']})")
            print(f"  - Evidence Preview:   {row['evidence'][:150]}...")
            
    print("==================================================")
    if output_path.exists() and len(df_rels) > 0:
        print("🎉 KẾT QUẢ BƯỚC 5: [PASS]")
        sys.exit(0)
    else:
        print("❌ KẾT QUẢ BƯỚC 5: [FAIL]")
        sys.exit(1)

if __name__ == "__main__":
    main()
