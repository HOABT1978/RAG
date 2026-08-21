import os
import sys
import io
import pandas as pd

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Resolve paths
script_dir = os.path.dirname(os.path.abspath(__file__))
secure_csv = os.path.abspath(os.path.join(script_dir, "..", "data", "chunks_combined_secure.csv"))
report_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "gap_input_catalog.md"))

print("=== INSPECTING DATA FOR COMPLIANCE GAP CHECKER (COMBINED SECURE CORPUS) ===")
print(f"Reading secure CSV from: {secure_csv}")

df = pd.read_csv(secure_csv)
unique_docs = df.drop_duplicates(subset=['document_id'])
total_docs = len(unique_docs)

print(f"Found {total_docs} unique documents in the dataset.")

# Analyze and classify each document
catalog_items = []
internal_policy_count = 0
external_req_count = 0

for idx, row in unique_docs.iterrows():
    doc_id = str(row['document_id'])
    title = str(row.get('title', '')).strip()
    so_ky_hieu = str(row.get('so_ky_hieu', '')).strip()
    loai_van_ban = str(row.get('loai_van_ban', '')).strip()
    co_quan_ban_hanh = str(row.get('co_quan_ban_hanh', '')).strip()
    ngay_ban_hanh = str(row.get('ngay_ban_hanh', '')).strip()
    
    # Classify based on the issuing agency metadata
    co_quan_lower = co_quan_ban_hanh.lower()
    is_internal = "agribank" in co_quan_lower or "nông nghiệp" in co_quan_lower
    
    if is_internal:
        classification = "INTERNAL_POLICY"
        evidence = f"Văn bản nội bộ được ban hành bởi Agribank (Ký hiệu: {so_ky_hieu})."
        internal_policy_count += 1
    else:
        classification = "EXTERNAL_REQUIREMENT"
        evidence = f"Văn bản pháp lý cấp Nhà nước ({loai_van_ban}) ban hành bởi {co_quan_ban_hanh} (Ký hiệu: {so_ky_hieu})."
        external_req_count += 1
        
    catalog_items.append({
        'document_id': doc_id,
        'title': title,
        'so_ky_hieu': so_ky_hieu,
        'loai_van_ban': loai_van_ban,
        'co_quan_ban_hanh': co_quan_ban_hanh,
        'ngay_ban_hanh': ngay_ban_hanh,
        'classification': classification,
        'evidence': evidence
    })

print(f"Classification summary: EXTERNAL_REQUIREMENT={external_req_count}, INTERNAL_POLICY={internal_policy_count}")

# Generate MD report
md_content = f"""# DANH MỤC TÀI LIỆU PHÂN TÍCH TUÂN THỦ (GAP INPUT CATALOG) - BUỔI 17

Danh mục này tổng hợp và phân loại các tài liệu từ dữ liệu nguồn `buoi_17/data/chunks_combined_secure.csv` phục vụ cho Use Case 2: Phân tích chênh lệch tuân thủ (Compliance Gap Analysis).

---

## 1. Thống Kê Chung
* **Tổng số văn bản (Unique Documents)**: `{total_docs}` văn bản.
* **Số văn bản yêu cầu pháp lý bên ngoài (EXTERNAL_REQUIREMENT)**: `{external_req_count}` văn bản.
* **Số văn bản quy định nội bộ ngân hàng (INTERNAL_POLICY)**: `{internal_policy_count}` văn bản.

---

## 2. Chi Tiết Danh Mục Phân Loại Văn Bản

"""
for item in catalog_items:
    md_content += f"""### Văn bản ID: `{item['document_id']}`
* **Tiêu đề**: *"{item['title']}"*
* **Ký hiệu**: `{item['so_ky_hieu']}`
* **Loại văn bản**: `{item['loai_van_ban']}`
* **Cơ quan ban hành**: `{item['co_quan_ban_hanh']}`
* **Ngày ban hành**: `{item['ngay_ban_hanh']}`
* **Phân loại (Classification)**: `{item['classification']}`
* **Bằng chứng phân loại (Evidence)**: {item['evidence']}

---
"""

# Append readiness status
if internal_policy_count == 0:
    md_content += """
## 3. Đánh Giá Sẵn Sàng Dữ Liệu

> [!CAUTION]
> Kết quả phân tích cho thấy không tồn tại bất kỳ quy định nội bộ nào của ngân hàng (INTERNAL_POLICY) trong tập dữ liệu nguồn.
> Do thiếu dữ liệu đối chiếu từ phía nội bộ ngân hàng, hệ thống không thể thực hiện phân tích chênh lệch tuân thủ thực tế trên corpus này.

```text
COMPLIANCE GAP DATA: INSUFFICIENT
DATA GAP: INTERNAL POLICY NOT FOUND
```
"""
    gap_status = "INSUFFICIENT"
    data_gap = "INTERNAL POLICY NOT FOUND"
else:
    md_content += """
## 3. Đánh Giá Sẵn Sàng Dữ Liệu

> [!NOTE]
> Kết quả kiểm tra dữ liệu cho thấy corpus tích hợp thành công cả các văn bản quy định pháp lý của Nhà nước (EXTERNAL_REQUIREMENT) và các quy định/quy chế nội bộ của Agribank (INTERNAL_POLICY).
> Hệ thống có đầy đủ dữ liệu đối chiếu từ hai phía và sẵn sàng thực hiện việc phân tích chênh lệch tuân thủ.

```text
COMPLIANCE GAP DATA: READY
```
"""
    gap_status = "READY"
    data_gap = "NONE"

# Write MD report
with open(report_path, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"\nReport written successfully to: {report_path}")
print(f"COMPLIANCE GAP DATA: {gap_status}")
if gap_status == "INSUFFICIENT":
    print(f"DATA GAP: {data_gap}")
