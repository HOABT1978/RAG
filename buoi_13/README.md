# Wiki Risk Graph MVP - Tài Liệu Dự Án Đào Tạo

Dự án này xây dựng một Wiki Risk Graph từ dữ liệu hạt giống (seed data) phục vụ cho hoạt động đào tạo quản trị rủi ro doanh nghiệp. Học viên có thể quan sát mối tương quan đồ thị giữa **Biện pháp Kiểm soát (KiemSoat) -> Rủi ro (RuiRo) -> Sự kiện rủi ro (SuKienRuiRo)** bằng Obsidian Graph View hoặc cơ sở dữ liệu đồ thị Neo4j.

---

## 1. Cấu trúc thư mục dự án

```text
buoi_13/
├── data/                       # Dữ liệu nguồn (seed CSVs)
│   ├── risk_profiles_seed.csv  # Danh sách rủi ro
│   ├── controls_seed.csv       # Danh sách biện pháp kiểm soát
│   ├── risk_events_seed.csv    # Danh sách sự kiện rủi ro
│   └── relationships_seed.csv  # Mối quan hệ nguồn
├── scripts/                    # Tập lệnh thực thi chương trình
│   ├── inspect_data.py         # Kiểm tra tính toàn vẹn dữ liệu nguồn
│   ├── build_entities.py       # Chuẩn hóa dữ liệu sang dạng thực thể & quan hệ
│   ├── build_wiki.py           # Tạo các trang Wiki Markdown và liên kết chéo
│   ├── validate_wiki.py        # Kiểm thử lỗi liên kết và thống kê nghiệp vụ rủi ro
│   └── load_neo4j.py           # Nạp dữ liệu vào cơ sở dữ liệu Neo4j (Tùy chọn)
├── outputs/                    # Dữ liệu chuẩn hóa đầu ra & Báo cáo
│   ├── entities.csv            # Danh sách thực thể hợp nhất
│   ├── relations.csv           # Danh sách quan hệ hợp nhất
│   └── wiki_validation_report.md # Báo cáo kiểm thử chất lượng Wiki
├── wiki/                       # Thư mục chứa Obsidian Wiki Vault
│   ├── Home.md                 # Trang cổng thông tin bắt đầu
│   ├── risks/                  # Trang Wiki rủi ro (type: RuiRo)
│   ├── controls/               # Trang Wiki kiểm soát (type: KiemSoat)
│   └── events/                 # Trang Wiki sự kiện rủi ro (type: SuKienRuiRo)
└── cypher/                     # Script cho cơ sở dữ liệu Neo4j
    ├── schema.cypher           # Thiết lập ràng buộc cho đồ thị
    ├── ho_so_rui_ro_schema.cypher # Schema mở rộng
    └── demo_queries.cypher     # Các câu truy vấn mẫu (traversing, auditing)
```

---

## 2. Thứ tự các lệnh chạy dự án

Từ thư mục gốc dự án, hãy chạy các lệnh sau theo đúng thứ tự:

### Bước 1: Kiểm tra chất lượng dữ liệu nguồn
Đọc 4 file CSV gốc, đếm dòng, phân tích khóa chính/ngoại, kiểm tra giá trị null/duplicate và phát hiện các trường thiếu master data.
```bash
python buoi_13/scripts/inspect_data.py
```

### Bước 2: Chuẩn hóa dữ liệu thành Entities và Relations
Hợp nhất các thực thể thành `entities.csv` và quan hệ thành `relations.csv` tại thư mục `outputs/`, đảm bảo giữ nguyên thuộc tính nghiệp vụ.
```bash
python buoi_13/scripts/build_entities.py
```

### Bước 3: Sinh Wiki Markdown và Liên kết chéo
Tạo trang Wiki cho từng thực thể trong các thư mục tương ứng kèm liên kết chéo Obsidian `[[Wikilink]]` và tạo trang cổng `Home.md`.
```bash
python buoi_13/scripts/build_wiki.py
```

### Bước 4: Kiểm thử liên kết Wiki
Quét toàn bộ thư mục `wiki/` để kiểm tra liên kết hỏng, trang cô lập, ID không đồng bộ, và liệt kê các rủi ro chưa có kiểm soát.
```bash
python buoi_13/scripts/validate_wiki.py
```

### Bước 5: (Tùy chọn) Nạp dữ liệu vào Đồ thị Neo4j
Nếu bạn có cơ sở dữ liệu Neo4j, hãy cập nhật cấu hình kết nối vào file `.env` ở thư mục buoi_13 và chạy:
```bash
python buoi_13/scripts/load_neo4j.py
```

### Bước 6: Khởi chạy Streamlit Dashboard
Để chạy giao diện quản lý đồ thị trực quan, thực thi lệnh sau:
```bash
streamlit run buoi_13/app.py
```
Hoặc kích hoạt nhanh bằng cách click đúp tệp tin `buoi_13/run_app.bat`.

---


## 3. Cách mở Wiki bằng Obsidian

1. Tải và mở ứng dụng **Obsidian**.
2. Chọn **Open folder as vault** (Mở thư mục dưới dạng vault).
3. Chọn đường dẫn đến thư mục `buoi_13/wiki/`.
4. Mở tệp `Home.md` để bắt đầu duyệt qua các liên kết.
5. Nhấn tổ hợp phím `Ctrl + G` (hoặc nhấp biểu tượng **Graph view** ở thanh bên) để quan sát mô hình đồ thị rủi ro trực quan dưới dạng:
   ```text
   KiemSoat (Biện pháp kiểm soát)
       ↓ (MITIGATES)
   RuiRo (Rủi ro)
       ↓ (OBSERVED_AS)
   SuKienRuiRo (Sự kiện rủi ro)
   ```

---

## 4. Các câu truy vấn mẫu trên Neo4j (Cypher)

Các câu truy vấn Cypher đã được cung cấp sẵn trong [demo_queries.cypher](file:///d:/Rag_thuchanh/RAG/buoi_13/cypher/demo_queries.cypher) bao gồm:
*   Xem toàn bộ đồ thị: `MATCH (n) RETURN n`
*   Tìm kiểm soát giảm thiểu rủi ro xác định: `MATCH (c:KiemSoat)-[r:MITIGATES]->(risk:RuiRo {id: 'RR-001'}) RETURN c, r, risk`
*   Tìm sự kiện của một rủi ro: `MATCH (risk:RuiRo {id: 'RR-001'})-[:OBSERVED_AS]->(e:SuKienRuiRo) RETURN risk, e`
*   Tra vết đường truyền đầy đủ: `MATCH path = (c:KiemSoat)-[:MITIGATES]->(risk:RuiRo)-[:OBSERVED_AS]->(e:SuKienRuiRo) RETURN path`
*   Tìm rủi ro thiếu kiểm soát: `MATCH (risk:RuiRo) WHERE NOT (:KiemSoat)-[:MITIGATES]->(risk) RETURN risk`
*   Kiểm toán liên kết chưa được xác thực: `MATCH ()-[r]->() WHERE r.verification_status <> 'VERIFIED' RETURN r`
