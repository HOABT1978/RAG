# BÁO CÁO KIỂM THỬ WIKI RISK GRAPH

Báo cáo này được tự động tạo bởi script `validate_wiki.py` để đánh giá tính toàn vẹn của dữ liệu và hệ thống Wiki liên kết.

## 1. Số liệu tổng hợp
- **Tổng số tệp tin Markdown (.md)**: `35` tệp
- **Tổng số liên kết chéo (Wikilinks)**: `78` liên kết
- **Tổng số thực thể trong entities.csv**: `34` thực thể
- **Tổng số quan hệ trong relations.csv**: `22` quan hệ

## 2. Kiểm thử tính toàn vẹn (Tính đúng đắn của code)
### A. Liên kết chéo bị hỏng (Broken Wikilinks)
✅ Không phát hiện liên kết chéo bị hỏng.

### B. Thực thể bị trùng ID trong entities.csv
✅ Không phát hiện ID trùng lặp trong thực thể.

### C. Lệch khớp ID giữa Wiki và entities.csv
✅ Hoàn toàn khớp ID giữa Wiki và entities.csv.

### D. Quan hệ chứa thực thể không tồn tại (Broken Relations)
✅ Tất cả quan hệ đều trỏ đến các thực thể tồn tại.

## 3. Kiểm thử nghiệp vụ rủi ro (Tính đầy đủ của dữ liệu nguồn)
> [!IMPORTANT]
> Các phát hiện dưới đây phản ánh **khoảng trống dữ liệu nguồn (Data Gaps)** từ file hạt giống (seed CSVs) chứ không phải lỗi lập trình.

### A. Rủi ro chưa có biện pháp kiểm soát giảm thiểu (Unmitigated Risks)
⚠️ Phát hiện `2` rủi ro trống biện pháp kiểm soát:
  - Rủi ro `RR-011`: **[[Nhà cung cấp công nghệ không đáp ứng cam kết]]**
  - Rủi ro `RR-012`: **[[Xung đột lợi ích trong mua sắm]]**

### B. Rủi ro chưa có sự kiện thực tế phát sinh (Risks without Events)
✅ Tất cả rủi ro đều ghi nhận ít nhất một sự kiện thực tế phát sinh.

### C. Trang mồ côi (Orphan Pages)
✅ Không có trang thực thể nào bị cô lập (mồ côi).

