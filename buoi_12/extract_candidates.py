import os
import sys
import re
import pandas as pd
from pathlib import Path

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

# Regex to detect Vietnamese legal document number signs (so_ky_hieu)
# e.g., 32/2024/QH15, 73/2016/NĐ-CP, 17/VBHN-BTC
SO_KY_HIEU_PATTERN = r'\b\d+/(?:\d{4}|VBHN)/[A-Za-z0-9Đđ\-\_]+\b'

# Triggers to search for in case-insensitive mode, ordered by length/specificity
TRIGGER_WORDS = [
    ("sửa đổi, bổ sung", "sửa đổi, bổ sung"),
    ("sửa đổi", "sửa đổi"),
    ("bổ sung", "bổ sung"),
    ("bãi bỏ", "bãi bỏ"),
    ("thay thế", "thay thế"),
    ("căn cứ", "căn cứ"),
]

def standardize_so_ky_hieu(match_str):
    """Standardize mixed-case document signs (e.g., 73/2016/nđ-cp -> 73/2016/NĐ-CP)"""
    parts = match_str.strip().split('/')
    if len(parts) >= 3:
        parts[-1] = parts[-1].upper()
        return '/'.join(parts)
    return match_str.upper()

def find_trigger_in_text(text):
    """Checks if any trigger word exists in the text and returns the trigger string"""
    text_lower = text.lower()
    for word, label in TRIGGER_WORDS:
        if word in text_lower:
            return label
    return None

def main():
    print("==================================================")
    print("📋 BƯỚC 2: RULE-BASED CANDIDATE EXTRACTION")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parents[1]
    input_path = root_dir / "ner_kb" / "cleaned_documents.csv"
    output_path = root_dir / "ner_kb" / "relation_candidates.csv"
    
    if not input_path.exists():
        print(f"❌ Không tìm thấy file cleaned_documents.csv tại: {input_path}")
        print("💡 Vui lòng chạy clean_data.py trước.")
        sys.exit(1)
        
    print(f"📖 Đang đọc {input_path.name}...")
    df = pd.read_csv(input_path)
    
    candidates = []
    
    for idx, row in df.iterrows():
        source_id = row['id']
        source_so_ky_hieu = row['so_ky_hieu']
        content = row['content_clean']
        
        if pd.isna(content) or not isinstance(content, str):
            continue
            
        # Split text into lines, then split each line into sentences
        raw_lines = content.split('\n')
        sentences = []
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            # Split line by sentence punctuation (. or ! or ? followed by space)
            parts = re.split(r'(?<=[.!?])\s+', line)
            for p in parts:
                p = p.strip()
                if p:
                    sentences.append(p)
                    
        # Scan sentences to find document signs
        for i, sentence in enumerate(sentences):
            # Find all document signs in current sentence
            matches = re.findall(SO_KY_HIEU_PATTERN, sentence)
            if not matches:
                continue
                
            for match in matches:
                target_so_ky_hieu = standardize_so_ky_hieu(match)
                
                # Rule 5: Loại bỏ tự tham chiếu chính văn bản
                if target_so_ky_hieu == source_so_ky_hieu:
                    continue
                    
                # Search trigger in the current sentence
                trigger = find_trigger_in_text(sentence)
                evidence = sentence
                
                # Rule 3: Nếu không thấy trigger ở câu hiện tại, thử tìm ở câu ngay trước đó
                # (đặc biệt hữu ích cho trường hợp danh sách gạch đầu dòng)
                if not trigger and i > 0:
                    prev_sentence = sentences[i-1]
                    prev_trigger = find_trigger_in_text(prev_sentence)
                    if prev_trigger:
                        trigger = prev_trigger
                        evidence = f"{prev_sentence} \n {sentence}"
                        
                # Nếu vẫn không thấy trigger nào, đặt mặc định là "tham chiếu"
                if not trigger:
                    trigger = "tham chiếu"
                    
                candidates.append({
                    "source_id": source_id,
                    "source_so_ky_hieu": source_so_ky_hieu,
                    "target_so_ky_hieu": target_so_ky_hieu,
                    "trigger": trigger,
                    "evidence": evidence
                })
                
    # Create DataFrame
    df_candidates = pd.DataFrame(candidates)
    
    if df_candidates.empty:
        print("⚠️ Không tìm thấy candidate nào.")
        # Create empty DataFrame with required columns
        df_candidates = pd.DataFrame(columns=["source_id", "source_so_ky_hieu", "target_so_ky_hieu", "trigger", "evidence"])
    else:
        # Rule 6: Loại duplicate candidates
        # Một duplicate candidate có cùng source_id, source_so_ky_hieu, target_so_ky_hieu và trigger
        prev_len = len(df_candidates)
        df_candidates = df_candidates.drop_duplicates(subset=["source_id", "target_so_ky_hieu", "trigger"])
        new_len = len(df_candidates)
        print(f"♻️ Loại bỏ trùng lặp: Giảm từ {prev_len} xuống {new_len} candidates.")
        
    # Save output
    print(f"💾 Đang lưu {len(df_candidates)} candidates tại: {output_path}")
    df_candidates.to_csv(output_path, index=False, encoding='utf-8')
    
    # 9. In thống kê
    total_candidates = len(df_candidates)
    print(f"\n📊 THỐNG KÊ KẾT QUẢ:")
    print(f"  - Tổng số candidate phát hiện: {total_candidates}")
    
    if total_candidates > 0:
        print(f"\n📈 Số candidate theo trigger:")
        trigger_counts = df_candidates['trigger'].value_counts()
        for trg, count in trigger_counts.items():
            print(f"  - {trg}: {count}")
            
        print(f"\n🔍 HIỂN THỊ 10 CANDIDATE MẪU:")
        sample_size = min(10, total_candidates)
        df_sample = df_candidates.head(sample_size)
        for idx, row in df_sample.iterrows():
            print("-" * 50)
            print(f"🎯 Candidate {idx+1}:")
            print(f"  - Source Doc ID:     {row['source_id']} ({row['source_so_ky_hieu']})")
            print(f"  - Target Doc Sign:   {row['target_so_ky_hieu']}")
            print(f"  - Trigger Word:      {row['trigger']}")
            print(f"  - Evidence Preview:  {row['evidence'][:150]}...")
            
    print("==================================================")
    if output_path.exists():
        print("🎉 KẾT QUẢ BƯỚC 2: [PASS]")
        sys.exit(0)
    else:
        print("❌ KẾT QUẢ BƯỚC 2: [FAIL]")
        sys.exit(1)

if __name__ == "__main__":
    main()
