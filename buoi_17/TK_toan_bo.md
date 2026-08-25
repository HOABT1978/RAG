# TỔNG HỢP TOÀN BỘ CÁC BÀI HỌC, PROMPT VÀ DỮ LIỆU TEST (BUỔI 10 - BUỔI 18)

Tài liệu này tổng hợp chi tiết mục tiêu, yêu cầu prompt hệ thống và dữ liệu thử nghiệm (test data) của toàn bộ các buổi học từ khóa học RAG & Graph RAG nâng cao.

---

## 1. BUỔI 10: Phân Tách Dữ Liệu (Chunking), Tạo Vector Nhúng (Embeddings) và Nạp Neo4j

### 1.1. Mục tiêu & Nội dung học
*   Làm sạch nội dung HTML từ các tệp dữ liệu pháp luật gốc nhưng vẫn bảo toàn cấu trúc văn bản (chương, mục, điều, khoản).
*   Phân tách văn bản thành các phân đoạn (chunks) có cấu trúc phân cấp Cha-Con (Hierarchical Parent-Child: Document -> Chapter -> Clause -> Paragraph).
*   Tạo vector nhúng dày đặc (Dense Embeddings) bằng mô hình tiếng Việt chuyên dụng trên CPU: `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5`.
*   Thiết kế Schema và nạp dữ liệu đồ thị văn bản vào Neo4j cục bộ.

### 1.2. Dữ liệu thử nghiệm (Test Data)
*   **Đầu vào**: Tập hợp 15 văn bản quy phạm pháp luật dưới dạng HTML.
*   **Schema Neo4j**:
    *   Các nhãn nút: `(:Document)`, `(:Chunk)`.
    *   Các quan hệ: `[:PART_OF]`, `[:PARENT_OF]`, `[:NEXT]` (luồng tuần tự), và quan hệ liên tài liệu: `[:CAN_CU]`, `[:THAY_THE]`, `[:HOP_NHAT]`.

### 1.3. Prompt hệ thống & Kịch bản xử lý
*   **Prompt Chunking**: Làm sạch các thẻ HTML thừa, giữ lại thẻ tiêu đề `<h1>` đến `<h4>` và thẻ bảng biểu `<table>`. Trích xuất các thuộc tính: Số hiệu văn bản, Tiêu đề chương/mục, Số thứ tự Điều/Khoản.
*   **Cypher Query nạp dữ liệu**:
    ```cypher
    MERGE (d:Document {id: $doc_id}) ON CREATE SET d.title = $title
    MERGE (c:Chunk {id: $chunk_id}) ON CREATE SET c.text = $text, c.embedding = $embedding
    MERGE (c)-[:PART_OF]->(d)
    ```

---

## 2. BUỔI 11: Tìm Kiếm Đồ Thị RAG Đa Bước (Multi-hop Graph RAG) và Ứng Dụng QA

### 2.1. Mục tiêu & Nội dung học
*   Xây dựng hệ thống Graph RAG bằng cách truy vấn các phân đoạn văn bản và các mối quan hệ được lưu trữ trong cơ sở dữ liệu Neo4j `kb-hops` từ Bài thực hành 1.
*   Thực hiện tìm kiếm đa bước (multi-hop) giữa các văn bản liên quan (duyệt theo các liên kết `CAN_CU`, `THAY_THE`, `HOP_NHAT`).
*   Tích hợp ngữ cảnh đa bước và tạo câu trả lời tự động bằng Gemini API (`gemini-flash-latest`).

### 2.2. Dữ liệu thử nghiệm (Test Data)
*   Bộ dữ liệu đồ thị Neo4j từ 15 văn bản của Buổi 10.
*   **5 câu hỏi kiểm thử phức tạp**:
    1.  Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?
    2.  Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?
    3.  Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?
    4.  Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?
    5.  Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?

### 2.3. Prompt hệ thống & Kịch bản xử lý
*   **Prompt LLM Generator**:
    ```text
    Bạn là trợ lý pháp lý chuyên nghiệp của ngân hàng. Hãy trả lời câu hỏi dựa trên các phân đoạn ngữ cảnh đồ thị đa bước dưới đây.
    Yêu cầu:
    - Nếu thông tin không có trong ngữ cảnh, hãy trả lời "Không tìm thấy thông tin trong tài liệu cung cấp", không tự bịa ra câu trả lời.
    - Cung cấp dẫn chứng rõ ràng từ Điều khoản và Số hiệu văn bản nào được trích xuất từ đồ thị.
    ```

