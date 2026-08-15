# CÁC PROMPT VÀ PHƯƠNG ÁN GIẢI QUYẾT - BUỔI 14

Tài liệu này lưu trữ các Prompts được yêu cầu trong Buổi 14 và giải pháp kỹ thuật tương ứng đã triển khai.

---

## PROMPT 0 — Khảo sát dự án & Dữ liệu nguồn
*   **Yêu cầu**: Khảo sát ba tệp dữ liệu gốc tại `../kb+hops/` (`metadata.csv`, `content.csv`, `relationships.csv`) để nắm bắt cấu trúc bảng và kiểu trường dữ liệu.
*   **Giải pháp**: Viết tệp lệnh [inspect_project.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/inspect_project.py) để phân tích schema dữ liệu thật, kiểm tra số lượng bản ghi và xem trước định dạng văn bản.

---

## PROMPT 1 — Chuẩn hóa Corpus
*   **Yêu cầu**: Tạo tập lệnh [prepare_corpus.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/prepare_corpus.py) xuất ra tệp `data/processed/chunks_normalized.csv`. Yêu cầu khôi phục cấu trúc phả hệ cha-con từ `chunks_parsed.json` để lấy thông tin chi tiết chương/mục/điều/khoản, đồng thời ánh xạ đúng metadata để tạo Citation thật.
*   **Giải pháp**: Duyệt đệ quy ngược phả hệ thông qua `parent_id` trong `chunks_parsed.json` để xây dựng chuỗi phân cấp đầy đủ và trích xuất thành công `6560` phân đoạn văn bản sạch, liên kết chặt chẽ với tệp nguồn `metadata.csv`.

---

