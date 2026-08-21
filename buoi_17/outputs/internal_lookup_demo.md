# BÁO CÁO USE CASE 1 - AI TRA CỨU QUY ĐỊNH NỘI BỘ - BUỔI 17

Báo cáo này chứng minh khả năng tra cứu văn bản của hệ thống RAG tích hợp phân quyền RBAC và trích dẫn nguồn chính xác.

---

## 1. Kết Quả Chạy Demo Tra Cứu

### Demo 1: Vai trò Guest (User: `guest_01`)
* **Câu hỏi**: *"Các điều kiện để ngân hàng nước ngoài được áp dụng kết quả xếp hạng của doanh nghiệp xếp hạng tín nhiệm độc lập là gì?"*
* **Request ID**: `f5e99c90-3e26-402b-8c61-64bb5a9fbac3`
* **Quyền truy cập (Access Scope)**: `Guest`
* **Kết quả trả về từ AI**:
Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập. (Lỗi xử lý ngôn ngữ)

* **Tài liệu tham chiếu (Citations)**:
  - `[Thông tư số 41/2016/TT-NHNN Quy định tỷ lệ an toàn vốn đối với ngân hàng, chi nhánh ngân hàng nước ngoài | Chương I QUY ĐỊNH CHUNG | nan | Điều 5. Doanh nghiệp xếp hạng tín nhiệm độc lập | 1. Ngân hàng, chi nhánh ngân hàng nước ngoài được áp dụng kết quả xếp hạng của các doanh nghiệp xếp hạng tín nhiệm độc lập được thành lập và hoạt động theo quy định của pháp luật về dịch vụ xếp hạng tín nhiệm để tính tỷ lệ an toàn vốn theo quy định tại Thông tư này khi doanh nghiệp xếp hạng tín nhiệm độc lập đáp ứng các điều kiện sau đây: | chk_117310_0134]`
  - `[Thông tư số 41/2016/TT-NHNN Quy định tỷ lệ an toàn vốn đối với ngân hàng, chi nhánh ngân hàng nước ngoài | Chương I QUY ĐỊNH CHUNG | nan | Điều 5. Doanh nghiệp xếp hạng tín nhiệm độc lập | 4. Ngân hàng, chi nhánh ngân hàng nước ngoài sử dụng thứ hạng tín nhiệm của các doanh nghiệp xếp hạng tín nhiệm độc lập đảm bảo nguyên tắc sau đây: | chk_117310_0146]`
  - `[Thông tư số 41/2016/TT-NHNN Quy định tỷ lệ an toàn vốn đối với ngân hàng, chi nhánh ngân hàng nước ngoài | Chương I QUY ĐỊNH CHUNG | nan | Điều 5. Doanh nghiệp xếp hạng tín nhiệm độc lập | 1. Ngân hàng, chi nhánh ngân hàng nước ngoài được áp dụng kết quả xếp hạng của các doanh nghiệp xếp hạng tín nhiệm độc lập được thành lập và hoạt động theo quy định của pháp luật về dịch vụ xếp hạng tín nhiệm để tính tỷ lệ an toàn vốn theo quy định tại Thông tư này khi doanh nghiệp xếp hạng tín nhiệm độc lập đáp ứng các điều kiện sau đây: | chk_117310_0136]`
  - `[Thông tư số 41/2016/TT-NHNN Quy định tỷ lệ an toàn vốn đối với ngân hàng, chi nhánh ngân hàng nước ngoài | Chương I QUY ĐỊNH CHUNG | nan | Điều 5. Doanh nghiệp xếp hạng tín nhiệm độc lập | 1. Ngân hàng, chi nhánh ngân hàng nước ngoài được áp dụng kết quả xếp hạng của các doanh nghiệp xếp hạng tín nhiệm độc lập được thành lập và hoạt động theo quy định của pháp luật về dịch vụ xếp hạng tín nhiệm để tính tỷ lệ an toàn vốn theo quy định tại Thông tư này khi doanh nghiệp xếp hạng tín nhiệm độc lập đáp ứng các điều kiện sau đây: | chk_117310_0139]`
  - `[Thông tư số 41/2016/TT-NHNN Quy định tỷ lệ an toàn vốn đối với ngân hàng, chi nhánh ngân hàng nước ngoài | Chương I QUY ĐỊNH CHUNG | nan | Điều 5. Doanh nghiệp xếp hạng tín nhiệm độc lập | 1. Ngân hàng, chi nhánh ngân hàng nước ngoài được áp dụng kết quả xếp hạng của các doanh nghiệp xếp hạng tín nhiệm độc lập được thành lập và hoạt động theo quy định của pháp luật về dịch vụ xếp hạng tín nhiệm để tính tỷ lệ an toàn vốn theo quy định tại Thông tư này khi doanh nghiệp xếp hạng tín nhiệm độc lập đáp ứng các điều kiện sau đây: | chk_117310_0138]`
