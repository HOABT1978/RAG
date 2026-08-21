# Advanced RAG Workshop - Buổi 08: Hybrid Search, RRF Fusion & Cross-Encoder Reranking

## 📌 1. Mục tiêu & Khác biệt giữa Buổi 07 và Buổi 08

Buổi 08 đại diện cho một bước nhảy vọt về kiến trúc RAG (Retrieval-Augmented Generation) chuyên biệt cho văn bản pháp lý tiếng Việt.

| Tiêu chí | Buổi 07 (Semantic Baseline) | Buổi 08 (Advanced RAG Pipeline) |
|---|---|---|
| **Retrieval Stage** | Đơn nguồn: Semantic Vector Search (Gemini Embeddings + ChromaDB). | Đa nguồn: Hybrid Search (BM25 Lexical + Gemini Semantic Vector). |
| **Search Combination** | Không có (chỉ dùng khoảng cách Cosine). | Reciprocal Rank Fusion (RRF) hợp nhất thứ hạng không phụ thuộc thang điểm. |
| **Candidate Stage** | Trả trực tiếp top-k vector gần nhất. | Phân tầng: Candidate Stage (Top 20/20) $\to$ RRF Fusion $\to$ Reranking Stage (Top 5). |
| **Reranking Stage** | Không có Reranker. | Mô hình Cross-Encoder đa ngôn ngữ `BAAI/bge-reranker-v2-m3` chấm điểm lại câu hỏi và văn bản. |
| **Confidence Gate** | Đơn ngưỡng Cosine Distance (`RAG_MAX_DISTANCE`). | Đa tầng: Gate Cosine cho Semantic + Gate Sigmoid Score (`RERANK_MIN_SCORE`) cho Reranker. |
| **Citation Mapping** | Gắn nhãn thủ công hoặc đơn giản. | Tự động bóc tách nhãn `[E1]`, `[E2]` sang metadata thật (`source`, `page_start`, `page_end`, `chunk_id`) và lọc nhãn giả. |

---

## 🏗️ 2. Sơ đồ Kiến trúc Pipeline 5 Tầng (Architecture Flowchart)

```text
[User Query]
     │
     ├──► [Nhánh 1: BM25 Lexical Search] ────► Top 20 Candidate Chunks ──┐
     │    (Tokenizer NFC, casefold, regex)                               │
     │                                                                   ├─► [RRF Fusion] ─► Top 20 Candidates ─► [Cross-Encoder Reranker] ─► Top 5 Final
     └──► [Nhánh 2: Gemini Vector Search] ───► Top 20 Candidate Chunks ──┘   (rrf_score = 1/(k+rank))               (bge-reranker-v2-m3)          │
          (Gemini Embeddings + ChromaDB)                                                                                                            │
                                                                                                                                                    ▼
[Grounded Answer] ◄── [Gemini LLM Generation] ◄── [Grounded Prompt] ◄── [Confidence Gate & Citation Map] ◄──────────────────────────────────────────┘
```

---

## 📂 3. Cấu trúc Project Buổi 08

```text
rag_foundation/buoi_08/
├── SPEC_buoi_08.md                   # Specification chi tiết data contract & pipeline logic
├── README.md                         # Tài liệu hướng dẫn sử dụng và báo cáo nghiệm thu
├── requirements.txt                  # Danh sách phụ thuộc Python
├── .env.example                      # Cấu hình biến môi trường mẫu
├── .env                              # File cấu hình thực thi local
├── .gitignore                        # Cấu hình Git ignore
├── rag.py                            # Baseline Semantic RAG (sao chép từ Buổi 07)
├── advanced_rag.py                   # Module Advanced RAG chính (BM25, RRF, Reranker, Query, Compare)
├── evaluate.py                       # Framework Đánh giá Offline (Recall@K, MRR@K, nDCG@K)
├── app.py                            # Ứng dụng Streamlit Dashboard 4 Tabs
├── eval/
│   └── questions.json                # Tập câu hỏi benchmark nghiệm thu
├── tests/
│   ├── __init__.py
│   ├── test_bm25.py                  # Unit tests BM25 Tokenizer & Search (8/8 PASS)
│   ├── test_semantic.py              # Unit tests Semantic Candidate Stage (6/6 PASS)
│   ├── test_hybrid.py                # Unit tests RRF Fusion & Hybrid Search (10/10 PASS)
│   ├── test_reranker.py              # Unit tests Cross-Encoder Reranker (10/10 PASS)
│   ├── test_answer.py                # Unit tests Answer Pipeline & Grounding (8/8 PASS)
│   └── test_evaluator.py             # Unit tests Metric Formulas & Evaluator (5/5 PASS)
├── reports/                          # Thư mục lưu báo cáo JSON tự động
└── storage/                          # Thư mục lưu trữ đĩa ChromaDB và Hugging Face cache
    ├── chroma/
    └── huggingface/
```