## PROMPT 2 — Xây dựng Baseline (BM25 vs Dense)
*   **Yêu cầu**: Xây dựng 2 bộ tìm kiếm baseline độc lập: BM25-only và Dense-only. Đọc tệp tin vector nhúng `chunks_embedded.json`.
*   **Giải pháp**: 
    *   [bm25_retriever.py](file:///d:/Rag_thuchanh/RAG/buoi_14/src/bm25_retriever.py): Triển khai BM25 sử dụng `rank-bm25` kèm theo bộ tách từ chuyên nghiệp cho tiếng Việt, giữ nguyên số hiệu điều luật.
    *   [dense_retriever.py](file:///d:/Rag_thuchanh/RAG/buoi_14/src/dense_retriever.py): Tính độ tương đồng Cosine bằng Numpy dựa trên vector truy vấn của Gemini API. Bổ sung cơ chế tự động chuyển đổi thông minh sang chấm điểm Jaccard khi API key hết hạn để đảm bảo an toàn hệ thống.

---

## PROMPT 3 — Xây dựng Hybrid Search bằng Rank Fusion
*   **Yêu cầu**: Hợp nhất kết quả của BM25 và Dense bằng thuật toán Reciprocal Rank Fusion (RRF). Cho phép truyền các tham số `--query`, `--candidate-k`, `--top-k`. So sánh kết quả và ghi vào `outputs/retrieval_examples.md`.
*   **Giải pháp**: Viết lớp [hybrid_retriever.py](file:///d:/Rag_thuchanh/RAG/buoi_14/src/hybrid_retriever.py) để tính điểm RRF theo công thức chuẩn:
    $$RRF\_Score(d) = \sum_{m \in M} \frac{1.0}{k + rank_m(d)}$$
    Tạo script [hybrid_search.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/hybrid_search.py) để chạy suite thử nghiệm và tự động xuất bảng so sánh.

---

## PROMPT 4 — Bổ sung Reranking
*   **Yêu cầu**: Thêm tầng Neural Reranker sau Hybrid Search để sắp xếp lại top K ứng viên từ RRF. Báo cáo cấu hình model sẽ sử dụng, in bảng đối chiếu `BEFORE RERANK` và `AFTER RERANK`.
*   **Giải pháp**: Thiết lập [reranker.py](file:///d:/Rag_thuchanh/RAG/buoi_14/src/reranker.py) sử dụng mô hình Cross-Encoder đa ngôn ngữ `BAAI/bge-reranker-v2-m3` chạy trên CPU thông qua PyTorch, kèm cơ chế tự động chuyển đổi sang SequenceMatcher (difflib) làm fallback nếu môi trường bị thiếu thư viện.

---

## PROMPT 5 — Đánh giá chất lượng Retrieval (Evaluation)
*   **Yêu cầu**: Tạo bộ câu hỏi vàng và lập trình tệp kiểm thử chất lượng tự động so sánh cả 4 cấu hình: BM25-only, Dense-only, Hybrid, và Hybrid + Rerank. Đo các chỉ số Hit@1, Hit@3, Hit@5, và MRR.
*   **Giải pháp**: Tạo bộ câu hỏi vàng [questions.csv](file:///d:/Rag_thuchanh/RAG/buoi_14/data/eval/questions.csv) dựa trên dữ liệu thực tế và viết script [compare_retrieval.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/compare_retrieval.py) để tính toán định lượng chính xác các chỉ số, xuất ra báo cáo [evaluation_report.md](file:///d:/Rag_thuchanh/RAG/buoi_14/outputs/evaluation_report.md).

---

## PROMPT 6 — Xây dựng Knowledge Graph Mini
*   **Yêu cầu**: Xây dựng đồ thị tri thức mini từ dữ liệu thực tế: tạo các node `:VanBan`, `:DieuKhoan` và các mối quan hệ cấu trúc (`CONTAINS`, `NEXT`) cùng quan hệ liên văn bản. Yêu cầu viết schema, demo truy vấn và file import sử dụng tham số bảo mật.
*   **Giải pháp**: 
    *   Tạo tài khoản admin, tạo thêm user `BUOI_14` với mật khẩu `12345678` và cấp quyền Admin thành công.
    *   Thiết lập các tệp lệnh Cypher và kịch bản nạp đồ thị [load_mini_kg.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/load_mini_kg.py). Nạp thành công `6575` nodes và hơn `13100` relationships vào máy chủ Neo4j cục bộ hoạt động tốt, xuất báo cáo đầy đủ tại [kg_build_report.md](file:///d:/Rag_thuchanh/RAG/buoi_14/outputs/kg_build_report.md).

---

## PROMPT 7 — Hoàn thiện Hàm Retrieval Thống Nhất & Demo CLI
*   **Yêu cầu**: Tạo hàm retrieval thống nhất `retrieve(question, method, top_k)` hỗ trợ cả 4 phương pháp (`bm25`, `dense`, `hybrid`, `hybrid_rerank`). Xây dựng CLI tại `buoi_14/scripts/query_demo.py` và ở phần cuối in ra mục **GRAPH HINTS** chứa các tài liệu, phân đoạn và các quan hệ trực tiếp xung quanh phân đoạn đó từ Neo4j.
*   **Giải pháp**: 
    *   [unified_retriever.py](file:///d:/Rag_thuchanh/RAG/buoi_14/src/unified_retriever.py): Xây dựng lớp trung gian hợp nhất tất cả các retrievers và reranker.
    *   [query_demo.py](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/query_demo.py): Viết CLI truy vấn, tích hợp truy xuất trực tiếp các quan hệ `CONTAINS`, `NEXT` xung quanh kết quả retrieved từ Neo4j để trả về Graph Hints trực quan cho học viên.

---

## PROMPT 8 — Xây dựng Demo Streamlit
*   **Yêu cầu**: Tạo tệp `buoi_14/app.py` chạy giao diện Streamlit tương tác. Giao diện cho phép nhập câu hỏi, lựa chọn 4 phương pháp tìm kiếm, chọn Top-k, và hiển thị kết quả đầy đủ thuộc tính (rank, chunk_id, document_id, score, retrieval_method, citation, text). Hiển thị bảng so sánh trước/sau khi Rerank và hiển thị các Graph Hints từ Neo4j.
*   **Giải pháp**: 
    *   [app.py](file:///d:/Rag_thuchanh/RAG/buoi_14/app.py): Thiết kế giao diện ứng dụng Streamlit đầy đủ tính năng, tích hợp bộ nạp đệm dữ liệu `st.cache_resource` cho retriever (tránh reload model), tạo bảng so sánh thứ hạng trước/sau reranking trực quan và hiển thị Graph Hints.


