# BÁO CÁO KIỂM TRA DỮ LIỆU VÀ MÔI TRƯỜNG (DEPENDENCY REPORT) - BUỔI 17

Báo cáo này kiểm tra tính sẵn sàng của dữ liệu nguồn từ Buổi 15/16 và khả năng tái sử dụng module `SecureRetriever` cho các tác vụ trong Buổi 17.

---

## 1. Kiểm tra dữ liệu nguồn (Source Data Inspection)

### 1.1. Thông tin chung
Cả hai tệp tin dữ liệu đều được lưu trữ tại `buoi_15/data/processed/` và được đọc thành công ở chế độ chỉ đọc (read-only):
* **Tệp dữ liệu chính**: `../buoi_15/data/processed/chunks_secure.csv`
* **Tệp đối chiếu**: `../buoi_15/data/processed/chunks_normalized.csv`

### 1.2. Thông số chi tiết

| Chỉ số | chunks_secure.csv | chunks_normalized.csv | Trạng thái đối chiếu |
| :--- | :--- | :--- | :--- |
| **Số dòng** | `6560` dòng | `6560` dòng | Khớp 100% |
| **Số cột** | `13` cột | `12` cột | Khớp (secure nhiều hơn 1 cột quyền) |
| **Cột `allowed_roles`** | **Có** | **Không** | Đúng thiết kế bảo mật |

### 1.3. Chi tiết danh sách cột thực tế
* **Cột trong `chunks_secure.csv`**:
  1. `chunk_id`
  2. `document_id`
  3. `text`
  4. `source_file`
  5. `title`
  6. `document_type` *(tương đương `loai_van_ban`)*
  7. `chapter`
  8. `section`
  9. `article`
  10. `clause`
  11. `effective_date` *(tương đương `ngay_ban_hanh`)*
  12. `status`
  13. `allowed_roles`
* **Cột trong `chunks_normalized.csv`**:
  Giống hoàn toàn với `chunks_secure.csv` ngoại trừ cột `allowed_roles` thứ 13.

### 1.4. Đối chiếu tính toàn vẹn dữ liệu
* Kiểm tra so khớp từng ô dữ liệu (excluding `allowed_roles`): **Khớp 100%**.
* Công thức xác lập: 
  $$\text{chunks\_secure.csv} = \text{chunks\_normalized.csv} + \text{allowed\_roles}$$
* **Đánh giá cột theo yêu cầu thực hành**:
  - Có sẵn: `chunk_id`, `document_id`, `title`, `allowed_roles`.
  - Không có sẵn cột `citation` (sẽ được sinh động bởi mã nguồn của bộ tìm kiếm).
  - Tên cột thực tế có một số khác biệt nhỏ so với tài liệu lý thuyết (ví dụ: dùng `document_type` thay cho `loai_van_ban`, dùng `effective_date` thay cho `ngay_ban_hanh`, không có cột `co_quan_ban_hanh` trong dữ liệu Buổi 15 này). Dữ liệu hoàn toàn đủ điều kiện sử dụng trực tiếp.

---

## 2. Phân tích mã nguồn `SecureRetriever` của Buổi 15/16

### 2.1. Thông tin Module và Khởi tạo
- **Đường dẫn tệp tin**: [buoi_15/src/secure_retriever.py](file:///d:/Rag_thuchanh/RAG/buoi_15/src/secure_retriever.py)
- **Class chính**: `SecureRetriever`
- **Helper class**: `SecureDenseRetriever`

### 2.2. Cơ chế phân quyền và Truy xuất
- **Đầu vào vai trò (Input role)**: Danh sách các chuỗi đại diện cho vai trò người dùng, ví dụ `user_roles = ["Risk_Manager", "Staff"]`.
- **Cơ chế lọc quyền**: **Lọc trước (Pre-filtering)**.
  - Trước khi thực hiện bất kỳ phương pháp tìm kiếm nào, dữ liệu gốc `self.df` được chuyển qua hàm `filter_authorized_df(user_roles)` để giữ lại phân đoạn hợp lệ.
  - Các bộ tìm kiếm `BM25Retriever` và `SecureDenseRetriever` được khởi tạo trực tiếp trên DataFrame đã lọc này. Do đó, các phân đoạn không được phép xem sẽ bị loại bỏ hoàn toàn khỏi không gian tìm kiếm trước khi tính điểm tương đồng hoặc đưa vào context của LLM.
- **Dữ liệu đầu ra (Output)**: Một danh sách các từ điển kết quả chứa đầy đủ thông tin:
  - `rank` (Thứ hạng kết quả)
  - `chunk_id` (Được giữ nguyên)
  - `document_id` (Được giữ nguyên)
  - `text` (Nội dung phân đoạn)
  - `score` (Điểm số BM25/Dense/Rerank)
  - `citation` (Chuỗi trích dẫn dạng `[Title | Chapter | Section | Article | Chunk_ID]`)
  - `retrieval_method` (Phương thức tìm kiếm được thực hiện)
  - `allowed_roles` (Danh sách các vai trò được phép đọc phân đoạn này)

---

## 3. Kết luận và Kế hoạch tái sử dụng

```text
SOURCE DATA: PASS
RBAC DATA AVAILABLE: YES
SECURE RETRIEVER REUSABLE: YES
REUSE PLAN:
- Tái sử dụng module `SecureRetriever` từ `buoi_15/src/secure_retriever.py` bằng cách đưa thư mục `buoi_15` vào `sys.path` của các script trong Buổi 17.
- Tạo một adapter `secure_retrieval_adapter.py` trong thư mục `buoi_17/scripts/` để bọc lớp `SecureRetriever` cũ, đảm bảo đầu ra chuẩn hóa đúng cấu trúc yêu cầu của Buổi 17 mà không làm ảnh hưởng hay sửa đổi mã nguồn gốc của các buổi trước.
```
