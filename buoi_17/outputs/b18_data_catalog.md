# BÁO CÁO CATALOGING DỮ LIỆU - BUỔI 18

Báo cáo này thực hiện thống kê, phân loại và đánh giá chất lượng dữ liệu của hai tệp:
1. `agribank_internal_policies.csv` (dữ liệu chính sách nội bộ)
2. `chunks_combined_secure.csv` (dữ liệu kết hợp bảo mật)

---

## 1. Thống Kê Chi Tiết Văn Bản Nội Bộ Agribank

Hệ thống phát hiện **10** văn bản nội bộ từ Agribank. Dưới đây là danh sách chi tiết:

| STT | ID | Tiêu đề | Số ký hiệu | Loại văn bản | Cơ quan ban hành | Ngày ban hành | Miền nghiệp vụ (Domain) |
|---|---|---|---|---|---|---|---|
| 1 | `agr_at01` | Quy định nội bộ số 100/QĐ-NHNO-AT về Giao nhận, bảo quản, vận chuyển tiền mặt và tài sản quý Agribank | `100/QĐ-NHNO-AT` | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 15/03/2024 | **An toàn kho quỹ** |
| 2 | `agr_bh06` | Quy định nội bộ số 180/QĐ-NHNO-BH về Mua bảo hiểm rủi ro nghiệp vụ và tài sản Agribank | `180/QĐ-NHNO-BH` | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 14/02/2024 | **Bảo hiểm** |
| 3 | `agr_car02` | Quy định nội bộ số 250/QĐ-NHNO-QLRR về Quản lý tỷ lệ an toàn vốn và định mức rủi ro Agribank | `250/QĐ-NHNO-QLRR` | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 20/06/2024 | **CAR & Rủi ro** |
| 4 | `agr_fx04` | Quy định nội bộ số 410/QĐ-NHNO-TTNH về Quản lý trạng thái ngoại tệ và giao dịch ngoại hối Agribank | `410/QĐ-NHNO-TTNH` | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 05/09/2024 | **Ngoại tệ** |
| 5 | `agr_gp05` | Quy chế số 520/QC-NHNO-MANGLUOI về Mở rộng mạng lưới chi nhánh và phòng giao dịch Agribank | `520/QC-NHNO-MANGLUOI` | Quy chế nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 18/11/2024 | **Mạng lưới chi nhánh** |
| 6 | `agr_hr08` | Quy định nội bộ số 88/QĐ-NHNO-NS về Quy hoạch, bổ nhiệm và quản lý nhân sự Agribank | `88/QĐ-NHNO-NS` | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 10/01/2025 | **Nhân sự** |
| 7 | `agr_it07` | Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT về An toàn thông tin và Quản trị dữ liệu AI Agribank | `600/QC-NHNO-CNTT` | Quy chế nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 01/03/2025 | **CNTT & AI** |
| 8 | `agr_tc09` | Quy chế tài chính số 720/QC-NHNO-TC về Chế độ chi tiêu và mua sắm tài sản nội bộ Agribank | `720/QC-NHNO-TC` | Quy chế nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 05/12/2024 | **Tài chính mua sắm** |
| 9 | `agr_td03` | Quy chế tín dụng nội bộ số 315/QC-NHNO-TD về Phán quyết và Phân cấp ủy quyền cho vay tại Agribank | `315/QC-NHNO-TD` | Quy chế nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 10/01/2024 | **Tín dụng** |
| 10 | `agr_xln10` | Quy định nội bộ số 390/QĐ-NHNO-XLN về Phân loại nợ và Xử lý nợ xấu tại Agribank | `390/QĐ-NHNO-XLN` | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 22/07/2024 | **Xử lý nợ** |

---

## 2. Phân Loại Văn Bản Theo Miền Nghiệp Vụ (Domain)

Dưới đây là danh sách phân loại chi tiết các văn bản theo từng miền nghiệp vụ nghiệp vụ ngân hàng:

### Miền: **An toàn kho quỹ**
- **ID**: `agr_at01` - *Quy định nội bộ số 100/QĐ-NHNO-AT về Giao nhận, bảo quản, vận chuyển tiền mặt và tài sản quý Agribank* (Ký hiệu: `100/QĐ-NHNO-AT`)

