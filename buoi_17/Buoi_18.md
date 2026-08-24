# BÀI THỰC HÀNH BUỔI 18
# AI Compliance Checker và AI Audit Checklist Generator bằng Vibe Coding

## Mục tiêu

Buổi 18 tập trung vào việc áp dụng AI/RAG nâng cao kết hợp với Metadata và Secure Retrieval để giải quyết hai bài toán quản trị & kiểm toán quy định chuyên sâu trong Ngân hàng (Agribank):

```text
UC3: AI Compliance Checker   → So sánh chéo văn bản nội bộ, phát hiện xung đột/mâu thuẫn, chỉ rõ Điều/Khoản & Severity
UC4: AI Audit Checklist Gen  → Nhập phạm vi kiểm toán (domain, unit), AI sinh bản nháp checklist rủi ro có link/citation gốc
```

Sản phẩm cuối buổi:

```text
Hệ thống AI Compliance & Audit bao gồm:
+ Module AI Compliance Checker (Cross-policy Conflict Detection)
+ Module AI Audit Checklist Generator (Domain & Unit Scoped)
+ Trích dẫn chính xác Điều/Khoản văn bản gốc (Citations & Direct Links)
+ Giao diện Web tương tác bằng Streamlit cho cả 2 use case
+ Audit Trail & RBAC Integration
```

---

# 1. Hai use case chính

## Use Case 3 — AI Compliance Checker (Kiểm tra tuân thủ & So sánh chéo)

```text
Tập văn bản nội bộ Agribank
→ Chọn văn bản / chủ đề cần đối chiếu
→ Cross-Comparison & Hybrid Retrieval
→ Phát hiện xung đột, chồng chéo, mâu thuẫn
→ Xuất danh sách Conflict (Văn bản A - Điều X vs Văn bản B - Điều Y)
→ Phân loại Severity (HIGH / MEDIUM / LOW)
→ Human Review & Verification
```

**Điểm quan trọng:**
> AI phải trích dẫn chính xác Điều, Khoản, Số ký hiệu của cả 2 phía văn bản mâu thuẫn và gán mức độ nghiêm trọng dựa trên rủi ro nghiệp vụ.

---

## Use Case 4 — AI Audit Checklist Generator (Tạo Checklist Kiểm toán)

```text
Nhập Phạm vi Kiểm toán (Domain, Unit)
→ Filter Quy định & Rủi ro áp dụng theo phạm vi
→ Hybrid Search + Metadata Filtering
→ AI sinh bản nháp Checklist Kiểm toán theo rủi ro
→ Gắn Link/Citation trực tiếp tới Điều/Khoản gốc
→ Export Checklist (CSV / Markdown)
→ Human Review & Final Approval
```

**Điểm quan trọng:**
> Checklist sinh ra phải bám sát phạm vi kiểm toán được chọn, liệt kê rõ câu hỏi kiểm tra, rủi ro tương ứng và trích dẫn văn bản quy định gốc để kiểm toán viên dễ tra cứu.

---

# 2. Nguyên tắc bắt buộc

- **Không sửa dữ liệu nguồn:** Giữ nguyên các tệp `agribank_internal_policies.csv` và `chunks_combined_secure.csv`.
- **Trích dẫn chính xác:** Mọi mâu thuẫn hay đầu mục checklist đều phải gắn `citation` (Số ký hiệu, Điều, Khoản, document_id).
- **Phân quyền RBAC:** Chỉ truy xuất và hiển thị quy định thuộc phạm vi được phép của `user_role`.
- **Không tự bịa xung đột / rủi ro:** Nếu chưa đủ bằng chứng chứng minh xung đột, hệ thống trả về `CHUA_DU_BANG_CHUNG`.
- **Bắt buộc Human Review:** Mọi kết quả do AI sinh ra phải gắn cờ `NEEDS_HUMAN_REVIEW`, không dùng làm kết luận kiểm toán cuối cùng nếu chưa có xác nhận của Kiểm toán viên.

---

# 3. Cấu trúc project đề xuất

