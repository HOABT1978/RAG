import sys
import pandas as pd
from pathlib import Path

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("==================================================")
    print("🛠️ BƯỚC 6: VALIDATE RELATIONSHIPS")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parents[1]
    raw_path = root_dir / "ner_kb" / "relationships_raw.csv"
    docs_path = root_dir / "ner_kb" / "cleaned_documents.csv"
    entities_path = root_dir / "ner_kb" / "entities.csv"
    
    output_rels_path = root_dir / "ner_kb" / "relationships.csv"
    output_report_path = root_dir / "ner_kb" / "validation_report.csv"
    
    # Check inputs
    for p in [raw_path, docs_path, entities_path]:
        if not p.exists():
            print(f"❌ Không tìm thấy file đầu vào: {p}")
            sys.exit(1)
            
    print("📖 Đang đọc dữ liệu đầu vào...")
    df_raw = pd.read_csv(raw_path)
    df_docs = pd.read_csv(docs_path)
    df_entities = pd.read_csv(entities_path)
    
    # Store valid document and entity IDs as sets of strings for O(1) lookup
    valid_doc_ids = set(df_docs['id'].astype(str))
    valid_entity_ids = set(df_entities['entity_id'].astype(str))
    
    allowed_doc_doc_types = {"THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI"}
    allowed_doc_ent_types = {"BAN_HANH_BOI", "KY_BOI", "AP_DUNG_CHO", "THUOC_LINH_VUC"}
    all_allowed_types = allowed_doc_doc_types.union(allowed_doc_ent_types)
    
    report_records = []
    pass_records = []
    
    seen_relations = set()
    fail_counts = {}
    
    for idx, row in df_raw.iterrows():
        source = str(row['source']).strip()
        target = str(row['target']).strip()
        rel_type = str(row['relationship_type']).strip()
        method = str(row['method']).strip()
        confidence = row['confidence']
        evidence = str(row['evidence']).strip() if pd.notna(row['evidence']) else ""
        
        status = "PASS"
        reason = ""
        
        # 1. Validate relationship type
        if rel_type not in all_allowed_types:
            status = "FAIL"
            reason = f"Loại quan hệ không hợp lệ: '{rel_type}'"
            
        # 2. Check missing evidence
        elif not evidence or evidence.lower() == "nan" or evidence == "":
            status = "FAIL"
            reason = "Thiếu bằng chứng (evidence rỗng)"
            
        # 3. Check self-loop
        elif source == target:
            status = "FAIL"
            reason = "Self-loop (source trùng target)"
            
        # 4. Validate source existence (must always be a Document in corpus)
        elif source not in valid_doc_ids:
            status = "FAIL"
            reason = f"Source document '{source}' không tồn tại trong corpus"
            
        # 5. Validate target existence
        else:
            if rel_type in allowed_doc_doc_types:
                # For Doc -> Doc relations, target must exist in corpus
                if target not in valid_doc_ids:
                    status = "FAIL"
                    reason = f"Target document '{target}' không tồn tại trong corpus (closed-corpus)"
            elif rel_type in allowed_doc_ent_types:
                # For Doc -> Entity relations, target must exist in entities.csv
                if target not in valid_entity_ids:
                    status = "FAIL"
                    reason = f"Target entity '{target}' không tồn tại trong danh sách entities"
                    
        # 6. Check duplicate relation
        if status == "PASS":
            rel_key = (source, target, rel_type)
            if rel_key in seen_relations:
                status = "FAIL"
                reason = "Quan hệ bị trùng lặp (duplicate edge)"
            else:
                seen_relations.add(rel_key)
                
        # Record results
        record = {
            "source": source,
            "target": target,
            "relationship_type": rel_type,
            "method": method,
            "confidence": confidence,
            "evidence": evidence,
            "status": status,
            "reason": reason
        }
        
        report_records.append(record)
        
        if status == "PASS":
            pass_records.append({
                "source": source,
                "target": target,
                "relationship_type": rel_type,
                "method": method,
                "confidence": confidence,
                "evidence": evidence
            })
        else:
            fail_counts[reason] = fail_counts.get(reason, 0) + 1
            
    # Save output files
    df_report = pd.DataFrame(report_records)
    df_pass = pd.DataFrame(pass_records)
    
    print(f"💾 Đang lưu {len(df_pass)} quan hệ đạt chuẩn tại: {output_rels_path}")
    df_pass.to_csv(output_rels_path, index=False, encoding='utf-8')
    
    print(f"💾 Đang lưu báo cáo kiểm duyệt đầy đủ tại: {output_report_path}")
    df_report.to_csv(output_report_path, index=False, encoding='utf-8')
    
    # 11. In thống kê
    total_raw = len(df_raw)
    total_pass = len(df_pass)
    total_fail = total_raw - total_pass
    
    print("\n" + "="*50)
    print("📊 BÁO CÁO KẾT QUẢ BƯỚC 6:")
    print("="*50)
    print(f"🔹 Tổng số quan hệ thô đầu vào:  {total_raw}")
    print(f"🔹 Số lượng quan hệ ĐẠT (PASS):  {total_pass}")
    print(f"🔹 Số lượng quan hệ LOẠI (FAIL): {total_fail}")
    
    if total_pass > 0:
        print(f"\n📈 Số lượng quan hệ PASS theo loại (relationship_type):")
        type_counts = df_pass['relationship_type'].value_counts()
        for rtype, count in type_counts.items():
            print(f"  - {rtype}: {count}")
            
    if total_fail > 0:
        print(f"\n📈 Các lý do loại bỏ (FAIL) phổ biến:")
        for reason, count in sorted(fail_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {reason}: {count}")
            
    if total_pass > 0:
        print(f"\n🔍 HIỂN THỊ 10 QUAN HỆ ĐẠT (PASS) MẪU:")
        df_sample = df_pass.head(10)
        for idx, row in df_sample.iterrows():
            print("-" * 50)
            print(f"Quan hệ PASS {idx+1}:")
            print(f"  - Source:      {row['source']}")
            print(f"  - Target:      {row['target']}")
            print(f"  - Type:        {row['relationship_type']}")
            print(f"  - Evidence:    {row['evidence'][:120]}...")
            
    print("==================================================")
    if output_rels_path.exists() and output_report_path.exists():
        print("🎉 KẾT QUẢ BƯỚC 6: [PASS]")
        sys.exit(0)
    else:
        print("❌ KẾT QUẢ BƯỚC 6: [FAIL]")
        sys.exit(1)

if __name__ == "__main__":
    main()
