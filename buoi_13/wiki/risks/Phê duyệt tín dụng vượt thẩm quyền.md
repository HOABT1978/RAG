---
id: RR-002
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RuiRo: Phê duyệt tín dụng vượt thẩm quyền

## Thông tin thực thể
- **Mã thực thể (ID)**: `RR-002`
- **Trạng thái xác thực**: `VERIFIED`
- **Nguồn dữ liệu**: `SYNTHETIC`
- **Phân loại rủi ro**: Rui ro tin dung
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị sở hữu (Owner Unit)**: `DV-CREDIT` *(Chưa có dữ liệu master đơn vị)*

## Mô tả rủi ro
Kiểm tra hạn mức phê duyệt không hiệu lực

## Nguyên nhân (Cause)
Phân quyền trên hệ thống không cập nhật

## Sự kiện kích hoạt (Event)
Khoản vay được phê duyệt vượt thẩm quyền

## Tác động (Impact)
Tăng nợ xấu và vi phạm quy định

## Biện pháp kiểm soát giảm thiểu (Mitigating Controls)
- [[Kiểm tra hạn mức phê duyệt trên hệ thống]] (Mã: `KS-002`, Loại quan hệ: `MITIGATES`, Trạng thái xác thực: `VERIFIED`, Trích dẫn: *"Dữ liệu mô phỏng: kiểm tra hạn mức ngăn phê duyệt vượt thẩm quyền"*)

## Sự kiện rủi ro đã phát sinh (Risk Events)
- [[Sự kiện rủi ro SK-002]] (Mã: `SK-002`, Loại quan hệ: `OBSERVED_AS`, Trạng thái xác thực: `VERIFIED`, Trích dẫn: *"Dữ liệu mô phỏng: sự kiện vượt thẩm quyền"*)
