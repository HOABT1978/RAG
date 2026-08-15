---
id: RR-001
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RuiRo: Giao dịch chuyển tiền bị hạch toán sai

## Thông tin thực thể
- **Mã thực thể (ID)**: `RR-001`
- **Trạng thái xác thực**: `VERIFIED`
- **Nguồn dữ liệu**: `SYNTHETIC`
- **Phân loại rủi ro**: Rui ro van hanh
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Cao`
- **Mức độ rủi ro còn lại (Residual Level)**: `Trung binh`
- **Đơn vị sở hữu (Owner Unit)**: `DV-OPS` *(Chưa có dữ liệu master đơn vị)*

## Mô tả rủi ro
Đối soát giao dịch cuối ngày không đầy đủ

## Nguyên nhân (Cause)
Thiếu đối chiếu giữa hệ thống thanh toán và sổ cái

## Sự kiện kích hoạt (Event)
Giao dịch được ghi nhận sai trạng thái

## Tác động (Impact)
Tổn thất tài chính và khiếu nại khách hàng

## Biện pháp kiểm soát giảm thiểu (Mitigating Controls)
- [[Đối soát tự động giao dịch và sổ cái]] (Mã: `KS-001`, Loại quan hệ: `MITIGATES`, Trạng thái xác thực: `VERIFIED`, Trích dẫn: *"Dữ liệu mô phỏng: đối soát tự động giảm nguy cơ hạch toán sai"*)

## Sự kiện rủi ro đã phát sinh (Risk Events)
- [[Sự kiện rủi ro SK-001]] (Mã: `SK-001`, Loại quan hệ: `OBSERVED_AS`, Trạng thái xác thực: `VERIFIED`, Trích dẫn: *"Dữ liệu mô phỏng: sự kiện đối soát giao dịch"*)