```text
buoi_17/ (hoặc buoi_18/)
├── .env
├── README.md
├── data/
│   ├── agribank_internal_policies.csv
│   └── chunks_combined_secure.csv
├── config/
│   └── rbac_policy.json
├── scripts/
│   ├── compliance_checker.py        # UC3: AI Compliance Checker Engine
│   ├── audit_checklist_gen.py       # UC4: AI Audit Checklist Generator Engine
│   ├── secure_retrieval_adapter.py
│   ├── audit_logger.py
│   └── final_validation_b18.py
├── outputs/
│   ├── compliance_conflicts.csv     # Bảng kết quả mâu thuẫn UC3
│   ├── compliance_conflict_report.md
│   ├── audit_checklist_results.csv  # Bảng checklist kiểm toán UC4
│   ├── audit_checklist_report.md
│   └── final_validation_b18_report.md
└── app.py                           # Web UI Streamlit tích hợp UC3 & UC4
```

---

# 4. `.env`

Đặt tại:

```text
.env
```

Cấu hình mẫu:

```env
SOURCE_AGRIBANK_INTERNAL_CSV=data/agribank_internal_policies.csv
SOURCE_COMBINED_SECURE_CSV=data/chunks_combined_secure.csv

GEMINI_API_KEY=YOUR_GEMINI_API_KEY_FREE
LLM_API_KEY=YOUR_GEMINI_API_KEY_FREE
LLM_MODEL=gemini-2.5-flash

APP_ENV=training
```

---

# 5. Cách làm Vibe Coding & Các Prompt Thực Hành

```text
Prompt
→ Agent đọc dữ liệu & mã nguồn hiện có
→ Thực hiện từng bước nhỏ độc lập
→ Chạy thử & kiểm tra output
→ PASS mới chuyển sang bước tiếp theo
```

---

# PROMPT SETUP — Kiểm tra môi trường & Dữ liệu Buổi 18

```text
Kiểm tra giúp tôi môi trường và dữ liệu cho Buổi 18.

Dữ liệu đầu vào chính:
1. data/agribank_internal_policies.csv
2. data/chunks_combined_secure.csv

Kiểm tra:
- Python và virtual environment;
- Đọc file agribank_internal_policies.csv và kiểm tra 14 cột metadata (so_ky_hieu, article, title, allowed_roles...);
- Đọc file chunks_combined_secure.csv và xác nhận số văn bản pháp lý / nội bộ;
- Đảm bảo các thư mục scripts/, outputs/ đã sẵn sàng;
- File .env đã có GEMINI_API_KEY / LLM_API_KEY hợp lệ chưa.

Báo kết quả:
ENVIRONMENT READY: YES / NO
INTERNAL DATA READY: YES / NO
COMBINED DATA READY: YES / NO
```

---

# PROMPT 1 — cataloging & Chuẩn bị dữ liệu cho UC3 & UC4

```text
Thực hiện Cataloging dữ liệu cho Buổi 18.

Dùng 2 tệp:
data/agribank_internal_policies.csv
data/chunks_combined_secure.csv

Yêu cầu:
1. Thống kê tất cả các văn bản nội bộ Agribank (Title, Số ký hiệu, Loại văn bản, Cơ quan ban hành).
2. Phân loại các văn bản theo Domain/Miền nghiệp vụ (vd: An toàn kho quỹ, CAR & Rủi ro, Tín dụng, Ngoại tệ, Bảo hiểm, CNTT & AI, Nhân sự, Tài chính mua sắm, Xử lý nợ).
3. Kiểm tra tính đầy đủ của trường Điều/Khoản (`article`), `citation`, và `allowed_roles`.

Tạo file báo cáo:
outputs/b18_data_catalog.md

Cuối file báo:
DATA CATALOGING: PASS / FAIL
DOMAINS DETECTED: [Số lượng domain]
READY FOR UC3 & UC4: YES / NO
```

---

# PROMPT 2 — Xây dựng Engine UC3: AI Compliance Checker

