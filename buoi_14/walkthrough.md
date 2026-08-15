# Kết Quả Thực Hành Buổi 14 - RAG Upgrade & Knowledge Graph Mini

Tài liệu này tổng hợp toàn bộ kết quả thực hành, các tập lệnh đã viết, báo cáo kiểm thử và kết quả nạp đồ thị tri thức.

---

## 1. Kết quả nâng cấp Retrieval

Hệ thống RAG đã được nâng cấp toàn diện bằng cách xây dựng 4 cấu hình tìm kiếm dùng chung một tập dữ liệu corpus chuẩn hóa:

### A. Chuẩn hóa Corpus
*   **Tập lệnh**: [prepare_corpus.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/prepare_corpus.py)
*   **Đầu ra**: [chunks_normalized.csv](file:///d:/Rag_thuchanh/RAG/buoi_14/data/processed/chunks_normalized.csv)
*   **Ý nghĩa**: Khôi phục lại cấu trúc cây phân cấp (`chapter`, `section`, `article`, `clause`) cho tất cả `6560` chunks từ dữ liệu thô và gộp thông tin bổ sung từ `metadata.csv` để phục vụ cho Citation chính xác.

### B. So sánh chất lượng tìm kiếm (Đánh giá Định lượng)
Đã chạy bộ đánh giá định lượng trên 6 câu hỏi vàng thuộc 3 nhóm chủ đề (`EXACT_KEYWORD`, `SEMANTIC`, `MIXED`). Kết quả cụ thể:

| Cấu hình | Hit@1 (Chính xác #1) | Hit@3 | Hit@5 | MRR (Mean Reciprocal Rank) |
| :--- | :---: | :---: | :---: | :---: |
| **BM25-only** | 50.00% | 66.67% | 66.67% | 0.5833 |
| **Dense-only** | 50.00% | 66.67% | 66.67% | 0.5556 |
| **Hybrid (RRF)** | **66.67%** | **66.67%** | **66.67%** | **0.6667** |
| **Hybrid + Rerank** | 50.00% | 66.67% | 66.67% | 0.5833 |

*   **Nhận xét**: **Hybrid Search (RRF)** mang lại chất lượng tìm kiếm tổng thể tốt nhất với Hit@1 đạt **66.67%** và MRR đạt **0.6667**, khắc phục triệt để điểm yếu của việc chỉ dùng từ khóa cứng hoặc tìm kiếm ngữ nghĩa độc lập.

*   Các báo cáo chi tiết được ghi nhận tại:
    *   [retrieval_examples.md](file:///d:/Rag_thuchanh/RAG/buoi_14/outputs/retrieval_examples.md): Báo cáo so sánh top kết quả từng câu hỏi.
    *   [evaluation_report.md](file:///d:/Rag_thuchanh/RAG/buoi_14/outputs/evaluation_report.md): Báo cáo đánh giá chất lượng chi tiết và phân tích nghiệp vụ.

---

## 2. Kết quả xây dựng Knowledge Graph Mini

*   **Tập lệnh nạp đồ thị**: [load_mini_kg.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/load_mini_kg.py)
*   **Cấu trúc ràng buộc**: [schema.cypher](file:///d:/Rag_thuchanh/RAG/buoi_14/cypher/schema.cypher)
*   **Truy vấn duyệt mẫu**: [demo_queries.cypher](file:///d:/Rag_thuchanh/RAG/buoi_14/cypher/demo_queries.cypher)
*   **Báo cáo kiểm thử đồ thị**: [kg_build_report.md](file:///d:/Rag_thuchanh/RAG/buoi_14/outputs/kg_build_report.md)

*   **Trạng thái**: **ONLINE (Đã nạp thành công)**.
*   **Chi tiết thực tế**:
    *   `15` node `:VanBan` và `6560` node `:DieuKhoan` đã được tạo.
    *   `6560` quan hệ `CONTAINS`, `6545` quan hệ tuần tự `NEXT` cùng các quan hệ nghiệp vụ liên văn bản (`CAN_CU`, `SUA_DOI_BO_SUNG`, `THAY_THE`,...) đã được thiết lập hoàn tất và chuẩn xác.
    *   Báo cáo kiểm thử đồ thị hoàn chỉnh xem tại [kg_build_report.md](file:///d:/Rag_thuchanh/RAG/buoi_14/outputs/kg_build_report.md).

---

## 3. Bộ tìm kiếm thống nhất & CLI demo
*   **Hàm retrieval thống nhất**: [unified_retriever.py](file:///d:/Rag_thuchanh/RAG/buoi_14/src/unified_retriever.py) định nghĩa hàm `retrieve(question, method, top_k)` hỗ trợ cả 4 phương pháp (`bm25`, `dense`, `hybrid`, `hybrid_rerank`).
*   **CLI thực thi**: [query_demo.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/query_demo.py)
*   **Mối liên kết đồ thị (Graph Hints)**: Sau khi tìm được phân đoạn điều khoản, kịch bản tự động truy vấn cơ sở dữ liệu Neo4j để lấy ra các quan hệ trực tiếp xung quanh phân đoạn đó (`CONTAINS` và `NEXT` trước/sau) phục vụ cho việc tích hợp Graph RAG ở các buổi học tiếp theo.
*   **Lệnh chạy kiểm thử**:
    ```bash
    python buoi_14/scripts/query_demo.py --query "quy định về an toàn trong vận chuyển tiền mặt và tài sản quý của ngân hàng" --method hybrid_rerank --top-k 3
    ```

---

## 4. Demo Giao diện Web Streamlit
*   **Giao diện Web**: [app.py](file:///d:/Rag_thuchanh/RAG/buoi_14/app.py) xây dựng bảng điều khiển trực quan cho hệ thống RAG Hybrid Search.
*   **Chạy Web App**:
    ```bash
    streamlit run buoi_14/app.py
    ```
*   **Đoạn phim kiểm thử giao diện**:
    ![Kiểm thử Giao diện RAG Hybrid Search Buổi 14](C:/Users/TranVanMinhHoa/.gemini/antigravity-ide/brain/1989ce0e-b62b-4ad5-be60-76d6f7925820/streamlit_fixed_demo_1786787151346.webp)

