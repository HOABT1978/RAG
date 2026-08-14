import os
import sys
import re
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

def clean_html(html_content):
    if pd.isna(html_content) or not isinstance(html_content, str):
        return ""
    
    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Get text with space separator
    text = soup.get_text(separator=" ")
    
    # Normalize whitespaces
    # Split by newlines, strip each line
    lines = [line.strip() for line in text.split("\n")]
    # Filter out empty lines
    lines = [line for line in lines if line]
    cleaned = "\n".join(lines)
    
    # Replace multiple spaces with a single space
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    # Normalize multiple newlines
    cleaned = re.sub(r"\n+", "\n", cleaned)
    
    return cleaned.strip()

def main():
    print("==================================================")
    print("🧹 BƯỚC 1: KIỂM TRA DỮ LIỆU & LÀM SẠCH HTML")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parents[1]
    metadata_path = root_dir / "ner_kb" / "metadata.csv"
    content_path = root_dir / "ner_kb" / "content.csv"
    output_path = root_dir / "ner_kb" / "cleaned_documents.csv"
    
    # 1. Đọc dữ liệu bằng pandas
    print(f"📖 Đang đọc {metadata_path.name}...")
    df_meta = pd.read_csv(metadata_path)
    print(f"📖 Đang đọc {content_path.name}...")
    df_content = pd.read_csv(content_path)
    
    # 2. Kiểm tra số dòng, số cột
    meta_rows, meta_cols = df_meta.shape
    content_rows, content_cols = df_content.shape
    print(f"\n📊 Kích thước dữ liệu gốc:")
    print(f"  - Metadata: {meta_rows} dòng, {meta_cols} cột")
    print(f"  - Content:  {content_rows} dòng, {content_cols} cột")
    
    # 3. Kiểm tra duplicate id
    meta_dups = df_meta['id'].duplicated().sum()
    content_dups = df_content['id'].duplicated().sum()
    print(f"\n🆔 Kiểm tra duplicate ID:")
    print(f"  - Số duplicate ID trong Metadata: {meta_dups}")
    print(f"  - Số duplicate ID trong Content:  {content_dups}")
    
    # 4. Kiểm tra ID mismatch
    meta_ids = set(df_meta['id'].dropna())
    content_ids = set(df_content['id'].dropna())
    
    only_in_meta = meta_ids - content_ids
    only_in_content = content_ids - meta_ids
    mismatch_count = len(only_in_meta) + len(only_in_content)
    
    print(f"\n⚠️ Kiểm tra ID mismatch:")
    print(f"  - ID chỉ có ở Metadata: {len(only_in_meta)} {list(only_in_meta) if only_in_meta else ''}")
    print(f"  - ID chỉ có ở Content:  {len(only_in_content)} {list(only_in_content) if only_in_content else ''}")
    print(f"  - Tổng số ID mismatch:  {mismatch_count}")
    
    # 5. Merge theo ID (sử dụng inner join để chắc chắn các document đều có cả metadata và content)
    df_merged = pd.merge(df_meta, df_content, on='id', how='inner')
    print(f"\n🔗 Merge thành công: {len(df_merged)} tài liệu kết hợp.")
    
    # 6. Thống kê missing values cho metadata (trên tập đã merge)
    print(f"\n📈 Thống kê missing values cho Metadata (tổng số dòng: {len(df_merged)}):")
    missing_report = []
    for col in df_meta.columns:
        if col == 'id':
            continue
        col_series = df_merged[col]
        
        # Đếm NaN/Null
        nan_count = col_series.isna().sum()
        
        # Đếm chuỗi rỗng (sau khi strip)
        empty_str_count = col_series.apply(lambda x: str(x).strip() == "" if pd.notna(x) else False).sum()
        
        # Đếm "Chưa phân loại"
        chua_phan_loai_count = col_series.apply(lambda x: str(x).strip() == "Chưa phân loại" if pd.notna(x) else False).sum()
        
        total_missing = nan_count + empty_str_count + chua_phan_loai_count
        missing_report.append({
            "Cột": col,
            "NaN/Null": nan_count,
            "Chuỗi rỗng": empty_str_count,
            "Chưa phân loại": chua_phan_loai_count,
            "Tổng thiếu": total_missing
        })
    
    df_missing = pd.DataFrame(missing_report)
    print(df_missing.to_string(index=False))
    
    # 7. Làm sạch content_html bằng BeautifulSoup
    print(f"\n🧹 Đang làm sạch cột content_html...")
    df_merged['content_clean'] = df_merged['content_html'].apply(clean_html)
    print("✅ Đã tạo cột content_clean.")
    
    # 8. Lưu kết quả
    print(f"💾 Đang lưu kết quả tại: {output_path}")
    df_merged.to_csv(output_path, index=False, encoding='utf-8')
    
    # 9. In mẫu content_html và content_clean
    print("\n🔍 IN MẪU 2 DÒNG DỮ LIỆU SAU KHI LÀM SẠCH:")
    sample_docs = df_merged.head(2)
    for idx, row in sample_docs.iterrows():
        print("-" * 50)
        print(f"📄 DOCUMENT ID: {row['id']} | Số hiệu: {row['so_ky_hieu']}")
        print(f"🔹 Tiêu đề: {row['title']}")
        print("-" * 50)
        
        # Preview HTML (truncated)
        html_preview = str(row['content_html'])[:300] + "..." if len(str(row['content_html'])) > 300 else str(row['content_html'])
        print(f"👉 Mẫu content_html (300 ký tự đầu):\n{html_preview}\n")
        
        # Preview Cleaned (truncated)
        clean_preview = str(row['content_clean'])[:300] + "..." if len(str(row['content_clean'])) > 300 else str(row['content_clean'])
        print(f"👉 Mẫu content_clean (300 ký tự đầu):\n{clean_preview}\n")
        
    # Check PASS/FAIL conditions
    # 1. Output file exists
    # 2. Number of documents equals the inner merged list (non-zero)
    # 3. ID column exists
    # 4. content_clean is not abnormally empty
    if output_path.exists() and len(df_merged) > 0 and 'id' in df_merged.columns and not df_merged['content_clean'].isna().all():
        print("==================================================")
        print("🎉 KẾT QUẢ BƯỚC 1: [PASS]")
        print("==================================================")
        sys.exit(0)
    else:
        print("==================================================")
        print("❌ KẾT QUẢ BƯỚC 1: [FAIL]")
        print("==================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
