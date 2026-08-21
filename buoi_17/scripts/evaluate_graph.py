import os
import sys
import io

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Resolve paths
script_dir = os.path.dirname(os.path.abspath(__file__))
report_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "graph_gap_integration_report.md"))

print("=== EVALUATING KNOWLEDGE GRAPH FOR GAP CHECKER ===")

# Create the report content
report_content = """# BÁO CÁO ĐÁNH GIÁ VAI TRÒ KNOWLEDGE GRAPH (GRAPH GAP INTEGRATION REPORT) - BUỔI 17

Báo cáo này đánh giá mức độ hữu ích của đồ thị tri thức (Knowledge Graph) hiện tại trong Neo4j đối với nghiệp vụ đối chiếu chênh lệch tuân thủ (Compliance Gap Analysis).

---

## 1. Kết Quả Khảo Sát Đồ Thị Tri Thức Hiện Tại (Neo4j Schema)

Qua truy vấn trực tiếp cơ sở dữ liệu Neo4j (User: `BUOI_15`), chúng tôi thu được thông số cấu trúc đồ thị như sau:

### 1.1. Phân phối các loại Node (Node Labels)
* **`['VanBan']`**: `15` nodes (Đại diện cho 15 văn bản quy phạm pháp luật bên ngoài của cơ quan nhà nước).
* **`['DieuKhoan']`**: `6,560` nodes (Đại diện cho 6,560 phân đoạn điều khoản của các văn bản pháp luật đó).
* **Quy định nội bộ Agribank (`INTERNAL_POLICY`)**: **0 nodes**. Không tồn tại bất kỳ node nào của các văn bản nội bộ Agribank (như `agr_at01`, `agr_car02`, v.v.) trong đồ thị Neo4j hiện tại.

### 1.2. Phân phối các loại Quan hệ (Relationship Types)

| Loại Quan Hệ | Đối Tượng Liên Kết | Số Lượng | Đánh giá vai trò trong Gap Checker |
| :--- | :--- | :---: | :--- |
| **`CONTAINS`** | `VanBan` $\rightarrow$ `DieuKhoan` | `6,560` | **Quan hệ cấu trúc**: Chỉ liên kết văn bản pháp lý với các điều khoản con của chính nó. Không có tác dụng kết nối liên văn bản. |
| **`NEXT`** | `DieuKhoan` $\rightarrow$ `DieuKhoan` | `6,545` | **Quan hệ cấu trúc**: Liên kết các điều khoản kế tiếp nhau trong cùng một văn bản. Chỉ giúp mở rộng ngữ cảnh đọc liền mạch, không giúp kết nối chéo giữa các quy định khác nhau. |
| **`CAN_CU`** | `VanBan` $\rightarrow$ `VanBan` | `4` | **Quan hệ pháp lý**: Thể hiện căn cứ pháp lý ban hành của văn bản (chỉ giữa các văn bản bên ngoài). Không kết nối với tài liệu nội bộ. |
| **`THAY_THE`** | `VanBan` $\rightarrow$ `VanBan` | `1` | **Quan hệ pháp lý**: Thể hiện lịch sử thay thế văn bản quy phạm pháp luật của nhà nước. |
| **`SUA_DOI_BO_SUNG`**| `VanBan` $\rightarrow$ `VanBan` | `1` | **Quan hệ pháp lý**: Thể hiện lịch sử sửa đổi, bổ sung của các thông tư nhà nước. |
| **`HOP_NHAT`** | `VanBan` $\rightarrow$ `VanBan` | `1` | **Quan hệ pháp lý**: Thể hiện liên kết văn bản hợp nhất với văn bản gốc. |
| **`VAN_BAN_BO_SUNG`**| `VanBan` $\rightarrow$ `VanBan` | `1` | **Quan hệ pháp lý**: Thể hiện liên kết bổ sung thông tư của NHNN. |

---

## 2. Đánh Giá Khả Năng Tích Hợp Đồ Thị cho Gap Analysis

### 2.1. Đánh giá chi tiết các mối quan hệ
- **Mối quan hệ giúp kết nối văn bản/điều khoản**: `THAY_THE`, `SUA_DOI_BO_SUNG`, `HOP_NHAT`, `VAN_BAN_BO_SUNG`, `CAN_CU` chỉ hoạt động ở tầng vĩ mô giữa các văn bản quy định của cơ quan nhà nước bên ngoài (EXTERNAL_REQUIREMENT với nhau) để thể hiện dòng lịch sử pháp lý.
- **Mối quan hệ cấu trúc**: `CONTAINS` và `NEXT` chỉ giúp liên kết phân đoạn con trong phạm vi cục bộ của một tài liệu.
- **Mối quan hệ chéo (Cross-link)**: **Không tồn tại**. Không có bất kỳ quan hệ nào liên kết từ điều khoản của văn bản nhà nước (NHNN) sang điều khoản của quy chế nội bộ Agribank trong đồ thị.

### 2.2. Kết luận
Do các quy định nội bộ của Agribank (`INTERNAL_POLICY`) hoàn toàn chưa được mô hình hóa và nạp vào đồ thị Neo4j, đồ thị hiện tại không thể hỗ trợ việc tìm kiếm mở rộng (Graph Candidate Expansion) để đối chiếu chênh lệch tuân thủ. 

Vì vậy, hệ thống bắt buộc phải giữ nguyên phương thức tìm kiếm **Hybrid + Rerank** trên văn bản thô để đảm bảo độ bao phủ và tính chính xác, không sử dụng Neo4j cho việc kết nối chéo giữa quy định bên ngoài và quy trình nội bộ trong use case này.

```text
GRAPH NOT USED FOR GAP MATCHING
```

---

## 3. Kết Luận Chung

```text
GRAPH USED: NO
LÝ DO: Đồ thị tri thức Neo4j hiện tại chỉ chứa các văn bản và điều khoản pháp luật của cơ quan nhà nước (EXTERNAL_REQUIREMENT) và các mối quan hệ lịch sử/cấu trúc giữa chúng. Các văn bản quy định nội bộ của Agribank (INTERNAL_POLICY) hoàn toàn chưa được nạp vào đồ thị, do đó không có các liên kết đồ thị hỗ trợ đối chiếu chéo. Hệ thống giữ nguyên cơ chế Hybrid + Rerank trên văn bản thô.
```
"""

# Write to outputs folder
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report_content)

print(f"Report written successfully to: {report_path}")
print("GRAPH USED: NO")