---

## ⚙️ 4. Khởi tạo Môi trường (.venv, requirements & .env)

1. **Kích hoạt Python Virtual Environment**:
   ```bash
   & "D:\Rag_thuchanh\RAG\rag_foundation\buoi_05\.venv\Scripts\Activate.ps1"
   ```
2. **Cài đặt Dependency**:
   ```bash
   pip install -r rag_foundation/buoi_08/requirements.txt
   ```
3. **Cấu hình File `.env`**:
   Tạo file `.env` tại `rag_foundation/buoi_08/.env` dựa trên `.env.example`:
   ```ini
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
   GEMINI_EMBEDDING_MODEL=gemini-embedding-2
   GEMINI_EMBEDDING_DIM=768
   GEMINI_GENERATION_MODEL=gemini-3.5-flash-lite
   RAG_MAX_DISTANCE=0.45
   BM25_CANDIDATES=20
   SEMANTIC_CANDIDATES=20
   RRF_K=60
   RRF_BM25_WEIGHT=1.0
   RRF_SEMANTIC_WEIGHT=1.0
   RERANK_CANDIDATES=20
   FINAL_TOP_K=5
   RERANKER_MODEL=BAAI/bge-reranker-v2-m3
   RERANKER_MAX_LENGTH=512
   RERANK_BATCH_SIZE=4
   RERANK_MIN_SCORE=0.50
   RERANK_DEVICE=auto
   ```

---

## ⚠️ 5. Cảnh báo Tài nguyên đối với Mô hình Reranker

Mô hình Reranker mặc định **`BAAI/bge-reranker-v2-m3`** là một mô hình Cross-Encoder đa ngôn ngữ (Multilingual Transformer):
- **Kích thước tải**: ~**2.2 GB** từ Hugging Face Hub (Lưu tại `storage/huggingface/`).
- **Yêu cầu bộ nhớ**: Ít nhất **4 GB RAM trống** (hoặc **2 GB VRAM GPU** nếu chạy `device=cuda`).
- **Thời gian nạp đầu tiên**: Cần kết nối Internet và mất từ 1 – 3 phút tùy tốc độ mạng.
- **Tốc độ suy luận CPU**: Khoảng 50ms – 200ms cho mỗi batch candidate.

---

## 💻 6. Danh sách Lệnh CLI Chẩn đoán (`advanced_rag.py`)

### 6.1 Lệnh Status (Read-only System Check)
```bash
python rag_foundation/buoi_08/advanced_rag.py status --strategy hierarchical
```

### 6.2 Lệnh Index Vector (Prepare Semantic)
```bash
python rag_foundation/buoi_08/advanced_rag.py prepare-semantic --strategy hierarchical
```

### 6.3 Lệnh Truy xuất BM25 Lexical Search
```bash
python rag_foundation/buoi_08/advanced_rag.py bm25 --strategy hierarchical --question "Điều 7 quy định gì?"
```

### 6.4 Lệnh Truy xuất Semantic Search
```bash
python rag_foundation/buoi_08/advanced_rag.py semantic --strategy hierarchical --question "Điều 7 quy định gì?"
```

### 6.5 Lệnh Dung hợp Hybrid RRF Search
```bash
python rag_foundation/buoi_08/advanced_rag.py hybrid --strategy hierarchical --question "Điều 7 quy định gì?"
```

### 6.6 Lệnh Reranking Chấm điểm lại Candidate
```bash
python rag_foundation/buoi_08/advanced_rag.py rerank --strategy hierarchical --question "Điều 7 quy định gì?"
```

### 6.7 Lệnh Hỏi đáp Advanced RAG (Query - Gọi LLM Generation 1 lần)
```bash
python rag_foundation/buoi_08/advanced_rag.py query --mode hybrid_rerank --strategy hierarchical --question "Điều 7 quy định gì?"
```

### 6.8 Lệnh So sánh thứ tự Xếp hạng 4 Modes (Compare - KHÔNG gọi LLM Generation)
```bash
python rag_foundation/buoi_08/advanced_rag.py compare --strategy hierarchical --question "Điều 7 quy định gì?"
```

---

## 🧪 7. Lệnh Chạy Unittest, Evaluator & Streamlit Web App

### 7.1 Chạy Toàn bộ 47 Unittests (100% Offline)
```bash
python -m unittest discover -s "rag_foundation/buoi_08/tests" -p "test_*.py" -v
```

### 7.2 Chạy Framework Đánh giá Offline (Evaluator)
```bash
python rag_foundation/buoi_08/evaluate.py --strategy hierarchical --k 5
```

### 7.3 Khởi chạy Giao diện Web App Streamlit 4 Tabs
```bash
python -m streamlit run rag_foundation/buoi_08/app.py
```

---

## 📊 8. Giải thích các Thang điểm Đánh giá (Score Metrics)