---

## 3. BUỔI 12: Chuẩn Hóa, Làm Giàu Metadata và Xây Dựng Đồ Thị Tri Thức

### 3.1. Mục tiêu & Nội dung học
*   Thực hiện trích xuất thực thể (Entity Extraction/NER) và xây dựng đồ thị tri thức từ tập 30 văn bản pháp luật lớn.
*   Kết hợp các bộ quy tắc (rule-based) và gọi mô hình ngôn ngữ lớn (Gemini API) để làm giàu Metadata.
*   Thực hiện chuẩn hóa thực thể (Entity Normalization) để tránh trùng lặp nút và phân tích trích xuất các mối quan hệ ngữ nghĩa.

### 3.2. Dữ liệu thử nghiệm (Test Data)
*   **Đầu vào**:
    *   `ner_kb/metadata.csv`: Chứa danh mục và mã định danh 30 văn bản.
    *   `ner_kb/content.csv`: Chứa nội dung HTML thô của 30 văn bản.

### 3.3. Prompt hệ thống & Kịch bản xử lý
*   **Prompt NER & Entity Rich Schema (Gemini)**:
    ```json
    {
      "system_instruction": "Phân tích nội dung đoạn điều khoản pháp luật ngân hàng và trích xuất danh sách các Thực thể (Cơ quan ban hành, Vai trò kiểm toán, Hành vi vi phạm, Tài sản bảo đảm) và các Mối quan hệ tương ứng.",
      "response_mime_type": "application/json"
    }
    ```

---

## 4. BUỔI 13: Xây Dựng Wiki Risk Graph Bằng Vibe Coding

### 4.1. Mục tiêu & Nội dung học
*   Xây dựng một **Wiki tri thức rủi ro dạng đồ thị** (Wiki Risk Graph) từ dữ liệu rủi ro mô phỏng.
*   Cho phép người dùng tra cứu hồ sơ rủi ro, xem các kiểm soát tương ứng giúp giảm thiểu rủi ro, xem các sự kiện rủi ro thực tế xảy ra.
*   Sinh ra các trang Markdown liên kết chéo tương thích hoàn toàn với chế độ Graph View của Obsidian và xuất dữ liệu node/edge nạp vào Neo4j.

### 4.2. Dữ liệu thử nghiệm (Test Data)
*   `data/risk_profiles_seed.csv`: Hồ sơ rủi ro (Nguyên nhân -> Sự kiện -> Hậu quả).
*   `data/controls_seed.csv`: Các hoạt động kiểm soát rủi ro của ngân hàng.
*   `data/risk_events_seed.csv`: Nhật ký ghi nhận các sự kiện rủi ro thực tế phát sinh.
*   `data/relationships_seed.csv`: Danh sách quan hệ liên kết và trạng thái xác minh (verification_status).

### 4.3. Prompt hệ thống & Kịch bản xử lý
*   **Prompt Tạo Wiki Markdown**:
    ```text
    Tạo các file Markdown tương ứng với từng hồ sơ rủi ro và hoạt động kiểm soát.
    Quy tắc liên kết: Sử dụng cấu trúc liên kết nội bộ wikilink [[Tên_file]] của Obsidian.
    Ví dụ: Trong file [[RR-001.md]] phải có phần kiểm soát liên quan liên kết tới [[KS-001.md]].
    ```

---

## 5. BUỔI 14: Nâng Cấp RAG Với Hybrid Search + Reranking và Xây Dựng Đồ Thị Mini

### 5.1. Mục tiêu & Nội dung học
*   Nâng cấp đường ống truy xuất RAG cơ bản lên kiến trúc Hybrid Search (kết hợp BM25 Lexical Search và Dense Vector Retrieval thông qua cơ chế xếp hạng dung hợp Reciprocal Rank Fusion - RRF).
*   Tích hợp mô hình xếp hạng lại (Cross-Encoder Neural Reranker: `BAAI/bge-reranker-v2-m3`) để tìm ra top-k ngữ cảnh tối ưu nhất.
*   Xây dựng một đồ thị tri thức nhỏ liên kết các tài liệu và điều khoản.

### 5.2. Dữ liệu thử nghiệm (Test Data)
*   Các tệp dữ liệu thô: `metadata.csv`, `content.csv` và tệp quan hệ giữa các điều khoản `relationships.csv`.

