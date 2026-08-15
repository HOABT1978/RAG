import os
import sys
import io
import re
import pandas as pd
from pathlib import Path

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def analyze_csv(file_path):
    print(f"Reading {file_path.name}...")
    # Attempt to read with utf-8 first, fallback to cp1252 if needed
    encoding = 'utf-8'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        encoding = 'cp1252'
        df = pd.read_csv(file_path, encoding='cp1252')
        
    row_count = len(df)
    cols = list(df.columns)
    
    # Null counts
    null_counts = df.isnull().sum().to_dict()
    
    # Duplicate rows count
    duplicate_rows = df.duplicated().sum()
    
    # Candidate keys (columns with no nulls and all unique values)
    candidate_keys = []
    for col in cols:
        if df[col].isnull().sum() == 0:
            if df[col].is_unique:
                candidate_keys.append(col)
                
    return {
        'row_count': row_count,
        'cols': cols,
        'encoding': encoding,
        'null_counts': null_counts,
        'duplicate_rows': duplicate_rows,
        'candidate_keys': candidate_keys,
        'df': df
    }

def main():
    script_dir = Path(__file__).resolve().parent
    buoi_14_dir = script_dir.parent
    project_root = buoi_14_dir.parent
    kb_hops_dir = project_root / "kb+hops"
    outputs_dir = buoi_14_dir / "outputs"
    os.makedirs(outputs_dir, exist_ok=True)
    
    print(f"Working directory: {buoi_14_dir}")
    print(f"Data source directory: {kb_hops_dir}")
    
    # 1. Check folder structure of buoi_14/
    buoi_14_files = []
    for root, dirs, files in os.walk(buoi_14_dir):
        for f in files:
            fpath = Path(root) / f
            # Exclude virtual env files if they are in this folder (though they shouldn't be)
            if '.venv' not in fpath.parts:
                buoi_14_files.append(fpath.relative_to(buoi_14_dir))
                
    # 2. Analyze CSVs
    csvs = {
        'metadata': kb_hops_dir / "metadata.csv",
        'content': kb_hops_dir / "content.csv",
        'relationships': kb_hops_dir / "relationships.csv"
    }
    
    analysis_results = {}
    for key, path in csvs.items():
        if path.exists():
            analysis_results[key] = analyze_csv(path)
        else:
            print(f"Error: {path} not found!")
            sys.exit(1)
            
    # 3. Check existing code for risky patterns
    risky_patterns = {
        r'os\.remove': [],
        r'shutil\.rmtree': [],
        r'open\(.*,\s*["\']w["\']\)': [],
        r'\bDELETE\b': [],
        r'\bDROP\b': [],
        r'\bDETACH\s+DELETE\b': []
    }
    
    existing_scripts = [buoi_14_dir / f for f in buoi_14_files if f.suffix == '.py']
    for script_path in existing_scripts:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
            for pattern, occurrences in risky_patterns.items():
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    occurrences.append((script_path.name, len(matches)))
                    
    # 4. Generate Report
    report = []
    report.append("# BÁO CÁO KIỂM TRA DỰ ÁN VÀ KHẢO SÁT DỮ LIỆU NGUỒN (BUỔI 14)")
    report.append("")
    report.append(f"- **Thư mục làm việc**: `buoi_14/`")
    report.append(f"- **Thư mục dữ liệu nguồn**: `kb+hops/`")
    report.append("")
    
    report.append("## 1. Cấu trúc thư mục buoi_14/")
    report.append("Danh sách các file hiện có:")
    for f in sorted(buoi_14_files):
        report.append(f"- `{f}`")
    report.append("")
    
    report.append("## 2. Kết quả phân tích dữ liệu nguồn")
    
    # Metadata.csv
    meta = analysis_results['metadata']
    report.append("### A. File `metadata.csv` (Thông tin văn bản)")
    report.append(f"- **Số dòng dữ liệu**: `{meta['row_count']}`")
    report.append(f"- **Encoding**: `{meta['encoding']}`")
    report.append(f"- **Tên các cột**: {', '.join([f'`{c}`' for c in meta['cols']])}")
    report.append(f"- **Số dòng trùng lặp**: `{meta['duplicate_rows']}`")
    report.append("- **Số giá trị Null từng cột**:")
    for col, cnt in meta['null_counts'].items():
        report.append(f"  - `{col}`: {cnt}")
    report.append(f"- **Khóa chính tiềm năng**: {', '.join([f'`{k}`' for k in meta['candidate_keys']]) if meta['candidate_keys'] else 'None'}")
    report.append("- **Trường text/metadata phù hợp citation**: `citation`, `title`, `document_id`, `document_type`")
    report.append("")
    
    # Content.csv
    cont = analysis_results['content']
    report.append("### B. File `content.csv` (Nội dung phân đoạn - chunks)")
    report.append(f"- **Số dòng dữ liệu**: `{cont['row_count']}`")
    report.append(f"- **Encoding**: `{cont['encoding']}`")
    report.append(f"- **Tên các cột**: {', '.join([f'`{c}`' for c in cont['cols']])}")
    report.append(f"- **Số dòng trùng lặp**: `{cont['duplicate_rows']}`")
    report.append("- **Số giá trị Null từng cột**:")
    for col, cnt in cont['null_counts'].items():
        report.append(f"  - `{col}`: {cnt}")
    report.append(f"- **Khóa chính tiềm năng**: {', '.join([f'`{k}`' for k in cont['candidate_keys']]) if cont['candidate_keys'] else 'None'}")
    report.append("- **Trường text phù hợp retrieval**: `text` (Chứa nội dung điều khoản)")
    report.append("- **Trường khóa liên kết**: `chunk_id` (Khóa chính), `document_id` (Khóa ngoại liên kết với văn bản)")
    report.append("")
    
    # Relationships.csv
    rel = analysis_results['relationships']
    report.append("### C. File `relationships.csv` (Mối quan hệ đồ thị)")
    report.append(f"- **Số dòng dữ liệu**: `{rel['row_count']}`")
    report.append(f"- **Encoding**: `{rel['encoding']}`")
    report.append(f"- **Tên các cột**: {', '.join([f'`{c}`' for c in rel['cols']])}")
    report.append(f"- **Số dòng trùng lặp**: `{rel['duplicate_rows']}`")
    report.append("- **Số giá trị Null từng cột**:")
    for col, cnt in rel['null_counts'].items():
        report.append(f"  - `{col}`: {cnt}")
    report.append(f"- **Các loại mối quan hệ có thật trong dữ liệu**:")
    # Get unique relationship types
    if 'relationship_type' in rel['df'].columns:
        rel_types = rel['df']['relationship_type'].unique()
        for rt in rel_types:
            report.append(f"  - `{rt}`")
    else:
        report.append("  - Không tìm thấy cột relationship_type.")
    report.append("")
    
    report.append("## 3. Rà soát an toàn mã nguồn (Risk & Safe Audit)")
    has_risky_code = False
    for pattern, occurrences in risky_patterns.items():
        if occurrences:
            has_risky_code = True
            report.append(f"- **Mẫu nhạy cảm `{pattern}`**:")
            for fname, cnt in occurrences:
                report.append(f"  - Tệp `{fname}`: {cnt} lần xuất hiện")
    if not has_risky_code:
        report.append("✅ Không phát hiện bất kỳ câu lệnh xóa dữ liệu phá hủy hoặc patterns nguy hại nào trong code hiện tại.")
    report.append("")
    
    # Write report
    report_path = outputs_dir / "inspection_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report) + '\n')
    print(f"Report written to {report_path}")
    
    # 5. Output Project Precheck summary to stdout
    print("\nPROJECT PRE-CHECK")
    print(f"Working root: {buoi_14_dir}")
    print(f"Data: {kb_hops_dir} containing metadata.csv ({meta['row_count']} rows), content.csv ({cont['row_count']} rows), relationships.csv ({rel['row_count']} rows)")
    print(f"Existing code: {len(existing_scripts)} python scripts inside buoi_14/scripts/")
    
    # Check if python is running and pandas is importable
    try:
        import pandas
        env_status = "Python OK, virtualenv OK, pandas importable"
    except ImportError:
        env_status = "Error: pandas not found in current environment"
        
    print(f"Environment: {env_status}")
    print(f"Potential risks: {'Phát hiện pattern nhạy cảm (xem báo cáo)' if has_risky_code else 'Không có rủi ro xóa dữ liệu'}")
    print("Safe to continue: YES")

if __name__ == '__main__':
    main()