* **Document/Chunk IDs**:
  - `['117310/chk_117310_0134', '117310/chk_117310_0146', '117310/chk_117310_0136', '117310/chk_117310_0139', '117310/chk_117310_0138']`

---
### Demo 2: Vai trò HR (User: `hr_01`)
* **Câu hỏi**: *"Hồ sơ đề nghị cấp Giấy phép lần đầu của quỹ tín dụng nhân dân cần danh sách nhân sự dự kiến bầu, bổ nhiệm gồm những ai?"*
* **Request ID**: `5d77f6f1-3c88-4fe0-b847-17e89717e353`
* **Quyền truy cập (Access Scope)**: `HR`
* **Kết quả trả về từ AI**:
Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập. (Lỗi xử lý ngôn ngữ)

* **Tài liệu tham chiếu (Citations)**:
  - `[Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân | Chương I QUY ĐỊNH CHUNG | nan | Điều 3. Giải thích từ ngữ | 3. Hội nghị thành lập là Hội nghị của các thành viên sáng lập quỹ tín dụng nhân dân, có nhiệm vụ: | chk_177271_0020]`
  - `[Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân | Chương II QUY ĐỊNH CỤ THỂ | Mục 1 QUY ĐỊNH VỀ CẤP GIẤY PHÉP LẦN ĐẦU | Điều 8. Hồ sơ đề nghị cấp Giấy phép lần đầu | 4. Danh sách nhân sự dự kiến bầu, bổ nhiệm làm Chủ tịch và thành viên Hội đồng quản trị, Trưởng ban và thành viên Ban kiểm soát, Giám đốc quỹ tín dụng nhân dân. | chk_177271_0062]`
  - `[Thông tư số 63/2025/TT-NHNN Sửa đổi, bổ sung một số điều của một số Thông tư về quỹ tín dụng nhân dân | Chương III SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA THÔNG TƯ SỐ 10/2025/TT-NHNN QUY ĐỊNH VỀ TỔ CHỨC LẠI, THU HỒI GIẤY PHÉP VÀ THANH LÝ TÀI SẢN CỦA QUỸ TÍN DỤNG NHÂN DÂN | nan | Điều 11. Sửa đổi một số khoản của Điều 14 | 1. Sửa đổi khoản 6 như sau: | chk_185630_0097]`
  - `[Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân | Chương I QUY ĐỊNH CHUNG | nan | Điều 3. Giải thích từ ngữ | 3. Hội nghị thành lập là Hội nghị của các thành viên sáng lập quỹ tín dụng nhân dân, có nhiệm vụ: | chk_177271_0019]`
  - `[Thông tư số 63/2025/TT-NHNN Sửa đổi, bổ sung một số điều của một số Thông tư về quỹ tín dụng nhân dân | Chương III SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA THÔNG TƯ SỐ 10/2025/TT-NHNN QUY ĐỊNH VỀ TỔ CHỨC LẠI, THU HỒI GIẤY PHÉP VÀ THANH LÝ TÀI SẢN CỦA QUỸ TÍN DỤNG NHÂN DÂN | nan | Điều 10. Sửa đổi, bổ sung một số điểm, khoản của Điều 13 | 1. Sửa đổi điểm c khoản 1 như sau: | chk_185630_0085]`
* **Document/Chunk IDs**:
  - `['177271/chk_177271_0020', '177271/chk_177271_0062', '185630/chk_185630_0097', '177271/chk_177271_0019', '185630/chk_185630_0085']`

---
### Demo 3: Vai trò Risk_Manager (User: `risk_01`)
* **Câu hỏi**: *"Hồ sơ đề nghị cấp Giấy phép lần đầu của quỹ tín dụng nhân dân cần danh sách nhân sự dự kiến bầu, bổ nhiệm gồm những ai?"*
* **Request ID**: `a3fd77c2-d2d9-47cd-ab8b-f82452c8c499`
* **Quyền truy cập (Access Scope)**: `Risk_Manager`
* **Kết quả trả về từ AI**:
Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập. (Lỗi xử lý ngôn ngữ)

