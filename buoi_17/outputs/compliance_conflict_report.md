# BÁO CÁO KẾT QUẢ ĐỐI CHIẾU TUÂN THỦ (COMPLIANCE CONFLICT REPORT) - BUỔI 18

Báo cáo này liệt kê danh sách các mâu thuẫn, chồng chéo hoặc điểm chênh lệch được phát hiện giữa các Quy chế/Quy định nội bộ của Agribank (INTERNAL_POLICY) và các văn bản Pháp lý quy định của Ngân hàng Nhà nước (EXTERNAL_REQUIREMENT).

---

## 1. Danh Sách Mâu Thuẫn Tuân Thủ Phát Hiện Được

Hệ thống phát hiện **2** điểm xung đột/mâu thuẫn cần lưu ý:

### Mâu thuẫn 1: ID `CONFLICT_CAR_01`
* **Miền nghiệp vụ (Domain)**: **CAR & Rủi ro**
* **Loại xung đột**: `Hạn mức/ngưỡng`
* **Mức độ nghiêm trọng (Severity)**: `LOW`
* **Trạng thái kiểm tra**: **`NEEDS_HUMAN_REVIEW`**
* **Văn bản nội bộ A**: ID `agr_car02` - Trích dẫn: `[250/QĐ-NHNO-QLRR - Quy định nội bộ số 250/QĐ-NHNO-QLRR | Điều 5 | doc_agr_car02_01]`
  * **Nội dung quy định**: *"Tỷ lệ an toàn vốn tối thiểu (CAR) của Agribank được quy định duy trì ở mức tối thiểu 8.5%, cao hơn 0.5% so với quy định chung 8% tại Thông tư 41/2016/TT-NHNN. Bộ phận Quản lý Rủi ro chịu trách nhiệm tính toán CAR theo tháng và quý."*
* **Văn bản pháp lý B**: ID `117310` - Trích dẫn: `[41/2016/TT-NHNN - Thông tư số 41/2016/TT-NHNN Quy định tỷ lệ an toàn vốn đối với ngân hàng, chi nhánh ngân hàng nước ngoài | Điều 6. Tỷ lệ an toàn vốn | doc_117310_điều_6__tỷ_lệ_an_toàn_vốn_6]`
  * **Nội dung quy định**: *"Ngân hàng, chi nhánh ngân hàng nước ngoài phải duy trì tỷ lệ an toàn vốn tối thiểu 8% xác định trên cơ sở riêng lẻ và hợp nhất."*
* **Mô tả chi tiết phân tích**:
  > Quy định nội bộ Agribank (Điều 5) yêu cầu tỷ lệ an toàn vốn tối thiểu (CAR) đạt 8.5%, trong khi Thông tư 41/2016/TT-NHNN (Điều 9) chỉ yêu cầu tối thiểu 8.0%. Đây là sự chồng chéo về hạn mức/ngưỡng với mức độ nghiêm trọng LOW vì quy định nội bộ nghiêm ngặt hơn quy định pháp lý chung.

---
### Mâu thuẫn 2: ID `CONFLICT_KHO_02`
* **Miền nghiệp vụ (Domain)**: **An toàn kho quỹ**
* **Loại xung đột**: `Quy trình thực hiện`
* **Mức độ nghiêm trọng (Severity)**: `LOW`
* **Trạng thái kiểm tra**: **`NEEDS_HUMAN_REVIEW`**
* **Văn bản nội bộ A**: ID `agr_at01` - Trích dẫn: `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 30 | doc_agr_at01_04]`
  * **Nội dung quy định**: *"Ban Quản lý kho tiền tại mỗi chi nhánh Agribank bao gồm 3 thành viên bắt buộc: Giám đốc (hoặc Phó Giám đốc ủy quyền), Kế toán trưởng (hoặc Phụ trách kế toán) và Thủ kho tiền. Mọi lần mở cửa gian kho tiền phải có mặt đầy đủ 3 thành viên."*
* **Văn bản pháp lý B**: ID `44209` - Trích dẫn: `[01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 63. Hội đồng kiểm kê, Hội đồng kiểm đếm, phân loại tiền kho tiền Trung ương | doc_44209_điều_63__hội_đồng_kiểm_kê__hội_đồng_kiểm_đếm__phân_loại_tiền_kho_tiền_trung_ương_63]`
  * **Nội dung quy định**: *"Hội đồng kiểm kê Quỹ dự trữ phát hành, tài sản quý, giấy tờ có giá tại kho tiền Trung ương gồm Cục trưởng, Trưởng phòng kế toán và thủ quỹ."*
* **Mô tả chi tiết phân tích**:
  > Quy định nội bộ Agribank (Điều 30) quy định thành phần Ban Quản lý kho tiền mở kho hàng ngày bao gồm Giám đốc, Kế toán trưởng và Thủ kho tiền. Trong khi đó, Thông tư 01/2014/TT-NHNN (Điều 63) quy định thành phần Hội đồng kiểm kê kho tiền bao gồm Cục trưởng, Trưởng phòng kế toán và thủ quỹ. Đây là sự chồng chéo/khác biệt về quy trình thực hiện thành viên mở/quản lý kho tiền.

---

## 2. Kết Luận Động Cơ Engine

```text
COMPLIANCE CHECKER ENGINE: PASS
CONFLICTS DETECTED: 2
HUMAN REVIEW GUARDRAIL: PASS
```
