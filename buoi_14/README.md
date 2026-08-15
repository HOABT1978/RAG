# Buổi 14: Nâng cấp RAG với Hybrid Search + Reranking & Knowledge Graph Mini

Dự án này thực hiện các bước nâng cấp cho hệ thống RAG cơ bản bằng cách kết hợp tìm kiếm từ khóa (BM25) và tìm kiếm ngữ nghĩa (Dense Retrieval), sau đó xếp hạng lại (Reranking) và xây dựng Đồ thị tri thức nhỏ trong Neo4j.

---

## 1. Cấu trúc thư mục dự án

```text
buoi_14/
│
├── data/
│   └── processed/
│       └── chunks_normalized.csv    # Corpus chuẩn hóa dùng chung
│
├── src/
│   ├── bm25_retriever.py            # Công cụ tìm kiếm BM25
│   └── dense_retriever.py           # Công cụ tìm kiếm Dense
│
├── scripts/
│   ├── inspect_project.py           # Khảo sát dữ liệu nguồn & an toàn mã nguồn
│   ├── prepare_corpus.py            # Chuẩn hóa corpus gốc
│   └── baseline_retrieval.py        # Thử nghiệm tìm kiếm BM25 & Dense độc lập
│
├── outputs/
│   ├── inspection_report.md         # Báo cáo khảo sát dữ liệu nguồn
│   └── retrieval_examples.md        # Báo cáo kết quả thử nghiệm tìm kiếm
│
├── .env                             # File cấu hình môi trường (API Key & Neo4j)
└── README.md                        # Tài liệu hướng dẫn
```

---

## 2. Thứ tự các lệnh chạy dự án

Từ thư mục gốc dự án, hãy chạy các lệnh sau theo đúng thứ tự:

### Bước 1: Khảo sát và kiểm tra dự án
Kiểm tra cấu trúc thư mục, thống kê dữ liệu nguồn và rà soát an toàn mã nguồn.
```bash
python buoi_14/scripts/inspect_project.py
```

### Bước 2: Chuẩn hóa dữ liệu nguồn (Corpus)
Tiến hành gộp dữ liệu từ `metadata.csv` và `chunks_parsed.json`, khôi phục lại cấu trúc cây phân cấp (`chapter`, `section`, `article`, `clause`) và ghi nhận vào corpus dùng chung.
```bash
python buoi_14/scripts/prepare_corpus.py
```

### Bước 3: Chạy Baseline Retrieval (BM25 & Dense)
Đánh giá và so sánh kết quả tìm kiếm từ khóa và ngữ nghĩa độc lập.
```bash
python buoi_14/scripts/baseline_retrieval.py
```
Hoặc chạy với câu hỏi tùy chọn:
```bash
python buoi_14/scripts/baseline_retrieval.py --query "Câu hỏi của bạn" --top-k 5
```

---

## 3. Hướng dẫn chạy và sử dụng Giao diện Web Streamlit

Dự án cung cấp giao diện Web trực quan để tương tác với hệ thống tìm kiếm pháp lý.

### Cách chạy Streamlit App
Từ thư mục gốc dự án, thực hiện lệnh sau:
```bash
streamlit run buoi_14/app.py
```

### Cách dừng Streamlit App
Để dừng máy chủ Streamlit đang chạy, nhấn tổ hợp phím `Ctrl + C` trên terminal của bạn.

### Cách sử dụng các tính năng giao diện:
1.  **Ô nhập "Câu hỏi"**: Nhập nội dung câu hỏi hoặc từ khóa pháp lý bạn muốn tìm kiếm.
2.  **Lựa chọn "Phương pháp tìm kiếm" (Method)**:
    *   **BM25 (Từ khóa)**: Tìm kiếm khớp từ khóa chính xác (Lexical Search).
    *   **Dense (Ngữ nghĩa)**: Tìm kiếm theo khoảng cách vector ngữ nghĩa (Semantic Search).
    *   **Hybrid (RRF)**: Hợp nhất kết quả BM25 và Dense bằng Reciprocal Rank Fusion.
    *   **Hybrid + Rerank**: Chạy tìm kiếm kết hợp và xếp hạng lại bằng mô hình Cross-Encoder `bge-reranker-v2-m3` để chọn ra phân đoạn tốt nhất.
3.  **Lựa chọn "Top-k"**: Điều chỉnh số lượng kết quả xuất ra màn hình (1 đến 20).
4.  **Giải thích các trường kết quả**:
    *   `Hạng`: Vị trí ưu tiên của phân đoạn sau cùng (1 là tốt nhất).
    *   `Chunk ID`: Định danh duy nhất của phân đoạn.
    *   `Score`: Điểm số tương ứng với phương pháp lựa chọn (điểm RRF hoặc Rerank).
    *   `Citation`: Trích dẫn pháp lý chính xác từ tệp tin gốc.
    *   `Graph Hints`: Bảng hiển thị các quan hệ nghiệp vụ, quan hệ chứa đựng và quan hệ liền kề NEXT trực tiếp từ Neo4j cho các phân đoạn được tìm thấy.

