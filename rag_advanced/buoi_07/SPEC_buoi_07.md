# Technical Specification - Buổi 07 (Agent Specification)

Tài liệu quy định chi tiết cho AI Agent thực hiện dự án **Buổi 07**.

---

## 1. Workspace

- **Phạm vi được đọc:**
  - `rag_foundation/buoi_05/output/chunks/`
  - `rag_foundation/buoi_05/.venv/`
  - `rag_foundation/buoi_06/`
  - `rag_foundation/buoi_07/`
- **Phạm vi được ghi:**
  - `rag_foundation/buoi_07/` duy nhất.
- **Quy tắc tuyệt đối:** Không sửa đổi bất kỳ file nào thuộc Buổi 05 và Buổi 06.

---

## 2. Python Environment

- **Interpreter:** Sử dụng virtual environment của Buổi 05 tại `rag_foundation/buoi_05/.venv/`.
- Tuyệt đối **không** tạo venv mới.

---

## 3. Input Data

- Nguồn dữ liệu duy nhất: Các file `.json` tại `rag_foundation/buoi_05/output/chunks/`.
- Buổi 05 được coi là nguồn dữ liệu chuẩn bị sẵn (**Black Box**).
- **Không** thực hiện OCR, không parse lại file PDF, không thực hiện re-chunking.

---

## 4. Packages & Dependencies

Chỉ được phép sử dụng các thư viện trực tiếp được định nghĩa trong `requirements.txt`:
- `streamlit>=1.61,<2`
- `google-genai>=2.16,<3`
- `chromadb>=1.5,<2`
- `python-dotenv>=1.2,<2`

---

## 5. Pipeline RAG

Quy trình RAG Buổi 07 bao gồm các bước theo đúng thứ tự:
`Validate Data` ➔ `Embedding` ➔ `Chroma Persistent` ➔ `Retrieval` ➔ `Confidence Gate` ➔ `Generation` ➔ `Citation Verification` ➔ `Streamlit UI` ➔ `Offline Unittest`

---

## 6. Data Contract

Mỗi chunk JSON đầu vào bắt buộc phải chứa các trường dữ liệu sau:
- `chunk_id`: Mã định danh duy nhất của chunk
- `strategy`: Chiến lược phân đoạn (`hierarchical`, `semantic`, `fixed-size`)
- `source`: Tên file gốc (ví dụ: `TT_02_2023_NHNN.pdf`)
- `page_start`: Trang bắt đầu (số nguyên >= 1)
- `page_end`: Trang kết thúc (số nguyên >= page_start)
- `text`: Nội dung văn bản của chunk

---

## 7. Index Contract

- **Bộ sưu tập (Collection):** Mỗi chiến lược (`strategy`) lưu trữ trong một collection riêng biệt hoặc phân tách rõ ràng.
- **Model & Dimension:** Sử dụng `GEMINI_EMBEDDING_MODEL` (`gemini-embedding-2`) với kích thước vector `GEMINI_EMBEDDING_DIM` (768 dimensions) nhất quán giữa Index và Query.
- ** Embedding Thật:** Chỉ sử dụng vector embedding tạo từ Gemini API. **Không** dùng vector giả, vector ngẫu nhiên hay embedding mặc định.
- **Kiểm tra Vector Hợp lệ:** Chặn tuyệt đối các vector chứa giá trị `NaN`, `Infinity`, kiểu `boolean` hoặc zero vector.
- **Chroma Setup:** Sử dụng khoảng cách Cosine, khai báo `embedding_function=None` khi tự quản lý vector.
- **Tính Idempotent:** Thao tác Index phải có tính Idempotent (chạy nhiều lần không gây lặp lại hay lỗi dữ liệu).
- **Hàm `status()`:** Chỉ đọc dữ liệu (read-only), không làm thay đổi DB.
- **Xác thực trước khi lưu:** Validate toàn bộ embedding hoàn chỉnh trước khi gọi reset/upsert vào ChromaDB.

---

## 8. Retrieval Contract

- **Trả về bằng chứng thật:** Retrieval trả về danh sách các chunks bằng chứng kèm theo khoảng cách (`distance`).
- **Confidence Gate:** Chỉ các chunks có `distance <= RAG_MAX_DISTANCE` (mặc định 0.45) mới được coi là đủ độ tin cậy để đưa vào bước Generation.
- **Ngắt sớm khi bằng chứng yếu:** Nếu không có chunk nào đạt ngưỡng `RAG_MAX_DISTANCE`, ngắt sớm và trả về thông báo không đủ thông tin, **không** gọi API Gemini Generation.

---

## 9. Citation Contract

- **Trích dẫn bằng chứng:** Trích dẫn phải lấy từ metadata thật (`source`, `page_start`, `page_end`, `chunk_id`).
- **Không tin tưởng LLM tự tạo citation:** Không sử dụng thông tin nguồn/trang do LLM tự bịa đặt.
- **Cấu trúc trả về:** Kết quả trả về chứa `citations` và `warnings`; code backend tự động kiểm tra và thay thế label bằng trích dẫn chuẩn từ metadata thật.

---

## 10. Security

- Tuyệt đối **không** để lộ API key, secret token trong log, print hay giao diện UI.

---

## 11. Testing Contract

- Tất cả unit tests nằm trong thư mục `tests/`.
- Sử dụng `unittest` kết hợp `unittest.mock` để mock toàn bộ API calls (`google-genai`).
- Sử dụng temporary storage cách ly cho ChromaDB trong các bài test.
- Đảm bảo 100% test suite chạy thành công **offline** không cần Internet hay API key thật.

---

## 12. Coding Style

- Tối giản số lượng file, class và function.
- Viết code rõ ràng, trực diện, không áp dụng các pattern phức tạp (như Repository, Factory, DI).
- **Quy tắc đường dẫn:** Bắt buộc dùng `Path(__file__).resolve()` để xử lý đường dẫn file tương đối, không hard-code đường dẫn tuyệt đối theo máy.
