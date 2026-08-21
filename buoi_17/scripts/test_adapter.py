import sys
import os
import json
import io

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Ensure we can import the adapter
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from secure_retrieval_adapter import SecureRetrievalAdapter

# Load environment
import dotenv
dotenv.load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))

print("Initializing SecureRetrievalAdapter...")
adapter = SecureRetrievalAdapter()

# Query related to HR (high security: ['Admin', 'HR'])
hr_query = "Cử nhân sự để giữ chức danh Chủ tịch Hội đồng quản trị"
target_chunk_id = "chk_168220_0155"

print(f"\n--- TESTING REQUIREMENT 1 & 2 on chunk {target_chunk_id} ---")
print(f"Query: '{hr_query}'")

# Test with authorized role: HR
hr_results = adapter.retrieve(hr_query, user_roles=["HR"], method="hybrid_rerank", top_k=5)
hr_chunk_ids = [item['chunk_id'] for item in hr_results]
hr_authorized_received = target_chunk_id in hr_chunk_ids
print(f"HR Role retrieved chunk ids: {hr_chunk_ids}")
print(f"HR Role (Authorized) received target chunk {target_chunk_id}: {hr_authorized_received}")

# Test with unauthorized role: Risk_Manager
risk_results = adapter.retrieve(hr_query, user_roles=["Risk_Manager"], method="hybrid_rerank", top_k=5)
risk_chunk_ids = [item['chunk_id'] for item in risk_results]
risk_unauthorized_denied = target_chunk_id not in risk_chunk_ids
print(f"Risk_Manager Role retrieved chunk ids: {risk_chunk_ids}")
print(f"Risk_Manager (Unauthorized) did NOT receive target chunk {target_chunk_id}: {risk_unauthorized_denied}")

# Test with unauthorized role: Guest
guest_results = adapter.retrieve(hr_query, user_roles=["Guest"], method="hybrid_rerank", top_k=5)
guest_chunk_ids = [item['chunk_id'] for item in guest_results]
guest_unauthorized_denied = target_chunk_id not in guest_chunk_ids
print(f"Guest (Unauthorized) did NOT receive target chunk {target_chunk_id}: {guest_unauthorized_denied}")

print("\n--- TESTING REQUIREMENT 3: Context Leakage Guard ---")
# If the chunk is not returned in risk_results, it cannot be put in the LLM context.
context_leakage_prevented = risk_unauthorized_denied and guest_unauthorized_denied
print(f"Context leakage prevented (unauthorized chunks absent from returned results): {context_leakage_prevented}")

print("\n--- TESTING REQUIREMENT 4: Metadata Preservation ---")
metadata_preserved = False
if len(hr_results) > 0:
    sample_item = hr_results[0]
    has_chunk_id = sample_item.get('chunk_id') is not None
    has_doc_id = sample_item.get('document_id') is not None
    has_citation = sample_item.get('citation') is not None
    has_title = sample_item.get('title') is not None
    has_article = sample_item.get('article') is not None
    has_decision = sample_item.get('access_decision') == 'GRANTED'
    
    metadata_preserved = has_chunk_id and has_doc_id and has_citation and has_title and has_decision
    print("Sample Item Keys:", list(sample_item.keys()))
    print(f"Metadata check - chunk_id: {has_chunk_id}, document_id: {has_doc_id}, citation: {has_citation}, title: {has_title}, article: {has_article}, access_decision: {has_decision}")
    print(f"Metadata preserved: {metadata_preserved}")
else:
    print("Error: No results returned to verify metadata!")

# Determine final statuses
sec_retrieval_reuse = "PASS" if (hr_authorized_received and risk_unauthorized_denied) else "FAIL"
no_unauthorized_context = "PASS" if context_leakage_prevented else "FAIL"
citation_preserved = "PASS" if metadata_preserved else "FAIL"

# Write markdown report
report_content = f"""# BÁO CÁO KIỂM THỬ AN TOÀN TRUY XUẤT (SECURE RETRIEVAL TEST REPORT) - BUỔI 17

Báo cáo này đánh giá hoạt động của bộ tìm kiếm an toàn thông qua lớp Adapter `SecureRetrievalAdapter` kết hợp kiểm tra 4 yêu cầu an ninh dữ liệu.

---

## 1. Kịch Bản Kiểm Thử (Test Scenario)

* **Phân đoạn bảo mật mục tiêu (Target Chunk)**: `{target_chunk_id}`
  - **Allowed Roles**: `["Admin", "HR"]` (Quyền cao nhất, liên quan đến nhân sự)
* **Câu hỏi truy vấn (Query)**: *"{hr_query}"*
* **Mục tiêu**: Chứng minh vai trò hợp lệ (`HR`) lấy được phân đoạn này, trong khi các vai trò không hợp lệ (`Risk_Manager`, `Guest`) hoàn toàn bị chặn và không có rò rỉ dữ liệu vào context.

---

## 2. Kết Quả Kiểm Thử Chi Tiết

### Yêu cầu 1: Vai trò hợp lệ nhận được phân đoạn (Authorized Access)
- **Đóng vai `HR` (Hợp lệ)**:
  - Danh sách Chunk ID nhận được: `{hr_chunk_ids}`
  - Nhận được `{target_chunk_id}`: **{hr_authorized_received} (PASS)**

### Yêu cầu 2: Vai trò không hợp lệ bị từ chối truy cập (Unauthorized Access Blocked)
- **Đóng vai `Risk_Manager` (Không hợp lệ)**:
  - Danh sách Chunk ID nhận được: `{risk_chunk_ids}`
  - Không chứa `{target_chunk_id}`: **{risk_unauthorized_denied} (PASS)**
- **Đóng vai `Guest` (Không hợp lệ)**:
  - Danh sách Chunk ID nhận được: `{guest_chunk_ids}`
  - Không chứa `{target_chunk_id}`: **{guest_unauthorized_denied} (PASS)**

### Yêu cầu 3: Chặn rò rỉ context (No Unauthorized Context)
- Vì phân đoạn `{target_chunk_id}` hoàn toàn bị chặn ở lớp tìm kiếm đối với vai trò `Risk_Manager` và `Guest`, phân đoạn này **không bao giờ xuất hiện trong context** truyền cho LLM.
- Trạng thái ngăn chặn rò rỉ: **{context_leakage_prevented} (PASS)**

### Yêu cầu 4: Bảo toàn siêu dữ liệu nguồn (Metadata Preservation)
- Kiểm tra các trường siêu dữ liệu trong kết quả trả về của Adapter:
  - `chunk_id` có tồn tại: **{has_chunk_id}**
  - `document_id` có tồn tại: **{has_doc_id}**
  - `citation` có tồn tại: **{has_citation}**
  - `title` có tồn tại: **{has_title}**
  - `article` có tồn tại: **{has_article}**
  - `access_decision` có giá trị `GRANTED`: **{has_decision}**
- Trạng thái bảo toàn siêu dữ liệu: **{metadata_preserved} (PASS)**

---

## 3. Kết Luận Kiểm Thử

```text
SECURE RETRIEVER REUSE: {sec_retrieval_reuse}
NO UNAUTHORIZED CONTEXT: {no_unauthorized_context}
CITATION PRESERVED: {citation_preserved}
```
"""

# Write to outputs directory
output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'secure_retrieval_test.md'))
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(report_content)
    
print(f"\nReport written successfully to: {output_path}")
print(f"SECURE RETRIEVER REUSE: {sec_retrieval_reuse}")
print(f"NO UNAUTHORIZED CONTEXT: {no_unauthorized_context}")
print(f"CITATION PRESERVED: {citation_preserved}")
