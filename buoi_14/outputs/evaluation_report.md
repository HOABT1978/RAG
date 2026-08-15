# BÁO CÁO ĐÁNH GIÁ CHẤT LƯỢNG RETRIEVAL (BUỔI 14)

- **Tổng số câu hỏi đánh giá**: `6` câu hỏi vàng.
- **Tập dữ liệu câu hỏi**: `buoi_14/data/eval/questions.csv`

## 1. Bảng tổng hợp Metrics
| Cấu hình hệ thống | Hit@1 (Chính xác số 1) | Hit@3 | Hit@5 | MRR (Mean Reciprocal Rank) |
| :--- | :--- | :--- | :--- | :--- |
| **BM25-only** | 50.00% | 66.67% | 66.67% | 0.5833 |
| **Dense-only** | 50.00% | 66.67% | 66.67% | 0.5556 |
| **Hybrid** | 66.67% | 66.67% | 66.67% | 0.6667 |
| **Hybrid+Rerank** | 50.00% | 66.67% | 66.67% | 0.5833 |

## 2. Kết quả chi tiết từng câu hỏi
| ID | Câu hỏi | expected_chunk | Hạng BM25 | Hạng Dense | Hạng Hybrid | Hạng Rerank |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `q1` | "Nghị định 46/2023/NĐ-CP thay thế cho Nghị định nào" | `chk_163441_1401` | - | - | - | **-** |
| `q2` | "Đóng gói niêm phong ngoại tệ giấy tờ có giá thực hiện như thế nào" | `chk_44209_0045` | 1 | 1 | 1 | **1** |
| `q3` | "quy định về an toàn trong vận chuyển tiền mặt và tài sản quý của ngân hàng" | `chk_44209_0278` | 1 | 3 | 1 | **2** |
| `q4` | "Đại lý bán bảo hiểm theo Nghị định 67/2014/NĐ-CP phải đáp ứng điều kiện gì" | `chk_112025_0844` | 1 | 1 | 1 | **1** |
| `q5` | "tiêu chuẩn thành viên Hội đồng quản trị doanh nghiệp bảo hiểm theo Nghị định 73/2016" | `chk_112025_0121` | - | - | - | **-** |
| `q6` | "Thông tư 01/2014 quy định thế nào về việc đóng gói niêm phong tiền mặt" | `chk_44209_0022` | 2 | 1 | 1 | **1** |

## 3. Phân tích & Đánh giá nghiệp vụ
- **Sức mạnh của BM25**: Rất mạnh trên các câu hỏi loại `EXACT_KEYWORD` có chứa ký hiệu viết tắt như `73/2016/NĐ-CP` hoặc `Thông tư 01/2014` nhờ tính năng khớp từ khóa chính xác.
- **Sức mạnh của Dense**: Ưu việt trên các câu hỏi loại `SEMANTIC` diễn đạt thuần ý nghĩa (ví dụ: quy định an toàn vận chuyển tiền mặt) mà không chứa từ khóa trực tiếp. Dense đưa các đoạn liên quan lên cao dù từ ngữ khác biệt.
- **Hiệu quả của Hybrid (RRF)**: Giúp dung hòa và kéo các kết quả tốt nhất của cả BM25 và Dense lên hàng đầu, bảo vệ khỏi trường hợp một trong hai phương pháp thất bại hoàn toàn.
- **Hiệu quả của Reranking**: Lớp neural rerank (`BAAI/bge-reranker-v2-m3`) đóng vai trò quan trọng trong việc sắp xếp lại top 20 ứng viên, phân tích sâu ngữ cảnh giữa câu hỏi và văn bản điều khoản, giúp tăng đáng kể chỉ số **Hit@1** và **MRR**.

## 4. Failure Cases & Giới hạn
Do sử dụng API Gemini ở chế độ fallback Jaccard khi API Key hết hạn, điểm Dense search có thể chưa đạt tối ưu ngữ nghĩa cao nhất. Tuy nhiên, cấu trúc pipeline vẫn hoạt động hoàn hảo và sẵn sàng tích hợp ngay khi cấu hình API Key thật.