```text
Xây dựng Core Engine cho UC3 — AI Compliance Checker.

Tạo file:
scripts/compliance_checker.py

Chức năng chính:
1. Cho phép chọn hoặc tự động quét các cặp văn bản nội bộ Agribank cùng domain (hoặc giữa quy định nội bộ vs Thông tư NHNN).
2. Thực hiện so sánh chéo (Cross-Comparison) bằng cách truy xuất các Điều/Khoản liên quan qua BM25/Hybrid Search.
3. Gửi Evidence Package gồm Điều khoản A và Điều khoản B sang LLM để phân tích:
   - Có mâu thuẫn/chồng chéo/xung đột không?
   - Loại xung đột: Hạn mức/ngưỡng, Quy trình thực hiện, Thẩm quyền phê duyệt, hoặc Thời hạn xử lý.
   - Trích dẫn cụ thể: Citation A (`so_ky_hieu_A` - `article_A`) vs Citation B (`so_ky_hieu_B` - `article_B`).
   - Đánh giá Severity: HIGH (ảnh hưởng pháp lý/rủi ro tài chính lớn), MEDIUM (rủi ro vận hành), LOW (chồng chéo thủ tục).
   - review_status = "NEEDS_HUMAN_REVIEW".
4. Nếu không phát hiện mâu thuẫn rõ ràng, trả về classification = "KHONG_XUNG_DOT" hoặc "CHUA_DU_BANG_CHUNG".

Đảm bảo:
- Bắt buộc dùng citation thật từ dataset, không tự bịa điều khoản.
- Tích hợp AuditLogger để ghi nhận vết kiểm tra.

Chạy test thử nghiệm với 3 cặp quy định (Kho quỹ, CAR, Tín dụng).

Xuất kết quả ra:
outputs/compliance_conflicts.csv
outputs/compliance_conflict_report.md

Cuối report:
COMPLIANCE CHECKER ENGINE: PASS / FAIL
CONFLICTS DETECTED: [Số lượng]
HUMAN REVIEW GUARDRAIL: PASS
```

**Schema bảng output UC3 (`compliance_conflicts.csv`):**

```text
conflict_id
domain
doc_a_id
doc_a_citation
doc_a_text
doc_b_id
doc_b_citation
doc_b_text
conflict_type
description
severity
review_status
request_id
```

---

# PROMPT 3 — Xây dựng Engine UC4: AI Audit Checklist Generator

```text
Xây dựng Core Engine cho UC4 — AI Audit Checklist Generator.

Tạo file:
scripts/audit_checklist_gen.py

Chức năng chính:
1. Input: 
   - `domain`: Miền kiểm toán (vd: "An toàn Kho quỹ & Vận chuyển", "Phán quyết Tín dụng", "Bảo mật CNTT & AI", "Quản lý CAR", v.v.)
   - `unit`: Đơn vị được kiểm toán (vd: "Chi nhánh loại I", "Phòng Giao dịch", "Khối CNTT", "Phòng Kế toán", v.v.)
   - `user_role`: Vai trò người dùng (để lọc RBAC).

2. Quy trình xử lý:
   - Truy xuất các chunk quy định nội bộ và văn bản NHNN liên quan đến `domain` và `unit` trong phạm vi RBAC.
   - LLM trích xuất các nghĩa vụ tuân thủ, quy trình bắt buộc, rủi ro chính và câu hỏi kiểm tra (Checklist Items).
   - Gán mức độ rủi ro (Risk Level: High / Medium / Low) cho từng mục kiểm tra.
   - Đóng gói link/citation trực tiếp tới Điều/Khoản văn bản gốc.

3. Output Schema cho từng đầu mục Checklist:
   - `item_id`: Mã mục kiểm tra (vd: `CHK_KHO_01`)
   - `domain`: Miền nghiệp vụ
   - `unit_scope`: Phạm vi áp dụng
   - `audit_question`: Câu hỏi kiểm toán (vd: "Chi nhánh có bố trí xe ô tô bọc thép chuyên dùng khi vận chuyển tiền mặt từ 3 tỷ đồng trở lên không?")
   - `risk_description`: Rủi ro tiềm ẩn (vd: "Thất thoát tiền mặt, rủi ro an ninh trên đường vận chuyển")
   - `risk_level`: HIGH / MEDIUM / LOW
   - `source_citation`: Citation văn bản gốc kèm Điều/Khoản
   - `review_status`: "NEEDS_HUMAN_REVIEW"

4. Tích hợp AuditLogger để ghi lại thao tác tạo checklist.

Chạy thử nghiệm tạo checklist cho 2 domain: "An toàn Kho quỹ" và "Bảo mật CNTT & AI".

Xuất kết quả ra:
outputs/audit_checklist_results.csv
outputs/audit_checklist_report.md

Cuối report:
CHECKLIST GENERATOR ENGINE: PASS / FAIL
CHECKLIST ITEMS CREATED: [Số lượng]
CITATIONS ATTACHED: YES
```

---

# PROMPT 4 — Xây dựng Giao diện Streamlit UI cho UC3 & UC4

