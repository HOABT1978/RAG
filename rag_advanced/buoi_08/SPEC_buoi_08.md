# Specification Buổi 08: Advanced RAG Pipeline (BM25, RRF Fusion & Cross-Encoder Reranking)

---

## 🔒 1. Workspace và Security Contract
- **Workspace Scoping**: Tất cả mã nguồn, dữ liệu cấu hình, lưu trữ vector và kết quả báo cáo của Buổi 08 CHỈ ĐƯỢC PHÉP lưu trữ trong thư mục `rag_advanced/buoi_08/`.
- **Bảo vệ Secret**: Biến môi trường `GEMINI_API_KEY` chỉ được nạp từ file `.env` local của Buổi 08. Không hardcode, không log giá trị key ra console/UI/report, và tuyệt đối không commit file `.env` lên hệ thống kiểm soát phiên bản (Git).

---

## 🔗 2. Quan hệ với Buổi 05 và Buổi 07
- **Kế thừa Buổi 05**: Nạp trực tiếp 9 file JSON chứa 510 chunks từ `rag_foundation/buoi_05/output/chunks/`.
- **Kế thừa Buổi 07**: Bản sao `rag.py` trong `rag_advanced/buoi_08/` lưu giữ toàn bộ loader, Gemini embedding, ChromaDB PersistentClient và confidence gate logic của Buổi 07 làm Semantic Baseline.
- **Tính độc lập**: Không import runtime trực tiếp từ `rag_foundation/buoi_07/`. Mọi dữ liệu lưu trữ vector đặt riêng tại `rag_advanced/buoi_08/storage/chroma/`.

---

## 📑 3. Data Contract
Mỗi chunk record từ Buổi 05 phải tuân thủ chuẩn 6 thuộc tính bắt buộc:
- `chunk_id` (string): ID duy nhất của đoạn văn bản.
- `strategy` (string): Thuộc tập `{"fixed-size", "semantic", "hierarchical"}`.
- `source` (string): Tên file tài liệu gốc (PDF).
- `page_start` (int): Trang bắt đầu (>= 1).
- `page_end` (int): Trang kết thúc (>= page_start).
- `text` (string): Nội dung văn bản tiếng Việt.

---

## 🔤 4. BM25 Tokenizer & Retrieval Contract
- **Tokenizer**: Chuẩn hóa Unicode NFC, `casefold()`, sử dụng Regex Unicode `[\w]+` tách từ tiếng Việt và giữ nguyên số Điều/Khoản.
- **Index**: Dùng `rank_bm25.BM25Okapi` xây dựng chỉ mục trong bộ nhớ (in-memory).
- **Candidate Limit**: Truy xuất `BM25_CANDIDATES` ứng viên đầu tiên (mặc định 20).
- **Tie-Breaking**: Thứ tự tie-break khi bằng điểm BM25: `-bm25_score` $\to$ `chunk_id` (alphabetical ascending).

---

## 🎯 5. Semantic Candidate Contract
- **Query Embedding**: Sử dụng Gemini API `gemini-embedding-2` với chiều `GEMINI_EMBEDDING_DIM = 768`.
- **Vector Search**: Truy vấn ChromaDB PersistentCollection theo khoảng cách Cosine.
- **Candidate Limit**: Truy xuất `SEMANTIC_CANDIDATES` ứng viên (mặc định 20).
- **Status Read-only**: Lệnh `status` chỉ đọc thông tin collection, không tự ý tạo collection rỗng hay gọi API Gemini.

---

## 🔀 6. RRF Fusion Contract
- **Công thức RRF**:
  $$\text{rrf\_score}(d) = \frac{\text{RRF\_BM25\_WEIGHT}}{k + \text{bm25\_rank}} + \frac{\text{RRF\_SEMANTIC\_WEIGHT}}{k + \text{semantic\_rank}}$$
  với $k = \text{RRF\_K}$ (mặc định 60), weights mặc định `1.0`.
