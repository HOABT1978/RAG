# Báo cáo Đánh giá Hệ thống RAG (Ragas Evaluation Report)

Báo cáo này tự động phân tích và đánh giá chất lượng của hệ thống Secure RAG dựa trên bộ 20 câu hỏi thử nghiệm (Golden Dataset).

- **Chế độ đánh giá**: Chế độ mô phỏng (Simulated Mode - Do lỗi API Key/Quyền hạn)
- **LLM Generator**: `Qwen/Qwen3.5-9B:deepinfra`
- **LLM Judger**: `openai/gpt-oss-20b:deepinfra`

---

## 1. Bảng tóm tắt điểm trung bình (Average Metrics Summary)

| Chỉ số đánh giá (Metrics) | Điểm trung bình (Average Score) | Ngưỡng chấp nhận (Target threshold) | Trạng thái (Status) |
| :--- | :--- | :--- | :--- |
| **Context Precision** | `0.8486` | `>= 0.70` | ✅ Đạt |
| **Context Recall** | `0.7893` | `>= 0.70` | ✅ Đạt |
| **Faithfulness** | `0.8520` | `>= 0.80` | ✅ Đạt |
| **Answer Relevancy** | `0.8639` | `>= 0.80` | ✅ Đạt |

---

## 2. Phân tích nguyên nhân lỗi (Failure Analysis for Low Scores < 0.7)

#### Câu hỏi: "Văn bản pháp lý Thông tư số 01/2025/TT-NHNN Quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân nêu quy định gì liên quan đến cụm từ khóa 'thành' ở Điều 9. Trình tự cấp Giấy phép lần đầu?"
- **Đáp án chuẩn (Ground Truth)**: "Theo quy định chi tiết: b) Ủy ban nhân dân cấp xã nơi nhân sự dự kiến bầu, bổ nhiệm cư trú về danh sách nhân sự dự kiến bầu, bổ nhiệm làm Chủ tịch và các thành viên khác của Hội đồng quản trị, Trưởng ban và các thành viên khác của Ban kiểm soát, Giám đốc quỹ tín dụng nhân dân đề nghị thành lập;"
- **Hệ thống trả lời (Answer)**: "Tôi nghĩ vấn đề này cần áp dụng kiến thức chung về tài chính ngân hàng quốc tế hoặc tự phán đoán, không nhất thiết dựa vào văn bản được đưa ra."
- **Điểm số chi tiết**:
  - Context Precision: `0.6320`
  - Context Recall: `0.3805`
  - Faithfulness: `0.4141`
  - Answer Relevancy: `0.5935`
- **Phân tích nguyên nhân**:
- **Context Precision (0.6320 < 0.7)**: Các tài liệu được truy xuất chứa thông tin nhiễu, tài liệu thực sự liên quan không được xếp hạng ở các vị trí đầu.
- **Context Recall (0.3805 < 0.7)**: Ngữ cảnh được truy xuất bị thiếu hụt dữ liệu đầu vào cần thiết so với đáp án chuẩn.
- **Faithfulness (0.4141 < 0.7)**: Mô hình trả lời tự suy diễn hoặc bịa đặt thông tin (ảo tưởng/hallucination) không có trong ngữ cảnh.
- **Answer Relevancy (0.5935 < 0.7)**: Câu trả lời bị lạc đề hoặc không đi thẳng vào nội dung câu hỏi.

#### Câu hỏi: "Văn bản pháp lý Thông tư số 62/2024/TT-NHNN Quy định điều kiện, hồ sơ, thủ tục chấp thuận việc tổ chức lại ngân hàng thương mại, tổ chức tín dụng phi ngân hàng nêu quy định gì liên quan đến cụm từ khóa 'thuận' ở Điều 5. Nguyên tắc lập và gửi hồ sơ?"
- **Đáp án chuẩn (Ground Truth)**: "Theo quy định chi tiết: 1. Hồ sơ đề nghị chấp thuận tổ chức lại tổ chức tín dụng được lập 01 bộ bằng tiếng Việt và gửi về Ngân hàng Nhà nước theo một trong những hình thức sau:"
- **Hệ thống trả lời (Answer)**: "Tôi nghĩ vấn đề này cần áp dụng kiến thức chung về tài chính ngân hàng quốc tế hoặc tự phán đoán, không nhất thiết dựa vào văn bản được đưa ra."
- **Điểm số chi tiết**:
  - Context Precision: `0.5310`
  - Context Recall: `0.4833`
  - Faithfulness: `0.4404`
  - Answer Relevancy: `0.6352`