```text
Cập nhật/Xây dựng giao diện Streamlit trong file:
app.py

Yêu cầu Giao diện Web:
1. Sidebar:
   - Chọn User ID & User Role (Admin, Risk_Manager, KiemToanVien, Staff).
   - Trạng thái kết nối dữ liệu (Internal Policies & External Legal Docs).
   - Nút Reset Session / Clean Audit Log.

2. Tab 1: 🔍 UC3 — AI Compliance Checker (Kiểm tra xung đột quy định)
   - Bộ lọc chọn Domain hoặc Chọn 2 Văn bản nội bộ cần so sánh.
   - Nút "Phát hiện Xung đột & Mâu thuẫn".
   - Hiển thị danh sách Conflicts dưới dạng Card/Table đẹp mắt:
     + Mã conflict & Severity Badge (HIGH = Đỏ, MEDIUM = Vàng, LOW = Xanh).
     + Trích dẫn Điều/Khoản 2 phía (`doc_a_citation` vs `doc_b_citation`).
     + Mô tả mâu thuẫn chi tiết & Loại xung đột.
     + Nhãn cờ `NEEDS_HUMAN_REVIEW`.
   - Cho phép xuất file Báo cáo Conflict (CSV / Markdown).

3. Tab 2: 📋 UC4 — AI Audit Checklist Generator (Tạo Checklist Kiểm toán)
   - Ô chọn Phạm vi Kiểm toán: Dropdown `Domain` và Dropdown `Unit`.
   - Nút "Tạo Bản Nháp Checklist Kiểm Toán".
   - Hiển thị Bảng Checklist Kiểm toán tương tác:
     + STT, Câu hỏi kiểm toán, Rủi ro liên quan, Mức rủi ro (High/Med/Low).
     + Cột "Văn bản gốc / Citation" có thể click mở popup xem chi tiết trích dẫn Điều/Khoản.
     + Nút Tải xuống Checklist (CSV / JSON).

4. Tab 3: 📜 Audit Log & System Trail
   - Xem toàn bộ lịch sử request tra cứu, check conflict và gen checklist.
   - Lọc theo Role và Action.

5. Banner & Warning:
   - Đặt banner khuyến cáo: "Demo sản phẩm AI Kiểm toán — Kết quả gợi ý cần Kiểm toán viên xác minh trước khi ban hành."

Chạy ứng dụng:
streamlit run app.py
```

---

# PROMPT 5 — Security & Guardrail Testing cho Buổi 18

```text
Đóng vai Security & Compliance Tester để kiểm thử ứng dụng Buổi 18.

Tạo file:
scripts/security_tests_b18.py

Thực hiện 7 bài test:
1. RBAC Test: Role 'Staff' không truy cập được quy định bảo mật riêng của 'Risk_Manager' hay 'Admin'.
2. Citation Integrity: Mọi conflict (UC3) và checklist item (UC4) bắt buộc phải có `citation` hợp lệ (không rỗng).
3. Hallucination Check: Kiểm tra AI có tự bịa ra Điều/Khoản không tồn tại trong dataset không.
4. Human Review Guardrail: Mọi kết quả xuất ra đều có `review_status = NEEDS_HUMAN_REVIEW`.
5. Audit Log Privacy: Audit log không lưu trữ secret, API key hay thông tin nhạy cảm.
6. Unknown Domain Test: Nhập domain không có trong data -> Hệ thống báo thông báo rõ ràng "Chưa có dữ liệu quy định", không tự bịa.
7. File Export Verification: Kiểm tra file CSV xuất ra có đúng schema và mở được không.

Xuất báo cáo:
outputs/security_test_b18_report.md

Cuối file báo:
SECURITY & GUARDRAIL TESTS: PASS / FAIL
```

---

# PROMPT 6 — Audit Toàn bộ Project & Final Validation

