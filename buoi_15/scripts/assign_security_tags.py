import os
import sys
import json
import io
import pandas as pd
from pathlib import Path

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Resolve paths
script_dir = Path(__file__).resolve().parent
buoi_15_dir = script_dir.parent
input_path = buoi_15_dir / "data" / "processed" / "chunks_normalized.csv"
output_path = buoi_15_dir / "data" / "processed" / "chunks_secure.csv"

# Load the normalized chunks
if not input_path.exists():
    print(f"Error: Normalized corpus not found at {input_path}. Please verify preprocessing.")
    sys.exit(1)

df = pd.read_csv(input_path)

# Keywords definition
hr_keywords = ["nhân sự", "lương thưởng", "tuyển dụng", "bổ nhiệm", "kỷ luật", "chế độ lương", "lao động", "phụ cấp", "nghỉ phép", "hợp đồng lao động"]
risk_keywords = ["tín dụng", "rủi ro", "hạn mức", "phê duyệt vay", "nợ xấu", "thế chấp", "bảo lãnh", "cho vay", "cầm cố", "phê duyệt duyệt vay"]

def assign_roles(row):
    text = str(row['text']).lower()
    title = str(row['title']).lower()
    doc_id = str(row['document_id']).lower()
    
    # 1. Check HR matching
    if any(kw in text for kw in hr_keywords) or any(kw in title for kw in hr_keywords):
        return json.dumps(["Admin", "HR"])
        
    # 2. Check Risk & Credit matching
    if any(kw in text for kw in risk_keywords) or any(kw in title for kw in risk_keywords):
        return json.dumps(["Admin", "Risk_Manager", "Staff"])
        
    # 3. Default: General documents (accessible by everyone including Guest)
    return json.dumps(["Admin", "HR", "Risk_Manager", "Staff", "Guest"])

# Apply the tagging function
df['allowed_roles'] = df.apply(assign_roles, axis=1)

# ASSERTION CHECKS:
# 1. No null allowed_roles
assert df['allowed_roles'].notnull().all(), "Error: Some rows have null allowed_roles!"

# 2. At least one role is assigned and valid JSON array format
for idx, val in df['allowed_roles'].items():
    try:
        roles_list = json.loads(val)
        assert isinstance(roles_list, list) and len(roles_list) >= 1
    except Exception as e:
        raise AssertionError(f"Error: Invalid security tagging format at row {idx}: {e}")

# Compute Statistics
stats = df['allowed_roles'].value_counts()

print("\n=== THỐNG KÊ PHÂN PHỐI QUYỀN TRUY CẬP (SECURITY TAGS) ===")
for roles_json, count in stats.items():
    roles_list = json.loads(roles_json)
    print(f"allowed_roles: {str(roles_list):<45} | Số lượng: {count:<5} chunks | Tỷ lệ: {count/len(df)*100:.2f}%")

# Display 3 Representative Samples for each security tier
print("\n=== MẪU DÒNG DỮ LIỆU ĐẠI DIỆN CHO CÁC CẤP ĐỘ BẢO MẬT ===")

# Tier 1: HR Only (High Security)
hr_subset = df[df['allowed_roles'] == json.dumps(["Admin", "HR"])]
if not hr_subset.empty:
    sample = hr_subset.iloc[0]
    print(f"\n[+] CẤP ĐỘ BẢO MẬT CAO (HR & Admin)")
    print(f"    - Chunk ID: {sample['chunk_id']}")
    print(f"    - Document ID: {sample['document_id']}")
    print(f"    - Title: {sample['title']}")
    print(f"    - Allowed Roles: {sample['allowed_roles']}")
    print(f"    - Snippet: {sample['text'][:180]}...")

# Tier 2: Risk Manager (Medium Security)
risk_subset = df[df['allowed_roles'] == json.dumps(["Admin", "Risk_Manager", "Staff"])]
if not risk_subset.empty:
    sample = risk_subset.iloc[0]
    print(f"\n[+] CẤP ĐỘ BẢO MẬT TRUNG BÌNH (Risk Manager, Staff & Admin)")
    print(f"    - Chunk ID: {sample['chunk_id']}")
    print(f"    - Document ID: {sample['document_id']}")
    print(f"    - Title: {sample['title']}")
    print(f"    - Allowed Roles: {sample['allowed_roles']}")
    print(f"    - Snippet: {sample['text'][:180]}...")

# Tier 3: General / Guest (Low Security / Public)
public_subset = df[df['allowed_roles'] == json.dumps(["Admin", "HR", "Risk_Manager", "Staff", "Guest"])]
if not public_subset.empty:
    sample = public_subset.iloc[0]
    print(f"\n[+] CẤP ĐỘ BẢO MẬT THẤP / CÔNG CỘNG (Mọi vai trò bao gồm Guest)")
    print(f"    - Chunk ID: {sample['chunk_id']}")
    print(f"    - Document ID: {sample['document_id']}")
    print(f"    - Title: {sample['title']}")
    print(f"    - Allowed Roles: {sample['allowed_roles']}")
    print(f"    - Snippet: {sample['text'][:180]}...")

# Save output
df.to_csv(output_path, index=False, encoding='utf-8')
print(f"\n[SUCCESS] Đã ghi tệp tin kết quả thành công tại: {output_path}")