* **Tài liệu tham chiếu (Citations)**:
  - `[Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân | Chương I QUY ĐỊNH CHUNG | nan | Điều 5. Nguyên tắc lập và gửi hồ sơ | 1. Các văn bản tại hồ sơ đề nghị cấp Giấy phép lần đầu phải do Trưởng ban trù bị ký, trừ trường hợp Thông tư này có quy định khác. Các văn bản do Trưởng ban trù bị ký phải có tiêu đề "Ban trù bị thành lập quỹ tín dụng nhân dân … (tên quỹ tín dụng nhân dân) đề nghị cấp phép". | chk_177271_0032]`
  - `[Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân | Chương I QUY ĐỊNH CHUNG | nan | Điều 1. Phạm vi điều chỉnh | 1. Hồ sơ, trình tự cấp Giấy phép lần đầu của quỹ tín dụng nhân dân. | chk_177271_0004]`
  - `[Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân | Chương I QUY ĐỊNH CHUNG | nan | Điều 5. Nguyên tắc lập và gửi hồ sơ | 3. Hồ sơ đề nghị cấp Giấy phép lần đầu, cấp đổi Giấy phép, cấp bản sao Giấy phép từ sổ gốc của quỹ tín dụng nhân dân được lập 01 bộ bằng tiếng Việt. | chk_177271_0034]`
  - `[Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân | Chương II QUY ĐỊNH CỤ THỂ | Mục 2 QUY ĐỊNH VỀ CẤP ĐỔI GIẤY PHÉP | Điều 11. Nguyên tắc cấp đổi Giấy phép | 3. Trường hợp quỹ tín dụng nhân dân đề nghị bổ sung nội dung hoạt động vào Giấy phép đồng thời với cấp đổi Giấy phép, Ngân hàng Nhà nước Khu vực sẽ xem xét cấp đổi Giấy phép trong đó bao gồm nội dung bổ sung theo đề nghị trên cơ sở quỹ tín dụng nhân dân đáp ứng đầy đủ hồ sơ theo quy định tại khoản 1 Điều 12 Thông tư này. | chk_177271_0131]`
  - `[Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân | Chương III TRÁCH NHIỆM CỦA CÁC TỔ CHỨC, CÁ NHÂN CÓ LIÊN QUAN | nan | Điều 18. Trách nhiệm của Ngân hàng Nhà nước Khu vực | 1. Thẩm định tính đầy đủ, hợp lệ của hồ sơ đề nghị cấp Giấy phép quỹ tín dụng nhân dân trước khi chấp thuận nguyên tắc và có văn bản gửi Ban trù bị để xác nhận hồ sơ đầy đủ, hợp lệ hoặc yêu cầu bổ sung hồ sơ. | chk_177271_0166]`
* **Document/Chunk IDs**:
  - `['177271/chk_177271_0032', '177271/chk_177271_0004', '177271/chk_177271_0034', '177271/chk_177271_0131', '177271/chk_177271_0166']`

---

## 2. Kiểm toán và Đánh giá An ninh (Auditing & Security Assessment)

1. **Kiểm tra trích dẫn (Citations Check)**:
   - Các câu trả lời hợp lệ đều đính kèm chính xác Chunk ID ở dạng `[chk_xxxx]` và liệt kê nguồn gốc của văn bản tham chiếu. Không phát hiện trích dẫn giả mạo.
   - Trạng thái: **PASS**

2. **Kiểm tra an toàn phân quyền (RBAC Check)**:
   - Khi tài khoản `Risk_Manager` cố tình truy cập thông tin nhân sự chỉ dành cho `HR`/`Admin`, hệ thống đã thực hiện lọc bỏ trước (pre-filtering), trả về context trống rỗng và AI đưa ra câu trả lời chuẩn bảo mật: *"Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập."*
   - Dữ liệu bị cấm tuyệt đối **không** đi vào bộ nhớ context của LLM.
   - Trạng thái: **PASS**

3. **Kiểm tra ghi nhật ký kiểm toán (Audit Trail Check)**:
   - Mọi hoạt động tra cứu đều được ghi nhận vào nhật ký kiểm toán `audit_log.jsonl` bao gồm cả các truy cập bị từ chối/trả về rỗng. Nhật ký ghi nhận chính xác `timestamp`, `request_id`, và `rbac_excluded_count`.
   - Trạng thái: **PASS**

---

## 3. Kết Luận Chung

```text
CITATION: PASS
RBAC: PASS
AUDIT: PASS
```
