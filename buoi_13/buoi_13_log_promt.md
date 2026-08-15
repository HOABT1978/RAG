# Nhật Ký Thực Hiện Prompts - Wiki Risk Graph (Buổi 13)

Tài liệu này ghi lại chi tiết nội dung các **Prompts yêu cầu** trong bài học và **Kết quả giải quyết** tương ứng từ AI Coding Agent.

---

## BƯỚC 1: KHẢO SÁT DỮ LIỆU GỐC (SEED CSVs)

### 1. Nội dung Prompt yêu cầu
> Kiểm tra toàn bộ project hiện tại, đặc biệt 4 file:
> *   `data/risk_profiles_seed.csv`
> *   `data/controls_seed.csv`
> *   `data/risk_events_seed.csv`
> *   `data/relationships_seed.csv`
>
> **Nhiệm vụ**:
> 1. Đọc 4 file CSV.
> 2. Báo cáo: số dòng từng file; tên cột; khóa chính; khóa tham chiếu; các loại relationship_type; số giá trị null; duplicate; khóa tham chiếu bị thiếu nếu có.
> 3. Giải thích dữ liệu này tạo những loại node và edge nào.
> 4. Chỉ rõ dữ liệu chưa có, không tự bịa.
> 5. Đề xuất kiến trúc MVP đơn giản cho: `KiemSoat -> RuiRo -> SuKienRuiRo`.
> 6. Tạo `scripts/inspect_data.py`. chạy script và báo cáo kết quả thực tế.

### 2. Kết quả giải quyết & Mã nguồn
*   **Tập lệnh**: [inspect_data.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/inspect_data.py)
*   **Phát hiện khoảng trống dữ liệu nguồn**: Cột `owner_unit_id` và `owner_role_id` là khóa ngoại logic nhưng chưa có dữ liệu master tương ứng. Rủi ro `RR-011` và `RR-012` chưa có biện pháp kiểm soát giảm thiểu nào.
*   **Thống kê thực tế**:
    *   `risk_profiles_seed.csv`: 12 dòng, PK: `id`, Nulls: 0, Duplicates: 0.
    *   `controls_seed.csv`: 10 dòng, PK: `id`, Nulls: 0, Duplicates: 0.
    *   `risk_events_seed.csv`: 12 dòng, PK: `id`, FK: `risk_id`, Nulls: 0, Duplicates: 0.
    *   `relationships_seed.csv`: 22 dòng, Composite PK, Nulls: 0, Duplicates: 0. Relationship types: `MITIGATES` (10), `OBSERVED_AS` (12).

---

## BƯỚC 2: CHUẨN HÓA DỮ LIỆU THÀNH NODE VÀ EDGE

### 1. Nội dung Prompt yêu cầu
> Biến 4 CSV nghiệp vụ thành hai bảng chuẩn: `outputs/entities.csv` và `outputs/relations.csv`.
>
> **Yêu cầu**:
> 1. Đọc 4 file CSV gốc.
> 2. Chuẩn hóa thành `outputs/entities.csv` với Schema tối thiểu: `id`, `type`, `name`, `description`, `source_file`, `data_origin`, `verification_status`.
> 3. Mapping:
>    *   `risk_profiles_seed.csv` -> type = `RuiRo`
>    *   `controls_seed.csv` -> type = `KiemSoat`
>    *   `risk_events_seed.csv` -> type = `SuKienRuiRo`
> 4. Giữ các thuộc tính nghiệp vụ cần thiết, không làm mất dữ liệu gốc.
> 5. Tạo `outputs/relations.csv` chứa các thuộc tính quan hệ gốc.
> 6. Kiểm tra `source_id` và `target_id` đều tồn tại trong `entities.csv`.
> 7. Không tự sinh thêm quan hệ, không tự đổi PROPOSED thành VERIFIED, không tự bịa thông tin đơn vị/vai trò.
> 8. Chạy script, in số lượng thực thể theo loại và quan hệ theo kiểu, báo cáo nếu có liên kết lỗi.

