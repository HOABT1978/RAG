# BÁO CÁO KẾT QUẢ TẠO CHECKLIST KIỂM TOÁN (AUDIT CHECKLIST REPORT) - BUỔI 18

Báo cáo này tổng hợp danh sách các mục kiểm soát (Checklist Items) được sinh tự động bằng AI dựa trên các quy định nội bộ và pháp lý được phân loại theo từng phạm vi kiểm toán cụ thể.

---

## 1. Danh Sách Checklist Kiểm Toán Tự Động Sinh Bằng AI

Hệ thống đã sinh **4** đầu mục kiểm tra. Dưới đây là bảng tổng hợp chi tiết:

| Mã mục | Miền nghiệp vụ (Domain) | Phạm vi áp dụng | Câu hỏi kiểm toán | Rủi ro tiềm ẩn | Mức rủi ro | Trích dẫn nguồn | Trạng thái duyệt |
|---|---|---|---|---|---|---|---|
| `CHK_KHO_01` | **An toàn Kho quỹ** | *Chi nhánh & Phòng giao dịch* | Chi nhánh có bố trí xe ô tô bọc thép chuyên dùng và ít nhất 02 bảo vệ chuyên trách khi vận chuyển tiền mặt từ 3 tỷ đồng trở lên hoặc vận chuyển liên tỉnh không? | Rủi ro thất thoát tài sản, cướp giật hoặc tai nạn trong quá trình vận chuyển tiền mặt quy mô lớn. | **HIGH** | `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_at01_02]` | `NEEDS_HUMAN_REVIEW` |
| `CHK_KHO_02` | **An toàn Kho quỹ** | *Chi nhánh* | Ban Quản lý kho tiền mở cửa gian kho có sự chứng kiến đầy đủ của cả 3 thành viên (Giám đốc, Kế toán trưởng, Thủ kho tiền) không? | Rủi ro xâm nhập kho quỹ trái phép, thông đồng lấy cắp tài sản quý và tiền mặt trong kho. | **HIGH** | `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 30 | doc_agr_at01_04]` | `NEEDS_HUMAN_REVIEW` |
| `CHK_IT_03` | **Bảo mật CNTT & AI** | *Khối CNTT & AI* | Nhật ký hệ thống (Audit Trail) của ứng dụng RAG có được lưu trữ tối thiểu 12 tháng và ghi nhận đầy đủ danh tính người dùng cũng như các tài liệu truy cập không? | Thiếu dấu vết kiểm toán khi xảy ra rò rỡ dữ liệu bảo mật hoặc tấn công hệ thống. | **MEDIUM** | `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 16 | doc_agr_it07_02]` | `NEEDS_HUMAN_REVIEW` |
| `CHK_IT_04` | **Bảo mật CNTT & AI** | *Khối CNTT & AI* | Ứng dụng RAG có tích hợp mô hình đánh giá tự động để lọc/phân loại dữ liệu đầu vào và phát hiện các mẫu thông tin restricted trước khi lập chỉ mục không? | Rò rỉ thông tin mật hoặc lưu trữ trái phép dữ liệu bị cấm lên chỉ mục tìm kiếm. | **HIGH** | `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 9 | doc_agr_it07_01]` | `NEEDS_HUMAN_REVIEW` |

---

## 2. Kết Luận Động Cơ Engine

```text
CHECKLIST GENERATOR ENGINE: PASS
CHECKLIST ITEMS CREATED: 4
CITATIONS ATTACHED: YES
```
