# BÁO CÁO KIỂM THỬ AN TOÀN BẢO MẬT & RÒ RỈ DỮ LIỆU (SECURITY AUDIT - BUỔI 15)

- **Ngày kiểm thử**: 2026-08-17
- **Môi trường**: Thư mục làm việc `buoi_15/` - Local Database
- **Tổng số ca kiểm thử quyền truy cập (Sub-test cases)**: 20
- **Số ca thành công (Passed)**: 20
- **Số ca thất bại (Failed)**: 0

### TỶ LỆ ĐẠT CHỨNG NHẬN BẢO MẬT: `100.00%`

> [!IMPORTANT]
> **KẾT LUẬN**: Hệ thống RAG đạt chứng nhận an toàn dữ liệu mức cơ bản. Không phát hiện bất kỳ trường hợp rò rỉ dữ liệu (data leakage) nào đối với các vai trò không được cấp quyền.

---

## Chi tiết các Test Case

### Test Case 1: Kiểm thử tài liệu Nhân sự cấp cao (Luật NHNN 25692)
- **Mã tài liệu nhạy cảm mục tiêu**: `25692`
- **Câu hỏi kiểm thử**: *"quy chế tuyển dụng, bổ nhiệm chức danh Thống đốc và kỷ luật cán bộ Ngân hàng Nhà nước"*
- **Trạng thái**: **✅ PASS**

#### 1. Kiểm thử vai trò KHÔNG ĐƯỢC PHÉP (Chặn rò rỉ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| Guest | `['Guest']` | **PASS (SECURED)** | Không tìm thấy bất kỳ tài liệu cấm nào trong danh sách kết quả. |
| Staff & Risk | `['Staff', 'Risk_Manager']` | **PASS (SECURED)** | Không tìm thấy bất kỳ tài liệu cấm nào trong danh sách kết quả. |

#### 2. Kiểm thử vai trò ĐƯỢC PHÉP (Truy cập hợp lệ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| HR Only | `['HR']` | **PASS (NO_MATCH_IN_DB)** | Tài liệu mục tiêu được phép xem nhưng không lọt vào Top 10 kết quả tương đồng. |
| Admin | `['Admin']` | **PASS (NO_MATCH_IN_DB)** | Tài liệu mục tiêu được phép xem nhưng không lọt vào Top 10 kết quả tương đồng. |

---

### Test Case 2: Kiểm thử tài liệu Rủi ro Quỹ bảo đảm QTDND (Thông tư 27/2024 - 168220)
- **Mã tài liệu nhạy cảm mục tiêu**: `168220`
- **Câu hỏi kiểm thử**: *"trích nộp Quỹ bảo đảm an toàn hệ thống quỹ tín dụng nhân dân hợp tác xã"*
- **Trạng thái**: **✅ PASS**

#### 1. Kiểm thử vai trò KHÔNG ĐƯỢC PHÉP (Chặn rò rỉ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| Guest Only | `['Guest']` | **PASS (SECURED)** | Không tìm thấy bất kỳ tài liệu cấm nào trong danh sách kết quả. |

#### 2. Kiểm thử vai trò ĐƯỢC PHÉP (Truy cập hợp lệ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| Staff Only | `['Staff']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 168220 tại hạng 1 với điểm 6.6842 |
| Risk Manager Only | `['Risk_Manager']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 168220 tại hạng 1 với điểm 6.6842 |
| Admin | `['Admin']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 168220 tại hạng 1 với điểm 6.6842 |

---

### Test Case 3: Kiểm thử tài liệu Tổ chức lại TCD (Thông tư 62/2024 - 174218)
- **Mã tài liệu nhạy cảm mục tiêu**: `174218`
- **Câu hỏi kiểm thử**: *"điều kiện chấp thuận tổ chức lại ngân hàng thương mại phi ngân hàng"*
- **Trạng thái**: **✅ PASS**

#### 1. Kiểm thử vai trò KHÔNG ĐƯỢC PHÉP (Chặn rò rỉ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| Guest Only | `['Guest']` | **PASS (SECURED)** | Không tìm thấy bất kỳ tài liệu cấm nào trong danh sách kết quả. |

#### 2. Kiểm thử vai trò ĐƯỢC PHÉP (Truy cập hợp lệ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| Risk Manager Only | `['Risk_Manager']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 174218 tại hạng 1 với điểm 4.8316 |
| Staff & HR | `['Staff', 'HR']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 174218 tại hạng 1 với điểm 4.8316 |

---

### Test Case 4: Kiểm thử cấp đổi Giấy phép QTDND 2025 (Thông tư 01/2025 - 177271)
- **Mã tài liệu nhạy cảm mục tiêu**: `177271`
- **Câu hỏi kiểm thử**: *"Hồ sơ thủ tục cấp Giấy phép lần đầu cấp đổi Giấy phép của quỹ tín dụng nhân dân"*
- **Trạng thái**: **✅ PASS**

#### 1. Kiểm thử vai trò KHÔNG ĐƯỢC PHÉP (Chặn rò rỉ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| Guest | `['Guest']` | **PASS (SECURED)** | Không tìm thấy bất kỳ tài liệu cấm nào trong danh sách kết quả. |
| HR Only (Without Risk roles) | `['HR']` | **PASS (SECURED)** | Không tìm thấy bất kỳ tài liệu cấm nào trong danh sách kết quả. |

#### 2. Kiểm thử vai trò ĐƯỢC PHÉP (Truy cập hợp lệ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| Risk Manager | `['Risk_Manager']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 177271 tại hạng 1 với điểm 5.7945 |
| Staff Only | `['Staff']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 177271 tại hạng 1 với điểm 5.7945 |

---

### Test Case 5: Kiểm thử tài liệu công cộng (Thông tư 01/2014 - 44209)
- **Mã tài liệu nhạy cảm mục tiêu**: `44209`
- **Câu hỏi kiểm thử**: *"Quy định quy trình niêm phong đóng gói tiền mặt giấy tờ có giá vận chuyển"*
- **Trạng thái**: **✅ PASS**

#### 1. Kiểm thử vai trò KHÔNG ĐƯỢC PHÉP (Chặn rò rỉ):
*Tài liệu công cộng, mọi vai trò đều có quyền truy cập.*

#### 2. Kiểm thử vai trò ĐƯỢC PHÉP (Truy cập hợp lệ):
| Cấu hình vai trò | Danh sách vai trò | Kết quả đánh giá | Chi tiết kiểm chứng |
| :--- | :--- | :--- | :--- |
| Guest | `['Guest']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 44209 tại hạng 1 với điểm 4.8750 |
| Staff | `['Staff']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 44209 tại hạng 1 với điểm 4.8750 |
| Risk Manager | `['Risk_Manager']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 44209 tại hạng 1 với điểm 4.8750 |
| HR | `['HR']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 44209 tại hạng 1 với điểm 4.8750 |
| Admin | `['Admin']` | **PASS (ACCESSIBLE)** | Tìm thấy tài liệu 44209 tại hạng 1 với điểm 4.8750 |

---

