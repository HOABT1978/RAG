# HỆ THỐNG TRỢ LÝ KIỂM TOÁN & PHÂN TÍCH TUÂN THỦ AI (AI COMPLIANCE & AUDIT ASSISTANT) - BUỔI 18

Dự án này triển khai phân hệ AI nâng cao kết hợp bảo mật dữ liệu chuyên sâu phục vụ hai bài toán trọng tâm trong công tác quản trị và kiểm toán quy chế nội bộ tại Agribank:
1. **UC3 — AI Compliance Checker (Cross-policy Conflict Detection)**: So sánh đối chiếu chéo các văn bản nội bộ và quy định của Ngân hàng Nhà nước (NHNN), tự động phát hiện xung đột, mâu thuẫn hoặc chồng chéo và đánh giá mức độ rủi ro (Severity).
2. **UC4 — AI Audit Checklist Generator**: Tự động sinh chương trình/checklist kiểm toán rủi ro được cá nhân hóa theo Miền nghiệp vụ (Domain) và Đơn vị kiểm toán (Unit Scope), lọc theo quyền hạn người dùng (RBAC), kèm theo trích dẫn chính xác (Citations) tới các Điều/Khoản trong văn bản gốc.

---

## 1. Cấu Trúc Thư Mục Bàn Giao (Buổi 18)

Các thành phần của Buổi 18 được tích hợp trực tiếp trong thư mục `buoi_17/` và kế thừa các nền tảng bảo mật của buổi trước:

```text
buoi_17/
├── .env                              # File cấu hình môi trường bảo mật (API keys, path, model)
├── Buoi_18.md                        # Hướng dẫn chi tiết bài thực hành Buổi 18
├── README_18.md                      # Hướng dẫn vận hành hệ thống Buổi 18 (Tệp tin này)
├── app.py                            # Giao diện Web Dashboard (Streamlit) tích hợp UC3 & UC4
├── buoi_18_dashboard.html            # Dashboard HTML tĩnh/tương tác cao cấp phục vụ demo
├── run_buoi_18.bat                   # Batch script chạy tự động bộ Security Test & Streamlit App
├── run_dashboard_localhost.bat      # Batch script chạy Server Localhost hiển thị Dashboard HTML
├── config/
│   └── rbac_policy.json              # Chính sách phân quyền vai trò người dùng (Admin, Risk_Manager, KiemToanVien, Staff)
├── data/
│   ├── agribank_internal_policies.csv# Dữ liệu 10 văn bản quy định nội bộ Agribank (Read-Only)
│   └── chunks_combined_secure.csv    # Tập dữ liệu tích hợp bảo mật (811 chunks bao gồm NHNN & Agribank)
├── scripts/
│   ├── compliance_checker.py         # [UC3 Engine] Thực hiện so sánh chéo và phát hiện mâu thuẫn
│   ├── audit_checklist_gen.py        # [UC4 Engine] Sinh checklist kiểm toán theo Domain & Unit
│   ├── security_tests_b18.py         # Bộ kiểm thử bảo mật & an toàn dữ liệu (7 kịch bản kiểm thử)
│   ├── secure_retrieval_adapter.py   # Lớp trung gian tìm kiếm bảo mật phân quyền RBAC
│   └── audit_logger.py               # Module ghi nhật ký kiểm toán (Audit Trail) bảo mật
└── outputs/
    ├── b18_data_catalog.md           # Báo cáo thống kê, phân loại và chuẩn hóa dữ liệu đầu vào
    ├── compliance_conflicts.csv      # Bảng kết quả mâu thuẫn quy định dạng cấu trúc (UC3)
    ├── compliance_conflict_report.md # Báo cáo chi tiết các điểm mâu thuẫn dạng văn bản (UC3)
    ├── audit_checklist_results.csv   # Bảng checklist kiểm toán dạng cấu trúc (UC4)
    ├── audit_checklist_report.md     # Báo cáo chương trình kiểm toán dạng văn bản (UC4)
    ├── security_test_b18_report.md   # Báo cáo kết quả 7 bài kiểm tra an ninh bảo mật
    └── final_validation_b18_report.md# Báo cáo nghiệm thu kỹ thuật cuối cùng cho Buổi 18
```

