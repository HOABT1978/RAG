# HỆ THỐNG SECURE RAG & COMPLIANCE GAP ANALYSIS - BUỔI 17

Dự án này triển khai các tiêu chuẩn bảo mật dữ liệu, phân quyền truy cập nâng cao (RBAC), nhật ký kiểm toán (Audit Trail), mã hóa dữ liệu tại chỗ (Encryption-at-Rest) và Phân tích chênh lệch tuân thủ bằng AI (Compliance Gap Checker) tích hợp giao diện Streamlit Dashboard cho Agribank.

---

## 1. Cấu Trúc Thư Mục Bàn Giao

```text
buoi_17/
├── config/
│   └── rbac_policy.json            # Cấu hình vai trò, từ khóa phân loại và quyền truy cập
├── data/
│   ├── agribank_internal_policies.csv # Dữ liệu quy trình nội bộ Agribank (10 văn bản)
│   └── chunks_combined_secure.csv     # Dữ liệu tích hợp (787 NHNN + 24 Agribank chunks)
├── scripts/
│   ├── rbac.py                     # Quản lý chính sách bảo mật RBAC
│   ├── secure_retrieval.py         # Phân hệ tìm kiếm bảo mật phân quyền (Adapter)
│   ├── secure_retrieval_adapter.py # Lớp chuyển đổi lớp tìm kiếm từ Buổi 15
│   ├── audit_logger.py             # Hệ thống ghi nhật ký kiểm toán JSONL bảo mật
│   ├── internal_lookup.py          # Hệ thống tra cứu văn bản an toàn bằng AI
│   ├── compliance_gap.py           # Phân hệ đối chiếu chênh lệch tuân thủ bằng AI
│   ├── prepare_gap_data.py         # Kịch bản kiểm tra và phân loại dữ liệu nguồn
│   ├── security_tests.py           # Bộ kiểm thử bảo mật tích hợp (10 kịch bản)
│   └── final_validation.py         # Kịch bản nghiệm thu kiểm toán toàn diện
├── outputs/
│   ├── dependency_report.md        # Báo cáo đánh giá sự phụ thuộc môi trường
│   ├── rbac_test_report.md         # Báo cáo đánh giá tái sử dụng RBAC
│   ├── rbac_reuse_report.md        # Báo cáo phân phối vai trò dữ liệu
│   ├── audit_log.jsonl             # Tệp nhật ký kiểm toán độc lập
│   ├── internal_lookup_demo.md     # Báo cáo kết quả tra cứu bảo mật demo
│   ├── compliance_gap_results.csv  # Kết quả đối chiếu chênh lệch dạng bảng
│   ├── compliance_gap_report.md    # Báo cáo đối chiếu chênh lệch tuân thủ dạng Markdown
│   ├── security_test_report.md     # Báo cáo kết quả kiểm thử an toàn
│   └── final_validation_report.md  # Báo cáo nghiệm thu kiểm toán toàn diện
├── app.py                          # Giao diện Web Dashboard (Streamlit)
└── README.md                       # Tài liệu hướng dẫn sử dụng này
```

---

## 2. Hướng Dẫn Cấu Hình Môi Trường (.env)

Tạo tệp tin `buoi_17/.env` và cấu hình các thông số sau:

```env
# Khóa API Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Mô hình AI sử dụng
LLM_MODEL=gemini-2.5-flash

# Kết nối cơ sở dữ liệu đồ thị Neo4j
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=BUOI_15
NEO4J_PASSWORD=your_neo4j_password_here
NEO4J_DATABASE=neo4j
```

---

## 3. Quy Trình Khởi Chạy Hệ Thống

Để vận hành hệ thống kiểm tra và nghiệm thu, thực hiện lần lượt các bước dưới đây bằng Terminal:

### Bước 1: Khảo sát và phân loại dữ liệu đầu vào
Kiểm tra tính sẵn sàng của dữ liệu nguồn tích hợp để phân tích chênh lệch tuân thủ:
```bash
.venv\Scripts\python.exe buoi_17/scripts/prepare_gap_data.py
```
*Kết quả:* Phân loại thành công 15 văn bản NHNN (`EXTERNAL_REQUIREMENT`) và 10 văn bản Agribank (`INTERNAL_POLICY`). Báo cáo được xuất ra `buoi_17/outputs/gap_input_catalog.md`.

### Bước 2: Chạy Phân tích chênh lệch tuân thủ bằng AI (Gap Checker)
Thực hiện tìm kiếm điều khoản liên quan và đối chiếu tự động:
```bash
.venv\Scripts\python.exe buoi_17/scripts/compliance_gap.py
```
*Kết quả:* Đối chiếu 5 điều khoản lớn, phân loại tuân thủ (`DAP_UNG`, `CHENH_LECH`, `THIEU`), ghi nhận nhật ký kiểm toán và xuất kết quả ra CSV/Markdown tương ứng.

### Bước 3: Thực hiện kiểm thử bảo mật an toàn hệ thống
Chạy 10 kịch bản kiểm thử bảo mật tự động:
```bash
.venv\Scripts\python.exe buoi_17/scripts/security_tests.py
```
*Kết quả:* Xác nhận hệ thống đạt `SECURITY TESTS: PASS` (Kiểm thử phân quyền RBAC thành công, không lộ dữ liệu bị cấm, che giấu mật khẩu trong log, bảo toàn trích dẫn nguồn).

### Bước 4: Chạy kiểm toán nghiệm thu toàn hệ thống
Tự động audit toàn dự án và nghiệm thu nghiệm chuẩn:
```bash
.venv\Scripts\python.exe buoi_17/scripts/final_validation.py
```
*Kết quả:* Nghiệm thu toàn bộ tiêu chí bảo mật, xuất kết luận nghiệm thu ra `final_validation_report.md`.

### Bước 5: Khởi chạy Giao diện điều khiển Web Dashboard
```bash
.venv\Scripts\streamlit.exe run buoi_17/app.py
```
*Kết quả:* Giao diện web được mở tại địa chỉ `http://localhost:8501`. Cho phép tra cứu bảo mật phân quyền chéo, xem báo cáo gap trực quan, và duyệt nhật ký audit theo vai trò (Admin/Guest/HR/v.v.) thời gian thực.

---

## 4. Các Giải Pháp Công Nghệ Nổi Bật

1. **RBAC Pre-Filtering**: Áp dụng bộ lọc vai trò trực tiếp lên tập dữ liệu trước khi chạy BM25 hoặc Jaccard similarity. Người dùng không có quyền truy cập tuyệt đối không bao giờ làm rò rỉ dữ liệu hoặc đưa dữ liệu bảo mật vào context LLM.
2. **Audit Logging & Redaction**: Tự động che giấu các khóa bí mật như mật khẩu, API key, hoặc token dưới dạng `[REDACTED]`. Ghi nhật ký cả các truy cập bị từ chối (`DENIED`).
3. **Encryption-at-Rest Demo**: Sử dụng thư viện `cryptography/Fernet` để minh họa bảo mật mã hóa tệp nhật ký kiểm toán tại chỗ. Ghi nhận cảnh báo rõ ràng về các yêu cầu sản xuất nghiệp vụ thực tế (TLS, Key Rotation, KMS/HSM).
4. **Human Review Guardrail**: Tất cả phát hiện chênh lệch tuân thủ AI đối chiếu đều mang trạng thái bắt buộc kiểm tra thủ công `NEEDS_HUMAN_REVIEW` đề phòng ảo giác mô hình và đảm bảo tính chính xác cho kiểm toán viên.