### Miền: **Bảo hiểm**
- **ID**: `agr_bh06` - *Quy định nội bộ số 180/QĐ-NHNO-BH về Mua bảo hiểm rủi ro nghiệp vụ và tài sản Agribank* (Ký hiệu: `180/QĐ-NHNO-BH`)

### Miền: **CAR & Rủi ro**
- **ID**: `agr_car02` - *Quy định nội bộ số 250/QĐ-NHNO-QLRR về Quản lý tỷ lệ an toàn vốn và định mức rủi ro Agribank* (Ký hiệu: `250/QĐ-NHNO-QLRR`)

### Miền: **Ngoại tệ**
- **ID**: `agr_fx04` - *Quy định nội bộ số 410/QĐ-NHNO-TTNH về Quản lý trạng thái ngoại tệ và giao dịch ngoại hối Agribank* (Ký hiệu: `410/QĐ-NHNO-TTNH`)

### Miền: **Mạng lưới chi nhánh**
- **ID**: `agr_gp05` - *Quy chế số 520/QC-NHNO-MANGLUOI về Mở rộng mạng lưới chi nhánh và phòng giao dịch Agribank* (Ký hiệu: `520/QC-NHNO-MANGLUOI`)

### Miền: **Nhân sự**
- **ID**: `agr_hr08` - *Quy định nội bộ số 88/QĐ-NHNO-NS về Quy hoạch, bổ nhiệm và quản lý nhân sự Agribank* (Ký hiệu: `88/QĐ-NHNO-NS`)

### Miền: **CNTT & AI**
- **ID**: `agr_it07` - *Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT về An toàn thông tin và Quản trị dữ liệu AI Agribank* (Ký hiệu: `600/QC-NHNO-CNTT`)

### Miền: **Tài chính mua sắm**
- **ID**: `agr_tc09` - *Quy chế tài chính số 720/QC-NHNO-TC về Chế độ chi tiêu và mua sắm tài sản nội bộ Agribank* (Ký hiệu: `720/QC-NHNO-TC`)

### Miền: **Tín dụng**
- **ID**: `agr_td03` - *Quy chế tín dụng nội bộ số 315/QC-NHNO-TD về Phán quyết và Phân cấp ủy quyền cho vay tại Agribank* (Ký hiệu: `315/QC-NHNO-TD`)

### Miền: **Xử lý nợ**
- **ID**: `agr_xln10` - *Quy định nội bộ số 390/QĐ-NHNO-XLN về Phân loại nợ và Xử lý nợ xấu tại Agribank* (Ký hiệu: `390/QĐ-NHNO-XLN`)

---

## 3. Kiểm Tra Tính Đầy Đủ Của Metadata (Completeness Check)

Kiểm tra các trường dữ liệu bắt buộc gồm: Điều/Khoản (`article`), trích dẫn (`citation`), và phân quyền (`allowed_roles`).

### 3.1. Đối với dữ liệu chính sách nội bộ (`agribank_internal_policies.csv` - 24 chunks)
- Trường `article`: Tỉ lệ điền **100.0%** (24/24 dòng) -> Trạng thái: **OK**
- Trường `citation`: Tỉ lệ điền **100.0%** (24/24 dòng) -> Trạng thái: **OK**
- Trường `allowed_roles`: Tỉ lệ điền **100.0%** (24/24 dòng) -> Trạng thái: **OK**

### 3.2. Đối với dữ liệu kết hợp (`chunks_combined_secure.csv` - 811 chunks)
- Trường `article`: Tỉ lệ điền **100.0%** (811/811 dòng) -> Trạng thái: **OK**
- Trường `citation`: Tỉ lệ điền **100.0%** (811/811 dòng) -> Trạng thái: **OK**
- Trường `allowed_roles`: Tỉ lệ điền **100.0%** (811/811 dòng) -> Trạng thái: **OK**

---

## 4. Kết Luận Đánh Giá

```text
DATA CATALOGING: PASS
DOMAINS DETECTED: 10
READY FOR UC3 & UC4: YES
```