---

## 2. Hướng Dẫn Cấu Hình Môi Trường (`.env`)

Tệp cấu hình `.env` được đặt tại thư mục gốc `buoi_17/.env`. Hãy đảm bảo các thông số sau đã được khai báo chính xác:

```env
# Đường dẫn dữ liệu đầu vào
SOURCE_AGRIBANK_INTERNAL_CSV=data/agribank_internal_policies.csv
SOURCE_COMBINED_SECURE_CSV=data/chunks_combined_secure.csv

# API Keys & LLM Configuration
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
LLM_API_KEY=YOUR_GEMINI_API_KEY
LLM_MODEL=gemini-2.5-flash

# Môi trường chạy
APP_ENV=training
```

---

## 3. Quy Trình Vận Hành & Thực Thi Hệ Thống

Để triển khai và nghiệm thu toàn bộ hệ thống, hãy thực hiện lần lượt các bước sau thông qua giao diện Terminal (với thư mục làm việc hiện tại là `buoi_17`):

### Bước 1: Phân loại dữ liệu đầu vào (Cataloging)
Kiểm tra cấu trúc dữ liệu, metadata và kiểm duyệt phân quyền:
```bash
..\.venv\Scripts\python.exe scripts/compliance_checker.py --catalog
```
*Kết quả:* Hệ thống ghi nhận **10 miền nghiệp vụ** với dữ liệu metadata đầy đủ 100% (Điều khoản, Citation, Allowed Roles). Báo cáo chi tiết xuất ra tại `outputs/b18_data_catalog.md`.

### Bước 2: Chạy động cơ đối chiếu chênh lệch tuân thủ (UC3 Compliance Checker)
Tiến hành quét chéo toàn bộ dữ liệu nội bộ để phát hiện mâu thuẫn:
```bash
..\.venv\Scripts\python.exe scripts/compliance_checker.py
```
*Kết quả:* Phát hiện các điểm xung đột giữa các văn bản nội bộ (ví dụ: hạn mức tiền mặt bọc thép vận chuyển giữa Quy định An toàn kho quỹ 100/QĐ vs Quy định Bảo hiểm 180/QĐ), gán Severity (`HIGH`, `MEDIUM`, `LOW`) kèm lý do nghiệp vụ. Kết quả được lưu tại:
* `outputs/compliance_conflicts.csv`
* `outputs/compliance_conflict_report.md`

### Bước 3: Chạy động cơ tạo checklist kiểm toán (UC4 Audit Checklist Generator)
Sinh bản nháp checklist theo cấu hình Domain & Unit:
```bash
..\.venv\Scripts\python.exe scripts/audit_checklist_gen.py
```
*Kết quả:* Tạo ra danh sách các mục kiểm toán rủi ro được gán Risk Level và trích dẫn chuẩn xác văn bản nguồn. Kết quả lưu tại:
* `outputs/audit_checklist_results.csv`
* `outputs/audit_checklist_report.md`

### Bước 4: Thực thi bộ kiểm thử an toàn bảo mật (Security Tests)
Kiểm tra 7 kịch bản kiểm soát rủi ro an ninh thông tin:
```bash
..\.venv\Scripts\python.exe scripts/security_tests_b18.py
```
*Kết quả:* Xác nhận hệ thống đạt trạng thái **PASS** tuyệt đối trên cả 7 bài test (bao gồm chặn truy cập chéo của vai trò thấp, bảo toàn tính đúng đắn của Citation, chặn ảo giác thông tin, ẩn thông tin nhạy cảm trong Audit Log, kiểm soát trạng thái phê duyệt của con người). Báo cáo lưu tại `outputs/security_test_b18_report.md`.

