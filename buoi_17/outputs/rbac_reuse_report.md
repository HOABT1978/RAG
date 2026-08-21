# BÁO CÁO PHÂN TÍCH VÀ TÁI SỬ DỤNG RBAC (RBAC REUSE REPORT) - BUỔI 17

Báo cáo này đánh giá tính hợp lệ của phân hệ kiểm soát truy cập dựa trên vai trò (RBAC) đã thiết lập ở Buổi 15 và kết quả chạy thử nghiệm kiểm soát quyền truy cập trên bộ tìm kiếm cũ `SecureRetriever`.

---

## 1. Phân tích Dữ liệu Quyền truy cập (`allowed_roles`)

Dữ liệu được trích xuất và phân tích từ tệp tin `buoi_15/data/processed/chunks_secure.csv` chứa các kết quả sau:

### 1.1. Các vai trò xuất hiện trong dữ liệu (Roles Present)
Hệ thống sử dụng đúng 5 vai trò (được định nghĩa trong `VALID_ROLES` của cấu hình hệ thống):
* `Admin`
* `HR`
* `Risk_Manager`
* `Staff`
* `Guest`

### 1.2. Thống kê phân phối quyền truy cập trên tổng số 6,560 phân đoạn (Chunks)

| Nhóm Vai Trò Hợp Lệ | Số phân đoạn | Tỷ lệ | Phân cấp bảo mật |
| :--- | :---: | :---: | :--- |
| `["Admin", "HR", "Risk_Manager", "Staff", "Guest"]` | `4,873` | 74.28% | **Cấp thấp / Công cộng**: Mọi vai trò (kể cả Guest) đều xem được. |
| `["Admin", "Risk_Manager", "Staff"]` | `1,479` | 22.51% | **Cấp trung bình / Nghiệp vụ**: Chỉ Admin, Risk Manager và Staff được phép xem. |
| `["Admin", "HR"]` | `208` | 3.17% | **Cấp cao / Nội bộ**: Chỉ Admin và Nhân sự (HR) được phép xem. |

* **Số phân đoạn theo từng vai trò cụ thể** (một phân đoạn có thể cho phép nhiều vai trò):
  - `Admin`: **6,560** phân đoạn (100% quyền truy cập).
  - `Risk_Manager`: **6,352** phân đoạn (96.83%).
  - `Staff`: **6,352** phân đoạn (96.83%).
  - `HR`: **5,081** phân đoạn (77.45%).
  - `Guest`: **4,873** phân đoạn (74.28%).

### 1.3. Đánh giá tính chất phân quyền
- **Phân đoạn dùng chung cho nhiều vai trò (Multiple roles)**: **6,560 phân đoạn (100%)**. Không có phân đoạn nào chỉ gán cho duy nhất 1 vai trò, do `Admin` luôn có quyền tối cao và được gán kèm vào mọi phân đoạn.
- **Phân đoạn hạn chế quyền (Restricted chunks)**: **1,687 phân đoạn** (chiếm 25.72% tổng dữ liệu) loại trừ vai trò `Guest` để bảo mật thông tin nhân sự và tín dụng nội bộ. Trong đó có 208 phân đoạn bảo mật tuyệt đối liên quan đến nhân sự chỉ dành riêng cho `Admin` và `HR`.
- **Tính ổn định của định dạng (Parse Stability)**: **100% ổn định**. Không có bất kỳ lỗi cú pháp nào khi thực hiện phân tích chuỗi JSON lưu trong cột `allowed_roles`.
- **Xử lý vai trò không xác định (Unknown role)**: Hệ thống áp dụng nguyên tắc **Default Deny** (Mặc định từ chối). Nếu người dùng chỉ mang một vai trò lạ (ví dụ `Unknown`), hệ thống sẽ lọc ra một DataFrame trống, kết quả là trả về **0 phân đoạn** và không thể tìm thấy bất kỳ thông tin nào.

---

## 2. Kiểm tra bộ tìm kiếm `SecureRetriever` từ Buổi 15

### 2.1. Xác minh cơ chế lọc quyền
- **Đọc cột `allowed_roles`**: Có, module `SecureRetriever` đọc trực tiếp cột dữ liệu này khi khởi tạo DataFrame.
- **Vị trí thực hiện lọc (Filter layer)**: **Lọc trước khi tìm kiếm (Pre-filtering)**.
  - Mã nguồn thực tế tại phương thức `retrieve()`:
    ```python
    auth_df = self.filter_authorized_df(user_roles)
    ```
  - Việc lọc được thực hiện ngay ở bước đầu tiên để sinh ra `auth_df` (DataFrame các phân đoạn mà user có quyền xem). Sau đó, thuật toán BM25 và Vector Search mới được khởi tạo và chạy trên `auth_df`. Do đó, tài liệu không được phép xem bị chặn ngay lập tức, không bao giờ được đưa vào không gian tính điểm hoặc context của LLM.

### 2.2. Kết quả kiểm tra truy vấn thực tế (Test Execution)
Thực hiện chạy thử nghiệm với câu hỏi: *"quy định nhân sự tuyển dụng và hạn mức tín dụng"* trên hệ thống thu được kết quả bảo mật hoàn hảo:

1. **Đóng vai `Admin`**: Trả về 5 phân đoạn có mức bảo mật cao nhất `['Admin', 'HR']` liên quan đến tuyển dụng, bầu bổ nhiệm nhân sự của Quỹ tín dụng nhân dân.
2. **Đóng vai `HR`**: Trả về 5 phân đoạn tương tự nhóm `Admin` liên quan đến hồ sơ và nhân sự quản trị dự kiến.
3. **Đóng vai `Risk_Manager`**: Trả về 5 phân đoạn có nhãn `['Admin', 'Risk_Manager', 'Staff']` liên quan đến rủi ro tín dụng và hệ số chuyển đổi CCF (không hề chứa bất kỳ nội dung nhân sự bảo mật nào của HR).
4. **Đóng vai `Staff`**: Trả về 5 phân đoạn nghiệp vụ tương đương vai trò `Risk_Manager`.
5. **Đóng vai `Guest`**: Trả về 5 phân đoạn cấp thấp nhất `['Admin', 'HR', 'Risk_Manager', 'Staff', 'Guest']` liên quan đến các điều khoản chung và doanh nghiệp xếp hạng tín nhiệm độc lập (không bị lộ thông tin nhân sự hay nghiệp vụ tín dụng chuyên sâu).
6. **Đóng vai `Unknown`**: Trả về **0 phân đoạn** (Đúng nguyên tắc bảo mật tối cao).

---

## 3. Kết luận về việc tái sử dụng

Mã nguồn `SecureRetriever` hiện tại đáp ứng hoàn toàn các tiêu chí bảo mật nghiệp vụ và sẵn sàng để tái sử dụng thông qua một adapter trong Buổi 17 nhằm chuẩn hóa định dạng giao tiếp.

```text
RBAC REUSED: YES
FILTER BEFORE RETRIEVAL: PASS
UNKNOWN ROLE DEFAULT DENY: PASS
```
