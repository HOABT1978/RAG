# Specification Buổi 08: Advanced RAG Architecture & Evaluation Framework

Dài và chi tiết về hợp đồng dữ liệu (Data Contract), quy trình xử lý đường ống (Pipeline Architecture), thuật toán dung hợp (RRF Fusion), mô hình chấm điểm lại (Cross-Encoder Reranker) và khung đánh giá tự động (Evaluation Framework).

---

## 1. Workspace và Security Contract

- **Workspace Root**: Thư mục `RAG` (`d:\Rag_thuchanh\RAG`), chứa trực tiếp `rag_foundation/`.
- **Thư mục Buổi 08**: `rag_foundation/buoi_08/`.
- **Quyền thao tác**: Tất cả mã nguồn, dữ liệu thử nghiệm, báo cáo đánh giá và dữ liệu lưu trữ mới của Buổi 08 CHỈ ĐƯỢC PHÁP ghi vào trong `rag_foundation/buoi_08/`.
- **Không sửa đổi**: Tuyệt đối không sửa đổi, xóa hoặc can thiệp mã nguồn/dữ liệu của các buổi trước (`buoi_05`, `buoi_07`).
- **Bảo mật Secret**: File `.env` chứa API Key thật (`GEMINI_API_KEY`) không được commit lên hệ thống quản lý phiên bản (Git). Không in trực tiếp giá trị API key ra màn hình, log hoặc giao diện người dùng.

---

## 2. Quan hệ với Buổi 05 và Buổi 07

- **Buổi 05 (Data Chunking Baseline)**: Cung cấp tập dữ liệu JSON chunks tại `rag_foundation/buoi_05/output/chunks/` thuộc 3 chiến lược: `fixed-size`, `semantic`, `hierarchical`. Dữ liệu này được nạp trực tiếp qua đường dẫn tương đối.
- **Buổi 07 (Semantic RAG Baseline)**: Module `rag.py` của Buổi 08 được sao chép độc lập từ Buổi 07 để làm baseline đối chứng cho Semantic Search đơn thuần.
- **Tính độc lập runtime**: Buổi 08 vận hành trên cấu hình `.env` và thư mục lưu trữ ChromaDB (`storage/`) riêng biệt, không đọc/ghi chung cơ sở dữ liệu với Buổi 07.

---

## 3. Data Contract (Hợp đồng dữ liệu Chunks & Metadata)

Mọi chunk dữ liệu đi qua hệ thống RAG (dù từ Buổi 05 hay Fixture sample) đều phải tuân thủ nghiêm ngặt schema JSON sau:

```json
{
  "chunk_id": "string (bắt buộc, không rỗng)",
  "strategy": "fixed-size | semantic | hierarchical (bắt buộc)",
  "source": "string (tên file gốc, bắt buộc)",
  "page_start": "integer (>= 1, bắt buộc)",
  "page_end": "integer (>= page_start, bắt buộc)",
  "text": "string (nội dung văn bản, không rỗng sau khi strip)"
}
```

---

## 4. BM25 Tokenizer & Retrieval Contract

- **Tokenizer tiếng Việt (`tokenize_vietnamese`)**:
  - Chuyển toàn bộ văn bản về chữ thường (lowercase).
  - Loại bỏ các ký tự đặc biệt, chỉ giữ lại ký tự chữ cái, chữ số và khoảng trắng.
  - Phân tách chuỗi dựa trên khoảng trắng và dấu câu.
  - Loại bỏ các stop words phổ biến trong văn bản pháp lý tiếng Việt.
- **Chỉ mục BM25 (`BM25Retriever`)**:
  - Sử dụng thuật toán `BM25Okapi` từ thư viện `rank-bm25`.
  - Tham số cấu hình: $k_1 = 1.5$, $b = 0.75$.
  - Trả về danh sách top-$K_{BM25}$ ứng viên kèm theo điểm số `bm25_score` và xếp hạng `bm25_rank`.

---

## 5. Semantic Candidate Contract

- **Gemini Query Embedding**:
  - Mô hình mặc định: `gemini-embedding-2` (chiều vector: 768).
  - Định dạng câu hỏi: `"task: question answering | query: {question}"`.
- **ChromaDB Semantic Search**:
  - Sử dụng khoảng cách Cosine Distance ($d_{cosine}$).
  - Trả về danh sách top-$K_{Semantic}$ ứng viên kèm điểm khoảng cách `distance` và xếp hạng `semantic_rank`.

---

## 6. Reciprocal Rank Fusion (RRF) Contract

RRF dung hợp hai danh sách kết quả xếp hạng từ BM25 Search và Semantic Search thành một danh sách điểm số thống nhất:

$$\text{RRF\_Score}(d) = \frac{1}{k + \text{rank}_{BM25}(d)} + \frac{1}{k + \text{rank}_{Semantic}(d)}$$

- **Hằng số làm mịn ($k$)**: Mặc định $k = 60$.
- **Nếu chunk chỉ xuất hiện trong 1 danh sách**: Xếp hạng của danh sách thiếu sẽ được tính là $\infty$ (hoặc không đóng góp phần dư vào tổng).
- **Đầu ra RRF**: Trả về tập danh sách ứng viên đã sắp xếp giảm dần theo `rrf_score` với thuộc tính `rrf_rank`.

---

## 7. Cross-Encoder Reranker Contract

- **Mô hình**: `BAAI/bge-reranker-v2-m3` (chạy qua `sentence-transformers` hoặc CrossEncoder inference).
- **Đầu vào**: Cặp câu `(Query, Candidate Document Text)`.
- **Đầu ra**: Điểm tương đồng ngữ nghĩa thực tế `rerank_score` (logit hoặc sigmoid score).
- **Xếp hạng lại**: Sắp xếp lại danh sách ứng viên top-N từ bước RRF theo chiều giảm dần của `rerank_score`, chọn ra top-$K_{Final}$.

---

## 8. Final Evidence & Citation Contract

- **Confidence Gate Threshold**:
  - Đối với Semantic Search: $d_{cosine} \le \text{RAG\_MAX\_DISTANCE}$ (mặc định $0.45$).
  - Đối với Reranker: $\text{rerank\_score} \ge \text{RERANK\_THRESHOLD}$.
- **Trích dẫn (Citation Mapping)**:
  - Gắn nhãn `[E1]`, `[E2]`,... tương ứng với từng evidence vượt qua Confidence Gate.
  - Áp dụng kỹ thuật Prompt Grounding an toàn ngăn ngừa Prompt Injection từ nội dung tài liệu.

---

## 9. Pipeline Trace Contract

Mọi kết quả trả về từ `query_advanced_rag()` đều chứa đối tượng `trace` cho phép kiểm thử và soi chiếu chi tiết từng công đoạn:

```json
{
  "question": "...",
  "strategy": "hierarchical",
  "pipeline_mode": "hybrid_rerank",
  "status": "answered | insufficient_evidence | retrieval_only",
  "answer": "...",
  "trace": {
    "bm25_top_k": [...],
    "semantic_top_k": [...],
    "rrf_fused_candidates": [...],
    "reranked_candidates": [...],
    "final_accepted_evidence": [...]
  }
}
```

---

## 10. Evaluation Metrics Contract

Hệ thống đánh giá offline tính toán các chỉ số chất lượng truy xuất trên tập benchmark `eval/questions.json`:

1. **Hit Rate@K**: Tỷ lệ phần trăm câu hỏi mà trong đó có *ít nhất 1* chunk liên quan thuộc top-K kết quả truy xuất.
2. **MRR@K (Mean Reciprocal Rank)**: Trung bình cộng nghịch đảo vị trí xuất hiện của chunk liên quan đầu tiên:
   $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
3. **Precision@K**: Tỷ lệ chunk liên quan nằm trong top-K truy xuất.
4. **Recall@K**: Tỷ lệ chunk liên quan được tìm thấy so với tổng số chunk liên quan trong tập nhãn gốc (Ground Truth).

---

## 11. Offline Testing Contract

- **Bộ dữ liệu kiểm thử**: Sử dụng file fixture `tests/fixtures/chunks_advanced_sample.json` và bộ câu hỏi `eval/questions.json`.
- **Yêu cầu không phụ thuộc API Key đối với unit test**: Các unit test cho BM25, RRF Fusion, Tokenizer và evaluation metrics phải chạy hoàn toàn offline không cần internet hoặc Gemini API key.
- **Trạng thái nhãn**: Tất cả câu hỏi trong `questions.json` ban đầu cài đặt `needs_human_review: true`.

---

## 12. UI Comparison Contract

Ứng dụng Streamlit ([app.py](file:///d:/Rag_thuchanh/RAG/rag_foundation/buoi_08/app.py)) hiển thị so sánh song song giữa 2 chế độ:
1. **Semantic Baseline (Buổi 07)**: Chỉ sử dụng Vector Search + Confidence Gate.
2. **Advanced Hybrid RAG (Buổi 08)**: Sử dụng BM25 + Semantic Search + RRF + Cross-Encoder Reranker.
Hiển thị bảng so sánh thứ tự xếp hạng của các chunk giữa BM25, Semantic, RRF và Reranker trong tab Pipeline Trace.