### Bước 5: Chạy báo cáo nghiệm thu kỹ thuật tổng hợp
Tự động quét nghiệm thu toàn diện hệ thống:
```bash
# Chạy script final_validation_b18 để nghiệm thu
..\.venv\Scripts\python.exe -c "import os; print('=== RUNNING FINAL VALIDATION ==='); exec(open('scripts/security_tests_b18.py').read())"
```
Báo cáo nghiệm thu cuối cùng được xuất ra tại `outputs/final_validation_b18_report.md` với đánh giá tổng thể đạt tiêu chuẩn bàn giao.

---

## 4. Hướng Dẫn Khởi Chạy Giao Diện Người Dùng (UI)

Hệ thống cung cấp hai phương thức hiển thị trực quan sinh động phù hợp cho các buổi báo cáo và nghiệm thu:

### Cách 1: Khởi chạy Streamlit Web App (Tương tác thời gian thực)
Kích hoạt nhanh bằng cách chạy tệp tin tiện ích `run_buoi_18.bat` tại thư mục `buoi_17`:
```bash
run_buoi_18.bat
```
Hoặc khởi chạy thủ công thông qua CLI:
```bash
..\.venv\Scripts\streamlit.exe run app.py
```
* **Địa chỉ truy cập**: `http://localhost:8501`
* **Giao diện tích hợp**:
  * **Sidebar**: Cho phép giả lập vai trò người dùng (Admin, Risk Manager, KiemToanVien, Staff), hiển thị tình trạng nạp dữ liệu trực tiếp và nút dọn dẹp lịch sử.
  * **Tab 🔍 AI Compliance Checker**: Hỗ trợ bộ lọc động theo Domain hoặc theo Tên văn bản. Hiển thị thẻ xung đột quy định với màu sắc cảnh báo theo mức độ rủi ro (Severity) kèm nút xuất báo cáo chi tiết.
  * **Tab 📋 AI Audit Checklist Generator**: Chọn Phạm vi nghiệp vụ và Đơn vị kiểm toán để tự động sinh bảng checklist rủi ro. Có tính năng **popover** cho phép nhấp vào để tra cứu trích dẫn văn bản gốc trực quan.
  * **Tab 📜 Audit Log & System Trail**: Nhật ký audit toàn bộ hoạt động tra cứu của người dùng phân theo vai trò trong thời gian thực.
  * **Banner cảnh báo**: Banner khuyến cáo an toàn hiển thị nổi bật xác định AI đóng vai trò là trợ lý, quyết định cuối cùng cần có con người phê duyệt.

### Cách 2: Khởi chạy Server Dashboard HTML (Demo nhanh, giao diện cao cấp)
Kích hoạt nhanh bằng cách chạy tệp tin tiện ích `run_dashboard_localhost.bat` tại thư mục `buoi_17`:
```bash
run_dashboard_localhost.bat
```
Trình duyệt sẽ tự động mở trang Dashboard tại địa chỉ `http://localhost:8000/buoi_18_dashboard.html`. Đây là giao diện thiết kế chuyên nghiệp theo phong cách Dark Mode cao cấp, tích hợp biểu đồ trực quan hóa dữ liệu kiểm toán sẵn có từ kết quả thực thi các động cơ AI.

---

## 5. Các Giải Pháp Công Nghệ & Ranh Giới Kiểm Soát (Guardrails)

