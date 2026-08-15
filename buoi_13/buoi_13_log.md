# Nhật Ký Công Việc - Wiki Risk Graph (Buổi 13)

Tài liệu này ghi lại toàn bộ nhật ký thực hiện dự án, bao gồm các bước khảo sát dữ liệu, lập trình, kiểm thử và tích hợp cơ sở dữ liệu đồ thị.

---

## 1. Khảo sát dữ liệu gốc (CSV Seeds)
*   **Mã tập lệnh**: [inspect_data.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/inspect_data.py)
*   **Kết quả phân tích**:
    *   **risk_profiles_seed.csv**: 12 dòng, khóa chính `id` (RR-001 đến RR-012). Cột `owner_unit_id` là mã tham chiếu logic phòng ban chưa có bảng master dữ liệu.
    *   **controls_seed.csv**: 10 dòng, khóa chính `id` (KS-001 đến KS-010). Cột `owner_role_id` là mã tham chiếu logic chức danh chưa có bảng master dữ liệu.
    *   **risk_events_seed.csv**: 12 dòng, khóa chính `id` (SK-001 đến SK-012), khóa ngoại `risk_id` trỏ về `risk_profiles_seed.csv`.
    *   **relationships_seed.csv**: 22 dòng, chứa mối liên kết thực tế:
        *   `MITIGATES` (10 bản ghi): Trỏ từ `KiemSoat` -> `RuiRo`.
        *   `OBSERVED_AS` (12 bản ghi): Trỏ từ `RuiRo` -> `SuKienRuiRo`.
*   **Phát hiện nghiệp vụ quan trọng**:
    *   Rủi ro `RR-011` (Nhà cung cấp công nghệ không đáp ứng cam kết) và `RR-012` (Xung đột lợi ích trong mua sắm) **hoàn toàn chưa có biện pháp kiểm soát giảm thiểu nào** trong dữ liệu nguồn.

---

## 2. Chuẩn hóa thực thể và quan hệ (Normalization)
*   **Mã tập lệnh**: [build_entities.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/build_entities.py)
*   **Kết quả đầu ra**:
    *   [entities.csv](file:///d:/Rag_thuchanh/RAG/buoi_13/outputs/entities.csv): Ghi nhận 34 thực thể (12 `RuiRo`, 10 `KiemSoat`, 12 `SuKienRuiRo`). Bảo toàn thuộc tính mở rộng.
    *   [relations.csv](file:///d:/Rag_thuchanh/RAG/buoi_13/outputs/relations.csv): Ghi nhận 22 quan hệ (10 `MITIGATES`, 12 `OBSERVED_AS`).
    *   **Kiểm tra toàn vẹn**: Xác nhận `0` lỗi tham chiếu mồ côi (Orphan references). Tất cả source và target đều hợp lệ.

---

## 3. Sinh Obsidian Wiki Markdown
*   **Mã tập lệnh**: [build_wiki.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/build_wiki.py)
*   **Kết quả đầu ra**:
    *   Tạo thư mục `wiki/` chứa `risks/`, `controls/`, `events/` và cổng thông tin `Home.md`.
    *   Sinh **35 trang Wiki** thành công.
    *   Tích hợp **78 wikilinks chéo** dạng `[[Tên thực thể]]`.
    *   **Độ chi tiết liên kết (Quy tắc 10)**: Mỗi liên kết đi kèm đầy đủ thông tin: `relationship_type`, `evidence_quote`, và `verification_status` lấy từ `relations.csv`.

---

## 4. Kiểm thử chất lượng Wiki
*   **Mã tập lệnh**: [validate_wiki.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/validate_wiki.py)
*   **Kết quả đầu ra**: [wiki_validation_report.md](file:///d:/Rag_thuchanh/RAG/buoi_13/outputs/wiki_validation_report.md)
    *   **Broken Wikilinks**: `0` lỗi (Tất cả liên kết đều trỏ đúng tệp tin).
    *   **Orphan Pages**: `0` trang (Tất cả trang thực thể đều được liên kết chéo).
    *   **Unmitigated Risks**: Phát hiện chính xác `2` rủi ro trống kiểm soát giảm thiểu (`RR-011` và `RR-012`) do cấu trúc thiếu từ dữ liệu nguồn hạt giống.

---

## 5. Tích hợp Đồ thị Tri thức Neo4j
*   **Cấu hình kết nối**:
    *   Tập tin `.env` được tạo tại `buoi_13/.env` (và thư mục gốc) chứa thông tin kết nối mới:
        ```env
        NEO4J_URI=neo4j://127.0.0.1:7687
        NEO4J_USER=BUOI_13
        NEO4J_PASSWORD=12345678
        NEO4J_DATABASE=neo4j
        ```
*   **Khởi tạo tài khoản**: Đã khởi tạo thành công tài khoản `BUOI_13` mật khẩu `12345678` trên máy chủ Neo4j cục bộ.
*   **Import dữ liệu**: Chạy [load_neo4j.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/load_neo4j.py) nạp thành công **34 Nodes** và **22 Edges** vào đồ thị.
*   **Duyệt dữ liệu đồ thị thực tế**:
    *   Mã tập lệnh: [verify_neo4j.py](file:///d:/Rag_thuchanh/RAG/buoi_13/scripts/verify_neo4j.py)
    *   Xác nhận số lượng nút và cạnh trong Neo4j khớp chính xác 100% với tệp tin chuẩn hóa.
    *   Định nghĩa ràng buộc bảo vệ trong [schema.cypher](file:///d:/Rag_thuchanh/RAG/buoi_13/cypher/schema.cypher) và các câu truy vấn phân tích đồ thị mẫu trong [demo_queries.cypher](file:///d:/Rag_thuchanh/RAG/buoi_13/cypher/demo_queries.cypher).

---

## 6. Phát triển Giao diện Streamlit Dashboard
*   **Mã nguồn**: [app.py](file:///d:/Rag_thuchanh/RAG/buoi_13/app.py) và [run_app.bat](file:///d:/Rag_thuchanh/RAG/buoi_13/run_app.bat)
*   **Tính năng chính**:
    *   Điều khiển chạy toàn bộ pipeline các bước trực tiếp trên trình duyệt Web.
    *   Đọc và xem tài liệu Wiki Markdown động.
    *   Xem bảng dữ liệu chuẩn hóa dạng lưới.
    *   Thực thi trực tiếp các câu truy vấn Cypher và xem kết quả trả về từ database Neo4j.
*   **Kiểm tra khởi chạy**: Streamlit server đã được khởi động và kiểm thử chạy mượt mà tại `http://localhost:8501`.

---
*Ngày tạo nhật ký: 2026-08-15*
*Người thực hiện: AI Coding Agent (Antigravity)*
