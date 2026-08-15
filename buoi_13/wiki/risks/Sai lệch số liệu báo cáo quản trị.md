---
id: RR-010
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# RuiRo: Sai lệch số liệu báo cáo quản trị

## Thông tin thực thể
- **Mã thực thể (ID)**: `RR-010`
- **Trạng thái xác thực**: `VERIFIED`
- **Nguồn dữ liệu**: `SYNTHETIC`
- **Phân loại rủi ro**: Rui ro bao cao
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `Trung binh`
- **Mức độ rủi ro còn lại (Residual Level)**: `Thap`
- **Đơn vị sở hữu (Owner Unit)**: `DV-FINANCE` *(Chưa có dữ liệu master đơn vị)*

## Mô tả rủi ro
Dữ liệu nguồn không được đối chiếu

## Nguyên nhân (Cause)
Thay đổi dữ liệu không có kiểm soát

## Sự kiện kích hoạt (Event)
Báo cáo quản trị có số liệu sai

## Tác động (Impact)
Quyết định quản trị sai lệch

## Biện pháp kiểm soát giảm thiểu (Mitigating Controls)
- [[Đối chiếu dữ liệu nguồn trước khi phát hành báo cáo]] (Mã: `KS-010`, Loại quan hệ: `MITIGATES`, Trạng thái xác thực: `VERIFIED`, Trích dẫn: *"Dữ liệu mô phỏng: đối chiếu nguồn giảm sai lệch báo cáo"*)

## Sự kiện rủi ro đã phát sinh (Risk Events)
- [[Sự kiện rủi ro SK-010]] (Mã: `SK-010`, Loại quan hệ: `OBSERVED_AS`, Trạng thái xác thực: `VERIFIED`, Trích dẫn: *"Dữ liệu mô phỏng: sự kiện sai lệch báo cáo"*)