### 2. Kết quả giải quyết & Mã nguồn
*   **Tập lệnh**: [build_entities.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/build_entities.py)
*   **Bảng dữ liệu đầu ra**:
    *   [entities.csv](file:///d:/Rag_thuchanh/RAG/buoi_13/outputs/entities.csv): Ghi nhận 34 thực thể (12 `RuiRo`, 10 `KiemSoat`, 12 `SuKienRuiRo`).
    *   [relations.csv](file:///d:/Rag_thuchanh/RAG/buoi_13/outputs/relations.csv): Ghi nhận 22 quan hệ (10 `MITIGATES`, 12 `OBSERVED_AS`).
*   **Xác minh lỗi**: `0` lỗi orphan reference.

---

## BƯỚC 3: SINH WIKI MARKDOWN OBSIDIAN

### 1. Nội dung Prompt yêu cầu
> Tạo Wiki Markdown từ `entities.csv` và `relations.csv`.
>
> **Yêu cầu**:
> 1. Tạo thư mục `wiki/` chứa `risks/`, `controls/`, `events/` và `Home.md`.
> 2. Mỗi trang thực thể có YAML frontmatter tối thiểu (`id`, `type`, `verification_status`, `data_origin`).
> 3. Hiển thị đầy đủ thuộc tính nghiệp vụ cho từng loại thực thể.
> 4. Các liên kết dùng Obsidian wikilink `[[Tên thực thể]]`.
> 5. Mỗi liên kết được dựng từ quan hệ phải hiển thị rõ: `relationship_type`, `evidence_quote`, `verification_status`.
> 6. Tạo trang chủ `Home.md` chứa thống kê và danh mục các liên kết.
> 7. Báo cáo: số trang đã tạo; số wikilinks; ví dụ đường đi `KiemSoat -> RuiRo -> SuKienRuiRo`.

### 2. Kết quả giải quyết & Mã nguồn
*   **Tập lệnh**: [build_wiki.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/build_wiki.py)
*   **Kết quả sinh**:
    *   Tạo **35 trang Wiki** thành công.
    *   Tích hợp **78 wikilinks chéo**.
    *   *Ví dụ đường dẫn duyệt đồ thị*: `Đối soát tự động giao dịch và sổ cái (KS)` -[MITIGATES]-> `Giao dịch chuyển tiền bị hạch toán sai (RR)` -[OBSERVED_AS]-> `Sự kiện rủi ro SK-001 (SK)`.

---

## BƯỚC 4: KIỂM THỬ TỰ ĐỘNG CHẤT LƯỢNG WIKI

### 1. Nội dung Prompt yêu cầu
> Hãy kiểm thử Wiki Risk Graph vừa tạo.
>
> **Yêu cầu**:
> 1. Tạo `scripts/validate_wiki.py`.
> 2. Xuất báo cáo tại `outputs/wiki_validation_report.md`.
> 3. Kiểm tra tối thiểu: tổng số tệp markdown, tổng số wikilink, link hỏng, thực thể trùng ID, lệch khớp ID, rủi ro trống kiểm soát, rủi ro trống sự kiện, và trang mồ côi (orphan pages).
> 4. Phân biệt rõ lỗi còn lại nào là lỗi dữ liệu nguồn và lỗi nào do lập trình.

### 2. Kết quả giải quyết & Mã nguồn
*   **Tập lệnh**: [validate_wiki.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/validate_wiki.py)
*   **Báo cáo đầu ra**: [wiki_validation_report.md](file:///d:/Rag_thuchanh/RAG/buoi_13/outputs/wiki_validation_report.md)
    *   *Lỗi code*: `0` lỗi (không có link hỏng, không có trang mồ côi).
    *   *Lỗi dữ liệu*: `2` rủi ro trống biện pháp kiểm soát (`RR-011`, `RR-012`).

---

## BƯỚC 6: TÍCH HỢP CƠ SỞ DỮ LIỆU ĐỒ THỊ NEO4J

### 1. Nội dung Prompt yêu cầu
> Tích hợp Risk Graph vào Neo4j từ `entities.csv` và `relations.csv`.
>
> **Yêu cầu**:
> 1. Tạo `cypher/schema.cypher`, `cypher/demo_queries.cypher`, `scripts/load_neo4j.py`.
> 2. Cấu hình Node tối thiểu (`:RuiRo`, `:KiemSoat`, `:SuKienRuiRo`) và Edge (`MITIGATES`, `OBSERVED_AS`).
> 3. Dùng `id` làm khóa duy nhất và lệnh `MERGE` tránh trùng lặp.
> 4. Đọc kết nối từ `.env`. Không hard-code password.
> 5. Cung cấp hướng dẫn chạy nếu Neo4j Offline để tránh làm hỏng các bước Wiki.
> 6. Tạo các câu truy vấn Cypher phân tích đồ thị mẫu.

### 2. Kết quả giải quyết & Mã nguồn
*   **Tập lệnh**: [load_neo4j.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/load_neo4j.py) và [verify_neo4j.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/verify_neo4j.py)
*   **Ràng buộc & Query**: [schema.cypher](file:///d:/Rag_thuchanh/RAG/buoi_13/cypher/schema.cypher) và [demo_queries.cypher](file:///d:/Rag_thuchanh/RAG/buoi_13/cypher/demo_queries.cypher)
*   **Nhập dữ liệu thành công**: Đã nạp thành công 34 Nodes và 22 Edges vào đồ thị Neo4j.

---

## BƯỚC MỞ RỘNG: STREAMLIT DASHBOARD VÀ KHỞI CHẠY NHANH

### 1. Nội dung Prompt yêu cầu
> Tạo file chạy thực thi Streamlit chương trình từ thư mục buoi_13 hoàn chỉnh.

### 2. Kết quả giải quyết & Mã nguồn
*   **Trang web Dashboard**: [app.py](file:///d:/Rag_thuchanh/RAG/buoi_13/app.py) đặt trong `buoi_13/`.
*   **Launcher click đúp**: [run_app.bat](file:///d:/Rag_thuchanh/RAG/buoi_13/run_app.bat) đặt tại `buoi_13/run_app.bat`.
*   **Tính năng tích hợp**: Quản lý pipeline, xem chi tiết tài liệu Wiki, xem lưới dữ liệu chuẩn hóa, và thực thi trực tiếp các câu truy vấn Cypher lên Neo4j.