```text
Audit toàn bộ project Buổi 18 và tạo báo cáo nghiệm thu cuối cùng.

Tạo file:
outputs/final_validation_b18_report.md

Kiểm tra và xác nhận các tiêu chí:
1. Source Data Integrity: Giữ nguyên tệp gốc, đọc read-only.
2. UC3 AI Compliance Checker: So sánh chéo được quy định nội bộ, phát hiện mâu thuẫn kèm Điều/Khoản và Severity.
3. UC4 AI Audit Checklist Generator: Sinh checklist kiểm toán bám sát Domain & Unit, trích dẫn chuẩn xác văn bản gốc.
4. Citation & Linking: Trích dẫn đầy đủ Số ký hiệu, Điều, Khoản.
5. RBAC & Governance: Lọc quyền trước retrieval/context, không lộ dữ liệu cấm.
6. Streamlit Web Interface: Giao diện trực quan, hoạt động mượt mà cho cả 2 use case.
7. Human Review Guardrail: Mọi finding đều yêu cầu Human Review.

Đánh giá tổng thể ở cuối file:
UC3 COMPLIANCE CHECKER: PASS / FAIL
UC4 AUDIT CHECKLIST GEN: PASS / FAIL
CITATION INTEGRITY: PASS / FAIL
RBAC & GOVERNANCE: PASS / FAIL
STREAMLIT DEMO: PASS / FAIL

SYSTEM READY FOR DEMO: YES / NO
```

---

# 6. Trình tự Demo cuối buổi

1. **Trình bày UC3 (AI Compliance Checker):**
   - Chọn miền "An toàn Kho quỹ" hoặc "Quản lý CAR".
   - Bấm nút kiểm tra tuân thủ -> AI chỉ ra điểm mâu thuẫn giữa Quy định 100/QĐ-NHNO-AT và Quy định 180/QĐ-NHNO-BH về hạn mức tiền mặt bọc thép.
   - Chỉ rõ trích dẫn Điều 12 (QĐ 100) vs Điều 5 (QĐ 180) kèm mức Severity: HIGH.

2. **Trình bày UC4 (AI Audit Checklist Generator):**
   - Nhập Domain = "Bảo mật CNTT & AI", Unit = "Khối CNTT".
   - AI lập bảng checklist gồm: Kiểm tra mã hóa AES-128 dữ liệu RAG AI, thời gian lưu audit log 12 tháng, phân quyền RBAC.
   - Gắn citation trực tiếp đến Quy chế 600/QC-NHNO-CNTT Điều 9 & Điều 16.

3. **Trình bày Audit Log & Guardrail:**
   - Mở Tab Audit Log xem nhật ký truy vết hệ thống.
   - Nhấn mạnh nhãn `NEEDS_HUMAN_REVIEW` — khẳng định AI đóng vai trò trợ lý trợ lực cho Kiểm toán viên, không thay thế con người.

---

# 7. Những điều Agent tuyệt đối không được làm

```text
- Sửa đổi tệp dữ liệu nguồn trong data/;
- Bịa đặt ra các số hiệu văn bản, Điều/Khoản không có trong tập dữ liệu;
- Bỏ qua bước kiểm tra RBAC (để lộ tài liệu cấm ra UI hoặc context LLM);
- Khẳng định kết luận kiểm toán của AI là quyết định cuối cùng mà không cần Human Review;
- Hard-code API Key hoặc ghi secret vào file log/report;
- Tự động thay đổi logic phân loại mâu thuẫn mà không có bằng chứng văn bản.
```

---

# 8. Tiêu chí nghiệm thu (Checklist)

```text
☐ Không sửa dữ liệu nguồn gốc.
☐ UC3 phát hiện mâu thuẫn quy định nội bộ có trích dẫn Điều/Khoản 2 phía.
☐ UC3 đánh giá đúng Severity (HIGH / MEDIUM / LOW).
☐ UC4 tạo checklist kiểm toán bám sát Domain & Unit.
☐ UC4 gắn link/citation trực tiếp tới văn bản quy định gốc.
☐ Mọi kết quả sinh ra đều gắn nhãn NEEDS_HUMAN_REVIEW.
☐ RBAC kiểm soát quyền truy cập chính xác.
☐ Audit Trail ghi lại đầy đủ thao tác và truy vết.
☐ Giao diện Streamlit chạy ổn định với 2 use case.
☐ Báo cáo nghiệm thu final_validation_b18_report.md đạt PASS.
```

---

# 9. Câu chốt Buổi 18

> “Buổi 18 nâng cấp hệ thống AI từ tra cứu câu hỏi đơn lẻ sang công cụ Quản trị Tuân thủ (Compliance Governance) và Hỗ trợ Kiểm toán (Audit Assist) toàn diện. AI giúp kiểm toán viên tự động phát hiện các điểm nghẽn, mâu thuẫn trong hệ thống văn bản nội bộ và lập chương trình kiểm toán chuẩn hóa chỉ trong vài giây.”
