# BÁO CÁO MÃ HÓA DỮ LIỆU CỤC BỘ (LOCAL ENCRYPTION DEMO REPORT) - BUỔI 17

Báo cáo này minh họa việc bảo vệ dữ liệu nhật ký kiểm toán ở trạng thái lưu trữ (data at-rest) bằng mật mã hóa đối xứng cục bộ.

---

## 1. Kịch Bản Demo Mã Hóa

* **Thuật toán sử dụng**: Đối xứng `Fernet` (thuộc thư viện `cryptography` Python, triển khai AES-128 trong chế độ CBC kết hợp HMAC-SHA256 để xác thực dữ liệu).
* **Tệp tin nhật ký nguồn**: `buoi_17/outputs/audit_log.jsonl`
* **Tệp tin mã hóa (encrypted)**: `buoi_17/outputs/audit_log.jsonl.enc`
* **Cơ chế lưu trữ khóa**: Khóa mã hóa được sinh tự động và lưu trữ tại tệp tin `buoi_17/scripts/secret.key` (đã được cấu hình trong `.gitignore` để đảm bảo an toàn, không bị commit lên GitHub).

---

## 2. Kết Quả Thực Nghiệm Chi Tiết

* **Khóa mã hóa**: Được tải thành công từ tệp tin độc lập. Khóa **không** được hard-code trong mã nguồn.
* **Mã hóa (Encryption)**:
  - Trạng thái: **PASS**
  - Kích thước trước mã hóa: `13230` bytes.
  - Kích thước sau mã hóa: `17720` bytes.
* **Giải mã (Decryption) & So khớp**:
  - Trạng thái: **PASS**
  - So khớp dữ liệu trước/sau giải mã: **Khớp 100%**

---

## 3. Khuyến Nghị An Toàn Hệ Thống

> [!WARNING]
> Bản demo này chỉ nhằm mục đích học tập và minh họa kỹ thuật cơ bản của mã hóa dữ liệu tĩnh (data at-rest). Hệ thống mã hóa này **KHÔNG** đủ tiêu chuẩn để sử dụng trực tiếp trong môi trường Production thực tế của ngân hàng.

**Để triển khai hệ thống mã hóa đạt tiêu chuẩn Enterprise/Production, cần bổ sung:**
1. **Quản lý khóa tập trung (Key Management System - KMS)**: Không lưu khóa dạng file cục bộ trên đĩa của VM. Cần sử dụng các giải pháp quản lý khóa chuyên nghiệp như Google Cloud KMS, HashiCorp Vault hoặc HSM vật lý.
2. **Cơ chế xoay vòng khóa (Key Rotation)**: Xoay vòng khóa định kỳ theo chính sách an ninh của ngân hàng nhằm giảm thiểu rủi ro khi lộ khóa.
3. **Bảo mật kênh truyền (Data in-transit)**: Sử dụng các giao thức bảo mật lớp truyền tải như TLS 1.3 đối với mọi giao tiếp mạng.
4. **Kiểm soát quyền truy cập khóa (IAM)**: Gán quyền chặt chẽ cho các Service Account ứng dụng được phép gọi KMS để mã hóa/giải mã thông qua vai trò cụ thể, ghi nhật ký truy cập khóa độc lập.

---

## 4. Kết Luận Kiểm Thử

```text
ENCRYPT: PASS
DECRYPT MATCH: PASS
PRODUCTION READY: NO
```
