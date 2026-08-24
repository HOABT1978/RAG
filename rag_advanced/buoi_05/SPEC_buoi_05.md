# SPEC — BUỔI 5: RAG Foundation (OCR PDF tiếng Việt + Trực quan hoá 3 chiến lược chunking)

## 1. Mục đích

Thiết kế 1 thành phần RAG Foundation **độc lập** trong `RAG/rag_foundation/buoi_05/`.
Thành phần này:
1. Đọc PDF tiếng Việt trong `datademo/` (đặc biệt là PDF scan).
2. Dùng kỹ thuật OCR (Llamaparse từ llama-cloud) làm **fallback** khi text layer của
   PyMuPDF trống hoặc bị lỗi font / encoding / ký tự lạ.
3. Minh hoạ trực quan **ba chiến lược chunking**: `fixed-size`, `semantic`, `hierarchical`.
4. Giúp người học nhìn thấy từng bước chuyển đổi: **PDF → text → chunk**.

## 2. Đầu vào

- Thư mục `datademo/` chứa PDF tiếng Việt công khai / mô phỏng.
- File `.env` đặt trong `src/` chứa khoá:
  ```env
  LLAMA_CLOUD_API_KEY='KEY CỦA BẠN'
  ```
- **QUY ĐỊNH**: code được phép *đọc sự tồn tại* của key trong `.env`
  (`dotenv` đọc vào biến môi trường) nhưng **không được đọc giá trị key để in ra
  màn hình, log, ghi vào file output hay commit**.

## 3. Đầu ra

### 3.1 Text chuẩn hoá
- Text Unicode, chuẩn hoá **NFC** (`unicodedata.normalize("NFC", text)`).
- Metadata mỗi tài liệu: `source`, `page`, `ocr_used`, `language` (`vi`), `method`.

### 3.2 Báo cáo chunking
So sánh **3 chiến lược**, mỗi chunk có đủ:
- `chunk_id` (duy nhất trong tài liệu),
- `strategy` (`fixed_size` | `semantic` | `hierarchical`),
- `source` (tên file PDF gốc),
- `page_start`, `page_end`,
- `text`,
- `structure` (metadata cấu trúc **nếu có thật trong văn bản**, ví dụ tiêu đề
  Chương/Mục/Điều — nếu văn bản không có cấu trúc thì ghi cảnh báo, **không bịa heading**).

## 4. Ba chiến lược chunking

| Chiến lược | Nguyên tắc cắt |
|---|---|
| `fixed_size` | Cắt theo số ký tự/token cố định **có overlap** (vd. size 500, overlap 50). |
| `semantic` | Ưu tiên ranh giới đoạn văn: ngắt đoạn (dòng trống / `\n\n`), kết đoạn, cách dòng; cố gắng **không cắt giữa câu**. |
| `hierarchical` | Dựa trên cấu trúc thật: mỗi `Chương → Mục → Điều/Khoản → Điểm` là **mốc bắt đầu** của 1 chunk. Không bịa cấu trúc; nếu không phát hiện heading → dùng semantic + ghi cảnh báo. |

## 5. Quy trình xử lý (luồng độc lập)

1. Liệt kê PDF trong `datademo/`.
2. Với từng PDF: thử lấy text layer bằng **PyMuPDF** (`fitz`).
3. Kiểm tra chất lượng text:
   - text **rỗng** hoặc quá ngắn,
   - **lỗi font/encoding** (dấu tiếng Việt bị vỡ, ký tự lạ như `CQNG HOAXA`),
   - **ký tự lạ** không thuộc bảng mã Unicode hợp lệ.
   - Nếu **trang nào** không dùng được → **render trang ra ảnh** (phục vụ minh hoạ)
     và **gửi OCR toàn bộ file** bằng Llamaparse.
4. Lấy kết quả OCR: `markdown_full` (mẫu gọi trong bài học) cho toàn bộ text;
   lấy markdown **theo từng trang** (kèm `page_number`) qua `parsing.get(job_id,
   expand=["markdown"])` để có metadata `page_start`/`page_end`. Fallback nếu
   không có per-page: tách `markdown_full` theo mốc `<!-- PageBreak -->`.
5. Chuẩn hoá **Unicode NFC** toàn bộ text.
6. **Lưu raw text** + metadata vào `output/raw/`.
7. Chạy **cả 3 chiến lược chunking**, lưu vào `output/chunks/` và viết báo cáo
   `output/report.md` (số chunk, độ dài min/max/trung bình mỗi chiến lược).

## 6. Quy ước thư mục & output

```text
buoi_05/
├── datademo/          # PDF tiếng Việt (không ghi đè, không sửa gốc)
├── src/               # code
├── storage/           # dành riêng (dự phòng)
├── tests/             # kiểm thử đơn giản
├── output/            # sinh khi chạy --write
│   ├── raw/           # text NFC + metadata JSON
│   ├── pages/         # ảnh render từ PDF (minh hoạ)
│   └── chunks/        # JSONL các chunk theo từng chiến lược
├── SPEC_buoi_05.md
├── app.py             # UI Streamlit (tiếng Việt)
└── requirements.txt
```

## 7. Ràng buộc (CONSTRAINTS)

- **KHÔNG** tạo embedding, **KHÔNG** lưu vector database, **KHÔNG** gọi LLM ở Buổi 5.
- Code ở mức **demo đơn giản**, không phức tạp hoá.
- **Không ghi đè PDF gốc**; PDF là dữ liệu công khai/mô phỏng.
- **Không in/log secret**; không commit `.env`.
- Lỗi ở 1 trang / 1 tài liệu **không được dừng** toàn bộ job (bắt lỗi, ghi cảnh báo, tiếp tục).
- Tiếng Việt chuẩn hoá **NFC**.

## 8. Tiêu chí nghiệm thu (checklist)

- [ ] Có cây `RAG/rag_foundation/buoi_05/datademo/` + PDF tiếng Việt công khai/mô phỏng.
- [ ] OCR dùng Llamaparse, có fallback (PyMuPDF trước, OCR sau) và cảnh báo phù hợp.
- [ ] So sánh được `fixed-size`, `semantic`, `hierarchical` (có số liệu min/max/trung bình).
- [ ] UI Streamlit cho thấy PDF → OCR/text → chunk trực quan.
- [ ] Chưa tạo vector database / chưa gọi LLM.
