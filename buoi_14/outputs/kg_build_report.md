# BÁO CÁO THIẾT LẬP KNOWLEDGE GRAPH MINI (BUỔI 14)

Đồ thị tri thức mini biểu diễn mối liên kết cấu trúc giữa các Văn bản pháp lý và các Điều khoản phân đoạn đã được nạp thành công vào cơ sở dữ liệu Neo4j.

## 1. Thống kê số lượng Nodes
- **Số node `:VanBan`**: `15`
- **Số node `:DieuKhoan`**: `6560`

## 2. Thống kê số lượng Cạnh (Relationships)
| Tên quan hệ (Type) | Số lượng bản ghi | Mô tả ý nghĩa |
| :--- | :--- | :--- |
| `CAN_CU` | `4` | Quan hệ nghiệp vụ văn bản (can cu) |
| `CONTAINS` | `6560` | Văn bản chứa Điều khoản |
| `HOP_NHAT` | `1` | Quan hệ nghiệp vụ văn bản (hop nhat) |
| `NEXT` | `6545` | Liên kết chuỗi điều khoản kế tiếp |
| `SUA_DOI_BO_SUNG` | `1` | Quan hệ nghiệp vụ văn bản (sua doi bo sung) |
| `THAY_THE` | `1` | Quan hệ nghiệp vụ văn bản (thay the) |
| `VAN_BAN_BO_SUNG` | `1` | Quan hệ nghiệp vụ văn bản (van ban bo sung) |

## 3. Kiểm thử tính toàn vẹn (Integrity Audit)
- **Số điều khoản mồ côi (không thuộc văn bản nào)**: `0`
- **Số văn bản rỗng (không chứa điều khoản nào)**: `0`

✅ **Kết luận**: Đồ thị tri thức hoàn toàn nhất quán. Không phát hiện điều khoản mồ côi hoặc văn bản rỗng.

