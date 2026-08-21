# Technical Specification - Buổi 06 (Hướng dẫn AI Agent)

Tài liệu quy định và hướng dẫn cho AI Agent thực hiện dự án Buổi 06.

---

## 1. Quy định Workspace (Thư mục & Phạm vi truy cập)

### Chỉ được phép đọc:
- `RAG/rag_foundation/buoi_05/output/chunks/`
- `RAG/rag_foundation/buoi_05/.venv/`
- `RAG/rag_foundation/buoi_06/`

### Không được đọc:
- Source code của Buổi 05
- `README` các buổi trước
- Jupyter Notebooks
- Git history
- Các thư mục khác ngoài phạm vi được phép

> **Lưu ý:** Buổi 05 là **black box**. Không reverse engineering. Không phân tích cách Buổi 05 hoạt động.

---

## 2. Môi trường Python (Python Environment)

- Sử dụng đúng interpreter trong: `RAG/rag_foundation/buoi_05/.venv/`
- **Không** tạo virtual environment mới.

---

## 3. Thư viện & Package (Dependencies)

**Chỉ cài đặt và sử dụng các thư viện sau:**
- `streamlit`
- `google-genai`
- `chromadb`
- `psycopg`
- `python-dotenv`

> **Lưu ý:** Không cài thêm framework hoặc thư viện ngoài danh sách trên.

---

## 4. Phong cách lập trình (Coding Style)

- **Ưu tiên:** Ít file, ít class, ít function, code rõ ràng và dễ đọc.
- **Không áp dụng các design pattern phức tạp:** Không tạo repository pattern, service layer, dependency injection, factory, plugin architecture.

---

## 5. Phạm vi tính năng (Scope)

**Chỉ thực hiện các phần:**
1. **Index**: Đánh chỉ mục dữ liệu
2. **Retrieval**: Tìm kiếm / Lấy dữ liệu liên quan
3. **Answer**: Sinh câu trả lời dựa trên thông tin thu thập
4. **Streamlit**: Giao diện người dùng đơn giản

> Không mở rộng hoặc phát triển thêm tính năng ngoài yêu cầu trên.

---

## 6. Xử lý lỗi (Error Handling)

- Chỉ dùng `try/except` ở mức tối thiểu cho các điểm dễ phát sinh lỗi cơ bản.
- **Không cần:** Cơ chế retry, hệ thống logging nâng cao, monitoring.

---

## 7. Bảo mật (Security)

- **Tuyệt đối không in (log/print):** API Key, password, token, secret.

---

## 8. Kích thước Code (Code Size)

- **Mục tiêu:** Tổng kích thước khoảng **300–500 dòng** code Python.
- **Hạn mức:** Nếu vượt khoảng **700 dòng**, cần tiến hành đơn giản hóa thiết kế.
