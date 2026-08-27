# HƯỚNG DẪN HỆ THỐNG LOCAL CONTAINERIZED AI SYSTEM (BUỔI 19)
## Agribank RAG Bảo Mật & Kiểm Toán Nội Bộ

Tài liệu này hướng dẫn cài đặt, cấu hình, và vận hành hệ thống trợ lý kiểm toán AI chạy offline hoàn toàn (On-Premise) sử dụng Docker, Ollama (mô hình Qwen3:0.6B) và Streamlit Web Interface. Hệ thống tích hợp toàn bộ giải pháp bảo mật dữ liệu, phân quyền RBAC và ghi vết kiểm toán từ các Buổi 17 & 18.

---

## 1. Kiến trúc Đóng gói Local AI & Docker

Hệ thống được ảo hóa bằng Docker Compose chia thành hai dịch vụ chính chạy trên mạng nội bộ `agribank-ai-network`:
* **Dịch vụ 1 (agribank-ollama-server):** Trình diễn mô hình SLM cục bộ `qwen3:0.6b` (hoặc `qwen2.5:0.5b`) phục vụ suy luận offline hoàn toàn bảo mật.
* **Dịch vụ 2 (agribank-ai-app):** Chạy ứng dụng Streamlit Web và lõi nghiệp vụ RAG Engines kết nối dữ liệu chính sách nội bộ.

```text
                                  [ Cổng 8501 ]
Kiểm toán viên (Browser)  ───>  agribank-ai-app (Streamlit Container)
                                       │
                                       │ (Cổng 11434 - Mạng Nội Bộ Docker)
                                       ▼
                            agribank-ollama-server (Ollama Engine)
                                       │
                                       ▼
                                Mô hình Qwen3:0.6B
```

---

## 2. Danh sách 4 Use Cases tích hợp

Ứng dụng Web tại cổng `8501` tích hợp trọn vẹn cả 4 Use Cases nghiệp vụ:
1. **UC1 - Tra cứu quy định nội bộ (Internal Lookup):** Tra cứu dữ liệu RAG có phân quyền RBAC trước khi truy hồi. Trả về câu trả lời có trích dẫn Chunk ID gốc.
2. **UC2 - Phân tích chênh lệch tuân thủ (Compliance Gap Analysis):** Đối chiếu văn bản pháp lý NHNN và quy trình nội bộ Agribank, tự động phân loại mức độ đáp ứng (`DAP_UNG`, `THIEU`, `CHENH_LECH`, `CHUA_DU_BANG_CHUNG`).
3. **UC3 - AI Compliance Checker (So sánh chéo):** Tự động phát hiện chồng chéo, mâu thuẫn giữa các quy định và đánh giá mức độ nghiêm trọng (`HIGH`, `MEDIUM`, `LOW`).
4. **UC4 - AI Audit Checklist Generator (Sinh Checklist):** Tạo bảng danh mục kiểm soát theo Miền nghiệp vụ (Domain) và Phạm vi Đơn vị (Unit).

---

## 3. Cấu hình biến môi trường `.env`

Tệp cấu hình `.env` cho phép chuyển đổi linh hoạt chế độ suy luận (Dual-Provider Switch):
```env
# Lựa chọn LLM Provider: 'ollama' hoặc 'gemini'
LLM_PROVIDER=ollama

# Cấu hình Local Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:0.6b

# Cấu hình dự phòng Cloud Gemini API (Khi LLM_PROVIDER=gemini)
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
LLM_MODEL=gemini-3.6-flash

APP_ENV=training
```

---

## 4. Hướng dẫn Khởi chạy Hệ thống

### Bước 1: Khởi động các container Docker
Di chuyển vào thư mục dự án và chạy:
```bash
docker compose up -d --build
```
Lệnh này sẽ build lại image ứng dụng Web và khởi chạy cả 2 container ở chế độ background.

### Bước 2: Tải mô hình Qwen vào Ollama Server
Thực hiện lệnh sau để tải và chạy thử mô hình local `qwen3:0.6b` bên trong Ollama Container:
```bash
docker exec -it agribank-ollama-server ollama run qwen3:0.6b "Xin chào"
```

### Bước 3: Truy cập ứng dụng Web
Mở trình duyệt Web của bạn và truy cập: **[http://localhost:8501](http://localhost:8501)**.
* Sử dụng thanh Sidebar để cấu hình LLM Provider, xem trạng thái Ollama Server, chọn vai trò kiểm toán viên (RBAC) và thực hiện các Use Cases.

---

## 5. Kịch bản Nghiệm thu & Kiểm thử tự động

Hệ thống cung cấp sẵn các công cụ tự động để nghiệm thu an toàn thông tin và tính sẵn sàng:
1. **Kiểm tra trạng thái đóng gói và tính sẵn sàng:**
   ```bash
   python scripts/verify_b19_docker.py
   ```
   Xem báo cáo tại: `outputs/b19_docker_acceptance_report.md`
2. **Kiểm tra an ninh và an toàn dữ liệu (6 hạng mục bảo mật):**
   ```bash
   python scripts/security_tests_b19.py
   ```
   Xem báo cáo tại: `outputs/security_test_b19_report.md`