### 5.3. Prompt hệ thống & Kịch bản xử lý
*   **Prompt sinh câu hỏi kiểm thử (Benchmark Generator)**:
    ```text
    Đóng vai trò là chuyên gia kiểm toán ngân hàng. Hãy tạo ra các câu hỏi và câu trả lời chuẩn xác (Ground Truth) dựa vào đoạn quy định nội bộ dưới đây. Câu hỏi phải bao hàm đầy đủ chi tiết mã hiệu văn bản và điều khoản trích dẫn.
    ```

---

## 6. BUỔI 15: Cài Đặt Kiểm Soát Truy Cập RBAC Ở Mức Dữ Liệu và Retrieval Pipeline

### 6.1. Mục tiêu & Nội dung học
*   Thiết kế hệ thống kiểm soát truy cập dựa trên vai trò (RBAC) ở mức thuộc tính dữ liệu (Property-based Security) tích hợp trực tiếp vào đường ống truy xuất.
*   Phân loại tài liệu thành các cấp độ bảo mật và gắn thẻ tag vai trò được phép truy cập (`allowed_roles`).
*   Tải thuộc tính RBAC lên đồ thị Neo4j và nâng cấp bộ lọc an toàn BM25 & Dense Vector trong Python nhằm loại bỏ hoàn toàn các tài liệu cấm xem trước khi chuyển qua bước Rerank và LLM.

### 6.2. Dữ liệu thử nghiệm (Test Data)
*   `chunks_normalized.csv` và tệp đầu ra đã gắn quyền `chunks_secure.csv`.
*   **Cấu hình phân quyền**: Tối thiểu 3 vai trò: `Admin`, `Risk_Manager`, `Staff`, `Guest`.
    *   Tài liệu về CAR chỉ cho phép: `Admin`, `Risk_Manager`.
    *   Tài liệu về An toàn kho quỹ: Cho phép `Admin`, `Risk_Manager`, `Staff`.
    *   Tài liệu về quy chế hoạt động chung: Cho phép mọi vai trò.

### 6.3. Prompt hệ thống & Kịch bản xử lý
*   **Cypher Query lọc quyền RBAC**:
    ```cypher
    MATCH (v:VanBan)-[:CONTAINS]->(d:DieuKhoan)
    WHERE any(role IN v.allowed_roles WHERE role IN $user_roles)
    RETURN v.id, d.id, d.text
    ```

---

## 7. BUỔI 16: Đánh Giá Hiệu Năng Hệ Thống RAG (RAG Evaluation) Bằng Ragas

### 7.1. Mục tiêu & Nội dung học
*   Thiết kế và cài đặt quy trình đánh giá tự động chất lượng hệ thống RAG sử dụng thư viện **Ragas**.
*   Áp dụng kiến trúc 2 mô hình độc lập để chấm điểm khách quan (LLM-as-a-judge):
    *   **Generator Model**: `Qwen/Qwen3.5-9B:deepinfra` (sinh câu trả lời).
    *   **Judger Model**: `openai/gpt-oss-20b:deepinfra` (đóng vai trò trọng tài).
*   Đánh giá hệ thống qua 4 chỉ số cốt lõi: *Context Precision*, *Context Recall*, *Faithfulness*, và *Answer Relevancy*.

### 7.2. Dữ liệu thử nghiệm (Test Data)
*   **Golden Dataset**: 20 câu hỏi & đáp án chuẩn (Ground Truth) được tự động sinh từ tệp `chunks_secure.csv` phân theo độ khó (Easy, Medium, Hard).
*   Tệp ghi nhận kết quả: `evaluation_results.csv` và báo cáo `ragas_evaluation_report.md`.

### 7.3. Prompt hệ thống & Kịch bản xử lý
*   **Prompt Ragas Evaluator (Faithfulness - mẫu)**:
    ```text
    Dựa trên ngữ cảnh cung cấp và câu trả lời được tạo ra, hãy chia nhỏ câu trả lời thành từng phán đoán đơn lẻ. Với mỗi phán đoán, xác định xem nó có được suy ra trực tiếp từ ngữ cảnh hay không. Trả về định dạng JSON điểm số trung thực (Faithfulness Score).
    ```

---

## 8. BUỔI 17: RBAC, Audit Trail và AI Compliance Gap Checker