- **BM25 Score**: Điểm số tần suất xuất hiện từ khóa khớp chính xác theo thuật toán BM25Okapi (*Càng cao càng tốt*).
- **Cosine Distance**: Khoảng cách Cosine giữa 2 vector embedding (*Càng nhỏ càng tốt, 0.0 là khớp tuyệt đối*).
- **RRF Score**: Điểm sốReciprocal Rank Fusion tổng hợp vị trí thứ hạng từ nhiều hệ thống (*Càng cao càng tốt, nằm trong (0, 1]*).
- **Rerank Score**: Điểm số Sigmoid chuẩn hóa trong khoảng `[0.0, 1.0]` từ raw logit của Cross-Encoder Transformer (*Càng cao càng tốt; Đây là score chuẩn hóa của mô hình, không phải xác suất toán học*).

---

## 🎯 9. Giải thích Candidate K và Final Top-K

- **`BM25_CANDIDATES` (20)** & **`SEMANTIC_CANDIDATES` (20)**: Số lượng candidate tối đa rút ra ở vòng sơ tuyển của mỗi nhánh.
- **`RERANK_CANDIDATES` (20)**: Số lượng candidate tối đa được đưa vào mô hình Cross-Encoder để tái chấm điểm.
- **`FINAL_TOP_K` (5)**: Số lượng candidate xuất sắc nhất sau khi rerank được đưa làm bằng chứng (Evidence) cho LLM tổng hợp câu trả lời.

---

## 📈 10. Chỉ số Đánh giá (Evaluation Metrics) & Giới hạn Gold Labels

- **Recall@K**: Tỷ lệ tài liệu chuẩn khớp tìm thấy trong top-K.
- **MRR@K (Mean Reciprocal Rank)**: Điểm số vị trí của tài liệu chuẩn đầu tiên xuất hiện trong kết quả.
- **nDCG@K**: Điểm số đánh giá mức độ ưu tiên xếp các tài liệu chuẩn lên các vị trí cao nhất.
- **⚠️ Giới hạn Gold Labels**: Các câu hỏi trong `eval/questions.json` chứa thuộc tính `"needs_human_review": true`. Do đó, kết quả đánh giá mang tính chất tham khảo chẩn đoán kỹ thuật, chưa tuyên bố mode nào thắng chính thức cho đến khi nhãn được nghiệm thu bởi chuyên gia pháp lý.

---

## 🔍 11. Các Lựa chọn Thử nghiệm So sánh Chẩn đoán (Manual Comparison Questions)

Để chẩn đoán chéo hiệu năng của 4 mode (`bm25`, `semantic`, `hybrid`, `hybrid_rerank`), hệ thống kiểm thử qua 4 dạng câu hỏi điển hình:

- **A. Exact Legal Reference (Truy xuất điều khoản chính xác)**:
  `"Điều 7 quy định như thế nào về cơ cấu lại thời hạn trả nợ?"`
- **B. Paraphrase Semantic (Diễn đạt tự nhiên/Đồng nghĩa)**:
  `"Khách hàng gặp khó khăn có thể được điều chỉnh kỳ hạn trả nợ ra sao?"`
- **C. Multi-concept (Đa khái niệm pháp lý)**:
  `"Phân loại nợ và trích lập dự phòng được thực hiện như thế nào?"`
- **D. Out-of-scope (Ngoài phạm vi tài liệu)**:
  `"Ngân hàng nào có lãi suất tiết kiệm cao nhất hôm nay?"`

---

## 🔧 12. Troubleshooting & Xử lý Lỗi thường gặp

1. **Lỗi `429 RESOURCE_EXHAUSTED` (Gemini API Rate Limit)**:
   - Hệ thống tự động phát hiện `retryDelay` và tạm dừng chờ retry tự động. Nếu quá hạn ngạch ngày, hãy đợi sau 24h hoặc đổi API key.
2. **Lỗi Reranker tải lâu hoặc thiếu bộ nhớ RAM**:
   - Khi chạy lần đầu, hãy đảm bảo Internet ổn định. Nếu RAM quá nhỏ, cấu hình `RERANK_DEVICE=cpu` và `RERANK_BATCH_SIZE=2` trong `.env`.
3. **Lỗi `Collection ... chưa tồn tại`**:
   - Hãy chủ động chạy lệnh `python rag_foundation/buoi_08/advanced_rag.py prepare-semantic --strategy hierarchical` để khởi tạo vector index.

---

## ⚖️ 13. Tuyên bố Miễn trừ Trách nhiệm (Legal Disclaimer)

Hệ thống RAG này được thiết kế phục vụ mục đích nghiên cứu và hỗ trợ tra cứu thông tin học thuật. Sản phẩm **KHÔNG PHẢI VĂN BẢN TƯ VẤN PHÁP LÝ CHÍNH THỨC** và không thay thế cho các văn bản pháp luật hiện hành do Ngân hàng Nhà nước Việt Nam công bố.