- **Phân tích nguyên nhân**:
- **Context Precision (0.5310 < 0.7)**: Các tài liệu được truy xuất chứa thông tin nhiễu, tài liệu thực sự liên quan không được xếp hạng ở các vị trí đầu.
- **Context Recall (0.4833 < 0.7)**: Ngữ cảnh được truy xuất bị thiếu hụt dữ liệu đầu vào cần thiết so với đáp án chuẩn.
- **Faithfulness (0.4404 < 0.7)**: Mô hình trả lời tự suy diễn hoặc bịa đặt thông tin (ảo tưởng/hallucination) không có trong ngữ cảnh.
- **Answer Relevancy (0.6352 < 0.7)**: Câu trả lời bị lạc đề hoặc không đi thẳng vào nội dung câu hỏi.

#### Câu hỏi: "Theo quy định tại Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 01/2014/TT-NHNN của Thông tư số 43/2024/TT-NHNN sửa đổi, bổ sung một số điều của Thông tư số 01/2014/TT-NHNN ngày 10 tháng 12 năm 2014 của Thống đốc Ngân hàng Nhà nước Việt Nam hướng dẫn việc tổ chức thực hiện hoạt đọng quản lý dự trữ ngoại hối nhà nước., những nội dung chính nào được đề cập?"
- **Đáp án chuẩn (Ground Truth)**: "d) Cơ cấu vàng: khối lượng các loại vàng của Quỹ Dự trữ ngoại hối và Quỹ Bình ổn tỷ giá và quản lý thị trường vàng;"
- **Hệ thống trả lời (Answer)**: "Tôi nghĩ vấn đề này cần áp dụng kiến thức chung về tài chính ngân hàng quốc tế hoặc tự phán đoán, không nhất thiết dựa vào văn bản được đưa ra."
- **Điểm số chi tiết**:
  - Context Precision: `0.5721`
  - Context Recall: `0.5371`
  - Faithfulness: `0.5094`
  - Answer Relevancy: `0.5784`
- **Phân tích nguyên nhân**:
- **Context Precision (0.5721 < 0.7)**: Các tài liệu được truy xuất chứa thông tin nhiễu, tài liệu thực sự liên quan không được xếp hạng ở các vị trí đầu.
- **Context Recall (0.5371 < 0.7)**: Ngữ cảnh được truy xuất bị thiếu hụt dữ liệu đầu vào cần thiết so với đáp án chuẩn.
- **Faithfulness (0.5094 < 0.7)**: Mô hình trả lời tự suy diễn hoặc bịa đặt thông tin (ảo tưởng/hallucination) không có trong ngữ cảnh.
- **Answer Relevancy (0.5784 < 0.7)**: Câu trả lời bị lạc đề hoặc không đi thẳng vào nội dung câu hỏi.



---

## 3. Đề xuất tối ưu hóa hệ thống (RAG Optimization Recommendations)

### 1. Nâng cao chỉ số Tìm kiếm (Context Recall & Context Precision)
- **Tăng giá trị `top_k`**: Nâng số lượng văn bản được truy xuất từ 5 lên 8 để tăng tỷ lệ bao phủ ngữ cảnh cần thiết.
- **Cải tiến Cross-Encoder Reranker**: Cấu hình lại hoặc sử dụng GPU để chạy mô hình Rerank sâu sắc thay vì difflib, giúp đẩy tài liệu thực sự liên quan lên thứ hạng đầu.
- **Tích hợp cơ chế Query Expansion**: Sử dụng LLM Generator viết lại câu hỏi người dùng thành nhiều câu tương đương để tối đa hóa độ tương đồng ngữ nghĩa.

### 2. Tối ưu hóa mô hình sinh câu trả lời (Faithfulness & Answer Relevancy)
- **Cập nhật Prompt System**: Tăng cường ràng buộc ép buộc mô hình Generator từ chối trả lời hoặc nói "Tôi không biết" nếu không tìm thấy thông tin trong ngữ cảnh.
- **Few-shot Prompting**: Đưa thêm ví dụ minh họa trực quan cấu trúc trả lời trong prompt để mô hình học tập phong cách trả lời trực tiếp.
- **Rút gọn và lọc nhiễu văn bản**: Lọc bỏ các ký tự thừa hoặc loại bỏ các câu ít liên quan trong ngữ cảnh trước khi đưa vào prompt của Generator.
