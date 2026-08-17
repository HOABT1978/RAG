# BÁO CÁO KIỂM TRA DỰ ÁN VÀ KHẢO SÁT DỮ LIỆU NGUỒN (BUỔI 14)

- **Thư mục làm việc**: `buoi_14/`
- **Thư mục dữ liệu nguồn**: `kb+hops/`

## 1. Cấu trúc thư mục buoi_14/
Danh sách các file hiện có:
- `buoi14.md`
- `scripts\inspect_data.py`
- `scripts\inspect_project.py`
- `TM kiemtra\BÀI KIỂM TRA 02.docx`
- `TM kiemtra\Cau 33.png`
- `TM kiemtra\KQKT bai 12.png`
- `TM kiemtra\Ontap.png`

## 2. Kết quả phân tích dữ liệu nguồn
### A. File `metadata.csv` (Thông tin văn bản)
- **Số dòng dữ liệu**: `15`
- **Encoding**: `utf-8`
- **Tên các cột**: `id`, `title`, `so_ky_hieu`, `ngay_ban_hanh`, `loai_van_ban`, `ngay_co_hieu_luc`, `ngay_het_hieu_luc`, `nguon_thu_thap`, `ngay_dang_cong_bao`, `nganh`, `linh_vuc`, `co_quan_ban_hanh`, `chuc_danh`, `nguoi_ky`, `pham_vi`, `thong_tin_ap_dung`, `tinh_trang_hieu_luc`
- **Số dòng trùng lặp**: `0`
- **Số giá trị Null từng cột**:
  - `id`: 0
  - `title`: 0
  - `so_ky_hieu`: 0
  - `ngay_ban_hanh`: 0
  - `loai_van_ban`: 0
  - `ngay_co_hieu_luc`: 1
  - `ngay_het_hieu_luc`: 14
  - `nguon_thu_thap`: 5
  - `ngay_dang_cong_bao`: 11
  - `nganh`: 3
  - `linh_vuc`: 2
  - `co_quan_ban_hanh`: 0
  - `chuc_danh`: 0
  - `nguoi_ky`: 0
  - `pham_vi`: 0
  - `thong_tin_ap_dung`: 15
  - `tinh_trang_hieu_luc`: 0
- **Khóa chính tiềm năng**: `id`, `title`, `so_ky_hieu`, `ngay_ban_hanh`
- **Trường text/metadata phù hợp citation**: `citation`, `title`, `document_id`, `document_type`

### B. File `content.csv` (Nội dung phân đoạn - chunks)
- **Số dòng dữ liệu**: `15`
- **Encoding**: `utf-8`
- **Tên các cột**: `id`, `content_html`
- **Số dòng trùng lặp**: `0`
- **Số giá trị Null từng cột**:
  - `id`: 0
  - `content_html`: 0
- **Khóa chính tiềm năng**: `id`, `content_html`
- **Trường text phù hợp retrieval**: `text` (Chứa nội dung điều khoản)
- **Trường khóa liên kết**: `chunk_id` (Khóa chính), `document_id` (Khóa ngoại liên kết với văn bản)

### C. File `relationships.csv` (Mối quan hệ đồ thị)
- **Số dòng dữ liệu**: `8`
- **Encoding**: `utf-8`
- **Tên các cột**: `doc_id`, `other_doc_id`, `relationship`, `relationship_type`
- **Số dòng trùng lặp**: `0`
- **Số giá trị Null từng cột**:
  - `doc_id`: 0
  - `other_doc_id`: 0
  - `relationship`: 0
  - `relationship_type`: 0
- **Các loại mối quan hệ có thật trong dữ liệu**:
  - `SUA_DOI_BO_SUNG`
  - `CAN_CU`
  - `VAN_BAN_BO_SUNG`
  - `THAY_THE`
  - `HOP_NHAT`

## 3. Rà soát an toàn mã nguồn (Risk & Safe Audit)
- **Mẫu nhạy cảm `\bDELETE\b`**:
  - Tệp `inspect_project.py`: 1 lần xuất hiện

