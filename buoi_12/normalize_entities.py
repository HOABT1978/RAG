import sys
import re
import unicodedata
import pandas as pd
from pathlib import Path

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

# Alias map for standardizing common abbreviations in Vietnamese legal context
ALIAS_MAP = {
    "nhnn": "Ngân hàng Nhà nước Việt Nam",
    "ngân hàng nhà nước": "Ngân hàng Nhà nước Việt Nam",
    "ngân hàng nhà nước vn": "Ngân hàng Nhà nước Việt Nam",
    "nhnn vn": "Ngân hàng Nhà nước Việt Nam",
    "btc": "Bộ Tài chính",
    "bộ tc": "Bộ Tài chính",
    "cp": "Chính phủ",
    "qh": "Quốc hội",
}

def remove_accents(input_str):
    """Removes combining marks to create ascii-friendly IDs."""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    # Replace Đ/đ specifically
    nfkd_form = nfkd_form.replace('Đ', 'D').replace('đ', 'd')
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def generate_entity_id(entity_type, canonical_name):
    """Generates a clean, deterministic entity_id."""
    name_no_accents = remove_accents(canonical_name)
    name_clean = re.sub(r'[^a-zA-Z0-9]', '_', name_no_accents)
    name_clean = re.sub(r'_+', '_', name_clean).strip('_').lower()
    return f"{entity_type.lower()}_{name_clean}"

def clean_text(text):
    """Clean spaces and normalize unicode to NFC."""
    if pd.isna(text) or not isinstance(text, str):
        return ""
    # Normalize Unicode to NFC
    text = unicodedata.normalize("NFC", text)
    # Strip spaces
    text = text.strip()
    # Normalize inner spaces
    text = re.sub(r'\s+', ' ', text)
    return text

def normalize_entity_name(name):
    """Applies clean text and matches against ALIAS_MAP."""
    cleaned = clean_text(name)
    cleaned_lower = cleaned.lower()
    if cleaned_lower in ALIAS_MAP:
        return ALIAS_MAP[cleaned_lower]
    return cleaned

def main():
    print("==================================================")
    print("🔄 BƯỚC 4: CHUẨN HÓA ENTITY")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parents[1]
    input_path = root_dir / "ner_kb" / "extracted_entities_raw.csv"
    output_path = root_dir / "ner_kb" / "entities.csv"
    
    if not input_path.exists():
        print(f"❌ Không tìm thấy file extracted_entities_raw.csv tại: {input_path}")
        print("💡 Vui lòng chạy enrich_metadata.py trước.")
        sys.exit(1)
        
    print(f"📖 Đang đọc {input_path.name}...")
    df_raw = pd.read_csv(input_path)
    
    initial_count = len(df_raw)
    print(f"🔹 Số lượng thực thể thô ban đầu: {initial_count}")
    
    normalized_list = []
    merged_aliases = []
    
    for idx, row in df_raw.iterrows():
        raw_name = str(row['entity'])
        entity_type = str(row['entity_type'])
        
        # 1. Clean and normalize
        canonical_name = normalize_entity_name(raw_name)
        original_name = clean_text(raw_name)
        
        # Track if an alias was merged
        if canonical_name.lower() != original_name.lower():
            merged_aliases.append((original_name, canonical_name))
            
        # 2. Generate unique canonical ID
        entity_id = generate_entity_id(entity_type, canonical_name)
        
        normalized_list.append({
            "entity_id": entity_id,
            "entity_type": entity_type,
            "canonical_name": canonical_name,
            "original_name": original_name,
            "source_doc_id": row['source_doc_id'],
            "method": row['method'],
            "confidence": row['confidence'],
            "evidence": clean_text(str(row['evidence']))
        })
        
    df_norm = pd.DataFrame(normalized_list)
    
    # 2. Loại duplicate
    # Deduplicate: Keep one record per document, entity type, and canonical name.
    # We sort by confidence descending first, so we keep the mention with highest confidence.
    df_norm = df_norm.sort_values(by="confidence", ascending=False)
    dedup_count_prev = len(df_norm)
    
    df_norm = df_norm.drop_duplicates(subset=["source_doc_id", "entity_type", "canonical_name"])
    final_count = len(df_norm)
    
    # Sort by document ID and entity ID for clean output
    df_norm = df_norm.sort_values(by=["source_doc_id", "entity_type", "canonical_name"])
    
    print(f"♻️ Đã loại trùng lặp: Giảm từ {dedup_count_prev} xuống {final_count} dòng.")
    
    # Save output
    print(f"💾 Đang lưu {len(df_norm)} thực thể đã chuẩn hóa tại: {output_path}")
    df_norm.to_csv(output_path, index=False, encoding='utf-8')
    
    # In thống kê
    print("\n" + "="*50)
    print("📊 THỐNG KÊ KẾT QUẢ BƯỚC 4:")
    print("="*50)
    print(f"🔹 Số entity trước chuẩn hóa (thô): {initial_count}")
    print(f"🔹 Số entity sau chuẩn hóa (sạch): {final_count}")
    
    print(f"\n📈 Danh sách các alias được merge thành công ({len(merged_aliases)}):")
    unique_merges = set(merged_aliases)
    if unique_merges:
        for orig, canon in sorted(unique_merges):
            print(f"  - '{orig}' ➔ '{canon}'")
    else:
        print("  - Không có alias viết tắt nào cần merge thêm (dữ liệu thô đã sạch).")
        
    print(f"\n🔍 HIỂN THỊ 10 ENTITY MẪU SAU KHI CHUẨN HÓA:")
    df_sample = df_norm.head(10)
    for idx, row in df_sample.iterrows():
        print("-" * 50)
        print(f" thực thể {idx+1}:")
        print(f"  - Entity ID:       {row['entity_id']}")
        print(f"  - Entity Type:     {row['entity_type']}")
        print(f"  - Canonical Name:  {row['canonical_name']}")
        print(f"  - Original Name:   {row['original_name']}")
        print(f"  - Doc ID:          {row['source_doc_id']}")
        print(f"  - Confidence:      {row['confidence']}")
        print(f"  - Evidence:        {row['evidence'][:100]}...")
        
    print("==================================================")
    if output_path.exists():
        print("🎉 KẾT QUẢ BƯỚC 4: [PASS]")
        sys.exit(0)
    else:
        print("❌ KẾT QUẢ BƯỚC 4: [FAIL]")
        sys.exit(1)

if __name__ == "__main__":
    main()
