# NHẬT KÝ LÀM VIỆC - BUỔI 14 (RAG UPGRADE & KNOWLEDGE GRAPH MINI)

*   **Thời gian**: 15/08/2026
*   **Mục tiêu**: Chuẩn hóa dữ liệu corpus, xây dựng Baseline (BM25 vs Dense), nâng cấp Hybrid Search (RRF), cấu hình tầng Reranking (BGE Cross-Encoder), thực hiện kiểm thử định lượng tự động và nạp cơ sở dữ liệu đồ thị tri thức Neo4j.

---

## 1. Nhật ký hoạt động chi tiết

| STT | Hành động / Bước thực hiện | Tập lệnh / Tệp tin liên quan | Trạng thái | Ghi chú kết quả |
| :--- | :--- | :--- | :---: | :--- |
| 1 | Khảo sát cấu trúc thư mục dữ liệu nguồn | `../kb+hops/` | **HOÀN THÀNH** | Xác nhận 15 văn bản, 6560 dòng text trong content.csv |
| 2 | Thiết lập môi trường và chuẩn hóa dữ liệu | [`prepare_corpus.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/prepare_corpus.py) | **HOÀN THÀNH** | Tạo thành công [chunks_normalized.csv](file:///d:/Rag_thuchanh/RAG/buoi_14/data/processed/chunks_normalized.csv) |
| 3 | Xây dựng Baseline BM25-only và Dense-only | [`bm25_retriever.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/src/bm25_retriever.py), [`dense_retriever.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/src/dense_retriever.py) | **HOÀN THÀNH** | Hỗ trợ fallback thông minh (Jaccard) khi API key hết hạn để tránh crash pipeline |
| 4 | Chạy thử nghiệm đối sánh baseline | [`baseline_retrieval.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/baseline_retrieval.py) | **HOÀN THÀNH** | Xuất báo cáo sơ bộ so sánh BM25 vs Dense |
| 5 | Tích hợp thuật toán Hybrid Search (RRF) | [`hybrid_retriever.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/src/hybrid_retriever.py), [`hybrid_search.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/hybrid_search.py) | **HOÀN THÀNH** | Kết hợp xếp hạng lexical và semantic bằng thuật toán Reciprocal Rank Fusion |
| 6 | Xây dựng bộ Reranking | [`reranker.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/src/reranker.py), [`rerank.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/rerank.py) | **HOÀN THÀNH** | Chạy thành công mô hình Cross-Encoder `BAAI/bge-reranker-v2-m3` cục bộ trên CPU |
| 7 | Thực hiện Đánh giá chất lượng định lượng | [`compare_retrieval.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/compare_retrieval.py) | **HOÀN THÀNH** | Tính toán Hit@1/3/5 và MRR trên bộ 6 câu hỏi vàng. Ghi vào [retrieval_comparison.csv](file:///d:/Rag_thuchanh/RAG/buoi_14/outputs/retrieval_comparison.csv) và [evaluation_report.md](file:///d:/Rag_thuchanh/RAG/buoi_14/outputs/evaluation_report.md) |
| 8 | Tạo tài khoản dịch vụ Neo4j mới | Scratch Script | **HOÀN THÀNH** | Tạo thành công user `BUOI_14` với mật khẩu `12345678` và cấp quyền Admin |
| 9 | Nạp Đồ thị tri thức vào cơ sở dữ liệu Neo4j | [`load_mini_kg.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/load_mini_kg.py) | **HOÀN THÀNH** | Nạp thành công `15` node `:VanBan`, `6560` node `:DieuKhoan`, `6560` cạnh `CONTAINS`, `6545` cạnh `NEXT` và toàn bộ cạnh nghiệp vụ giữa các văn bản |
| 10 | Hàm retrieval thống nhất & Demo CLI | [`query_demo.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/scripts/query_demo.py) | **HOÀN THÀNH** | Tích hợp toàn bộ pipeline tìm kiếm và trích xuất Graph Hints trực tiếp từ Neo4j |
| 11 | Demo Streamlit Giao diện Web | [`app.py`](file:///d:/Rag_thuchanh/RAG/buoi_14/app.py) | **HOÀN THÀNH** | Giao diện tương tác RAG trực quan cho phép so sánh method, hiển thị BEFORE/AFTER Rerank và Neo4j Graph Hints |

---

## 2. Các lệnh đã thực thi trên terminal

1.  **Chuẩn hóa dữ liệu corpus**:
    ```bash
    python buoi_14/scripts/prepare_corpus.py
    ```
2.  **Chạy thử nghiệm baseline**:
    ```bash
    python buoi_14/scripts/baseline_retrieval.py
    ```
3.  **Chạy tìm kiếm Hybrid**:
    ```bash
    python buoi_14/scripts/hybrid_search.py
    ```
4.  **Chạy kiểm thử Rerank độc lập**:
    ```bash
    python buoi_14/scripts/rerank.py
    ```
5.  **Chạy bộ kiểm thử định lượng tự động (Evaluation Suite)**:
    ```bash
    python buoi_14/scripts/compare_retrieval.py
    ```
6.  **Tạo tài khoản và nạp đồ thị tri thức Neo4j**:
    ```bash
    python buoi_14/scripts/load_mini_kg.py
    ```
7.  **Chạy Demo tìm kiếm thống nhất tích hợp Graph Hints**:
    ```bash
    python buoi_14/scripts/query_demo.py --query "quy định về an toàn trong vận chuyển tiền mặt và tài sản quý của ngân hàng" --method hybrid_rerank --top-k 3
    ```
8.  **Khởi chạy Giao diện Web Streamlit**:
    ```bash
    streamlit run buoi_14/app.py
    ```
    hoặc nhấp đúp chạy trực tiếp tệp [`buoi_14/run_app.bat`](file:///d:/Rag_thuchanh/RAG/buoi_14/run_app.bat).