- **Hợp nhất Candidate**: Union theo `chunk_id` (không trùng lặp). Giữ candidate dù chỉ thuộc 1 nhánh (`matched_by: ["bm25"]`, `["semantic"]` hoặc `["bm25", "semantic"]`).
- **Tie-Breaking RRF**: `-rrf_score` $\to$ `best_rank` $\to$ `semantic_rank` $\to$ `bm25_rank` $\to$ `chunk_id`.

---

## 🤖 7. Cross-Encoder Reranker Contract
- **Model mặc định**: `BAAI/bge-reranker-v2-m3` (`transformers.AutoModelForSequenceClassification`).
- **Lazy Loading**: Mô hình CHỈ được nạp khi mode `hybrid_rerank` hoặc lệnh CLI `rerank` thực sự được gọi.
- **Inference & Scores**: Input pair `(question, candidate_text)`. Raw logit được chuyển thành `rerank_score = sigmoid(logit)` trong đoạn `[0, 1]`.
- **Sorting Rerank**: `-rerank_score` $\to$ `fused_rank` $\to$ `chunk_id`.
- **Rank Change**: `rank_change = fused_rank - rerank_rank`.
- **Dependency Injection**: Cho phép truyền callable `custom_reranker` phục vụ unit test offline.

---

## 📜 8. Final Evidence & Citation Contract
- **Confidence Gate**:
  - Mode `semantic`: `distance <= RAG_MAX_DISTANCE` (0.45).
  - Mode `hybrid_rerank`: `rerank_score >= RERANK_MIN_SCORE` (0.50).
- **LLM Grounding Prompt**: Chỉ các accepted evidence được đưa vào prompt. Đánh dấu rõ evidence là dữ liệu thô, không phải chỉ dẫn hệ thống.
- **Citation Mapping**: LLM trả về nhãn `[E1]`, `[E2]`. Code tự động bóc tách sang metadata thật (`source`, `page_start`, `page_end`, `chunk_id`). Lọc và cảnh báo các nhãn giả.

---

## ⏱️ 9. Pipeline Trace Contract
Trả về dictionary `trace` trong kết quả RAG:
- `bm25_candidates` (int)
- `semantic_candidates` (int)
- `union` (int) & `overlap` (int)
- `reranked` (int) & `accepted` (int)
- `generation_called` (bool)
- `latency_ms`: dict chứa thời gian thực thi (ms) cho từng tầng: `bm25`, `semantic`, `fusion`, `rerank`, `generation`, `total`.

---

## 📈 10. Evaluation Metrics Contract
- **Metrics**:
  - `Recall@K`: Tỷ lệ relevant chunks được trả về trong top-k.
  - `MRR@K`: Nghịch đảo vị trí xuất hiện của relevant chunk đầu tiên.
  - `nDCG@K`: Discounted Cumulative Gain chuẩn hóa với binary relevance.
  - `Latency`: Mean ms và P50 (median) ms.
- **Không Tuyên bố Winner Giả**: Nếu `needs_human_review = true` trong benchmark dataset, báo cáo JSON phải ghi cảnh báo và đặt `official_winner_declared = false`.
- **0 LLM Generation Call**: Quá trình đánh giá retrieval metrics không gọi LLM generation.

---

## 🧪 11. Offline Testing Contract
- 100% unit tests phải chạy **OFFLINE** (không kết nối mạng, không gọi Gemini API thật, không tải mô hình Hugging Face thật).
- Sử dụng Fake Deterministic Embeddings và Custom Mock Reranker Callable trong unit tests.

---

## 🖥️ 12. UI Comparison Contract
Ứng dụng Streamlit `app.py` thiết kế 4 Tabs rõ ràng:
1. `Hỏi đáp Advanced RAG`: Form hỏi đáp, status badge, evidence cards, citations.
2. `So sánh Retrieval`: Bảng so sánh 4 modes (`bm25`, `semantic`, `hybrid`, `hybrid_rerank`) KHÔNG gọi generation.
3. `Pipeline Trace`: Trực quan hóa luồng candidate counts và biểu đồ latency ms.
4. `Đánh giá Metrics`: Nạp báo cáo JSON từ `reports/`.
