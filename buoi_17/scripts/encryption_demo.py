import os
import io
import sys
from cryptography.fernet import Fernet

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Resolve paths
script_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(script_dir, "secret.key")
audit_log_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "audit_log.jsonl"))
encrypted_log_path = audit_log_path + ".enc"
report_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "encryption_demo_report.md"))

print("=== STARTING LOCAL ENCRYPTION DEMO ===")

# 1. Generate Key (if not exists)
if not os.path.exists(key_path):
    print("Generating new Fernet key...")
    key = Fernet.generate_key()
    with open(key_path, "wb") as key_file:
        key_file.write(key)
else:
    print("Fernet key already exists. Reusing it.")

# 2. Load Key
with open(key_path, "rb") as key_file:
    key = key_file.read()
cipher = Fernet(key)

# 3. Read Original Audit Log
if not os.path.exists(audit_log_path):
    print(f"Error: Audit log not found at {audit_log_path}. Creating a dummy one for test.")
    original_data = b'{"timestamp":"2026-08-21T00:00:00Z", "query":"Test query for encryption", "status":"SUCCESS"}\n'
    with open(audit_log_path, "wb") as f:
        f.write(original_data)
else:
    with open(audit_log_path, "rb") as f:
        original_data = f.read()

print(f"Original file size: {len(original_data)} bytes")

# 4. Encrypt Data
encrypt_success = False
try:
    print("Encrypting data...")
    encrypted_data = cipher.encrypt(original_data)
    with open(encrypted_log_path, "wb") as f:
        f.write(encrypted_data)
    print(f"Encrypted file written to {os.path.basename(encrypted_log_path)} (Size: {len(encrypted_data)} bytes)")
    encrypt_success = True
except Exception as e:
    print("Encryption FAILED:", e)

# 5. Decrypt and Verify
decrypt_match = False
if encrypt_success:
    try:
        print("Reading encrypted file and decrypting...")
        with open(encrypted_log_path, "rb") as f:
            read_encrypted = f.read()
        decrypted_data = cipher.decrypt(read_encrypted)
        
        match = (decrypted_data == original_data)
        print(f"Decrypted data matches original: {match}")
        decrypt_match = match
    except Exception as e:
        print("Decryption FAILED:", e)

encrypt_status = "PASS" if encrypt_success else "FAIL"
decrypt_match_status = "PASS" if decrypt_match else "FAIL"

# 6. Generate Report
report_content = f"""# BÁO CÁO MÃ HÓA DỮ LIỆU CỤC BỘ (LOCAL ENCRYPTION DEMO REPORT) - BUỔI 17

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
  - Trạng thái: **{encrypt_status}**
  - Kích thước trước mã hóa: `{len(original_data)}` bytes.
  - Kích thước sau mã hóa: `{len(encrypted_data) if encrypt_success else 0}` bytes.
* **Giải mã (Decryption) & So khớp**:
  - Trạng thái: **{decrypt_match_status}**
  - So khớp dữ liệu trước/sau giải mã: **{"Khớp 100%" if decrypt_match else "Có sai lệch dữ liệu"}**

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
ENCRYPT: {encrypt_status}
DECRYPT MATCH: {decrypt_match_status}
PRODUCTION READY: NO
```
"""

with open(report_path, "w", encoding="utf-8") as f:
    f.write(report_content)

print(f"Report written successfully to: {report_path}")
print(f"ENCRYPT: {encrypt_status}")
print(f"DECRYPT MATCH: {decrypt_match_status}")
print("PRODUCTION READY: NO")