### 8.1. Mục tiêu & Nội dung học
*   Bổ sung cơ chế lưu vết nhật ký hoạt động (Audit Trail) để ghi nhận chi tiết mọi hành vi truy cập hệ thống.
*   Xây dựng module **AI Compliance Gap Checker** nhằm tự động so sánh, đối chiếu chéo các quy định nội bộ của ngân hàng với các quy định pháp lý chung/Thông tư Ngân hàng Nhà nước.
*   Giao diện người dùng Streamlit hỗ trợ đóng vai và kiểm tra phân tích kẽ hở tuân thủ.

### 8.2. Dữ liệu thử nghiệm (Test Data)
*   Quy định nội bộ Agribank: `agr_car02`, `agr_at01`, `agr_td03`.
*   Quy định pháp lý / SBV: `117310` (Thông tư 41/2016/TT-NHNN), `44209` (Thông tư 01/2014/TT-NHNN).

### 8.3. Prompt hệ thống & Kịch bản xử lý
*   **Prompt Compliance Gap Analysis (Gemini)**:
    ```text
    So sánh quy định nội bộ (A) và quy định pháp lý (B) dưới đây. Hãy xác định trạng thái tuân thủ:
    - DAP_UNG: Nội bộ tuân thủ đầy đủ.
    - THIEU: Quy định nội bộ bị thiếu so với luật pháp.
    - CHENH_LECH: Có sự chồng chéo hoặc khác biệt về ngưỡng/hạn mức/quy trình.
    - CHUA_DU_BANG_CHUNG: Không đủ cơ sở để so sánh.
    
    Yêu cầu trả về chi tiết Điều khoản trích dẫn cả hai phía và gắn nhãn NEEDS_HUMAN_REVIEW.
    ```

---

## 9. BUỔI 18: AI Compliance Checker và AI Audit Checklist Generator

### 9.1. Mục tiêu & Nội dung học
*   Xây dựng hoàn chỉnh giải pháp **AI Compliance & Audit System** gồm 2 tính năng nghiệp vụ cốt lõi:
    *   **UC3: AI Compliance Checker (Kiểm tra tuân thủ)**: So sánh chéo các văn bản nội bộ, phát hiện các điểm mâu thuẫn chồng chéo, phân loại mức độ nghiêm trọng (Severity: HIGH/MEDIUM/LOW).
    *   **UC4: AI Audit Checklist Generator (Tạo danh mục kiểm toán)**: Sinh tự động danh mục câu hỏi kiểm toán dựa theo phạm vi nghiệp vụ (Domain) và phòng ban kiểm tra (Unit) kèm trích dẫn văn bản gốc.
*   Triển khai bộ 7 bài test bảo mật (RBAC, Citation Integrity, Hallucination Check, Human Review Guardrail, Audit Log Privacy, Unknown Domain, File Export Verification).
*   Giao diện tương tác Streamlit và báo cáo HTML tĩnh đồng bộ.

### 9.2. Dữ liệu thử nghiệm (Test Data)
*   **Văn bản nội bộ**: `agr_car02` (Quyết định 250/QĐ-NHNO-QLRR), `agr_at01` (Quyết định 100/QĐ-NHNO-AT), `agr_td03` (Quy chế 315/QC-NHNO-TD).
*   **Văn bản pháp lý**: `117310` (Thông tư 41), `44209` (Thông tư 01).
*   **Kết quả đầu ra**: `compliance_conflicts.csv` và `audit_checklist_results.csv`.

### 9.3. Prompt hệ thống & Kịch bản xử lý
*   **Prompt UC3 (Compliance Checker)**:
    ```json
    {
      "system_instruction": "Hãy đóng vai trò là chuyên gia giám sát tuân thủ tại Agribank. So sánh văn bản nội bộ của Agribank (A) và quy định pháp lý (B) được cung cấp để tìm ra điểm xung đột/mâu thuẫn. Trích dẫn chính xác Số ký hiệu, Điều, Khoản của cả hai phía.",
      "response_mime_type": "application/json"
    }
    ```
*   **Prompt UC4 (Audit Checklist Generator)**:
    ```json
    {
      "system_instruction": "Hãy sinh danh sách câu hỏi kiểm toán (Audit Checklist) chi tiết dựa vào văn bản nội bộ dưới đây dành cho miền nghiệp vụ và phòng ban được chọn. Mỗi mục phải có câu hỏi, mô tả rủi ro, mức độ rủi ro (HIGH/MEDIUM/LOW) và trích dẫn chuẩn văn bản gốc.",
      "response_mime_type": "application/json"
    }
    ```