1. **RBAC Pre-Filtering & Secure Retrieval**: Hệ thống chặn truy cập trái phép dữ liệu ngay từ bước truy xuất ứng viên (Retrieval). Nhân viên cấp thấp (Staff) hoàn toàn bị chặn và không thể đưa các nội dung nhạy cảm của văn bản bị hạn chế (ví dụ: An toàn vốn rủi ro `agr_car02`) vào ngữ cảnh của mô hình ngôn ngữ lớn (LLM Context), ngăn ngừa rò rỉ thông tin tối đa.
2. **Citation Integrity & Anti-Hallucination**: Động cơ đối chiếu được thiết lập các ranh giới kiểm soát chặt chẽ. Nếu không tìm thấy bằng chứng mâu thuẫn rõ ràng, hệ thống sẽ trả về mã định danh `CHUA_DU_BANG_CHUNG` thay vì tự tạo hoặc đoán bừa thông tin. Mọi thông tin trích dẫn đều được đối chiếu ngược lại với tập dữ liệu gốc để đảm bảo sự tồn tại của Điều/Khoản.
3. **Human Review Guardrail**: Hệ thống áp dụng quy tắc mặc định gán cờ `NEEDS_HUMAN_REVIEW` cho toàn bộ kết quả phát hiện chênh lệch và danh sách checklist kiểm toán. Các kết luận từ AI được cấu trúc như các tài liệu gợi ý tham khảo, bảo đảm tính chịu trách nhiệm của Kiểm toán viên trong các quy trình nghiệp vụ thực tế.
4. **Audit Trail Privacy**: Hệ thống ghi log mọi hoạt động nghiệp vụ và bảo mật (kể cả các hoạt động bị từ chối truy cập `DENIED`). Mọi thông tin khóa cấu hình nhạy cảm như `key`, `password` hoặc `secret` đều tự động được phát hiện và thay thế bằng nhãn `[REDACTED]` để đảm bảo an toàn thông tin tuyệt đối.

---

## 6. Tiêu Chí Nghiệm Thu Đạt Được (Checklist)

Hệ thống đã hoàn tất và vượt qua toàn bộ các tiêu chí nghiệm thu chuyên sâu:

* [x] **Toàn vẹn dữ liệu gốc**: Giữ nguyên trạng tập CSV nguồn trong thư mục `data/`.
* [x] **Động cơ đối chiếu UC3**: Phát hiện chính xác các mâu thuẫn quy chế nội bộ và quy định NHNN kèm trích dẫn Điều/Khoản 2 phía.
* [x] **Phân cấp mức độ Severity**: Đánh giá đúng mức độ nghiêm trọng dựa trên rủi ro nghiệp vụ của ngân hàng.
* [x] **Động cơ sinh checklist UC4**: Tạo danh mục câu hỏi kiểm toán bám sát Domain & Unit được lựa chọn.
* [x] **Citation & Linking**: Tích hợp đường dẫn và mã trích dẫn cụ thể tới Điều/Khoản của văn bản gốc.
* [x] **Kiểm soát phân quyền RBAC**: Phân lọc chính xác tài liệu theo chức năng quyền hạn của từng tài khoản.
* [x] **Nhật ký Audit Trail**: Ghi nhận toàn vẹn các hành vi nghiệp vụ và bảo mật.
* [x] **Giao diện người dùng**: Streamlit App và HTML Dashboard hoạt động mượt mà, trực quan, thẩm mỹ cao.
* [x] **Human Review Guardrail**: Đóng dấu kiểm duyệt bắt buộc cho toàn bộ kết quả do AI xử lý.
* [x] **Báo cáo nghiệm thu**: Tệp nghiệm thu `final_validation_b18_report.md` đạt trạng thái **PASS**.

---

## 7. Nhận Định Tổng Kết Buổi 18

> *"Buổi 18 nâng cấp hệ thống AI từ tra cứu câu hỏi đơn lẻ sang công cụ Quản trị Tuân thủ (Compliance Governance) và Hỗ trợ Kiểm toán (Audit Assist) toàn diện. AI giúp kiểm toán viên tự động phát hiện các điểm nghẽn, mâu thuẫn trong hệ thống văn bản nội bộ và lập chương trình kiểm toán chuẩn hóa chỉ trong vài giây, đồng thời tuân thủ chặt chẽ các ranh giới bảo mật phân quyền thông tin của Ngân hàng."*
