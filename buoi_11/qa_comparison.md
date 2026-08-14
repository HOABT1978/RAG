# Báo cáo so sánh Hiệu quả Đồ thị RAG Đa bước (Multi-hop Graph RAG)

*Ngày thực hiện: 2026-08-12 20:54:39*

Báo cáo này trình bày so sánh chi tiết chất lượng câu trả lời của LLM khi thay đổi số lượng bước nhảy ($N$) trong đồ thị RAG:
- **0 bước nhảy (N=0)**: Chỉ sử dụng tìm kiếm vector trực tiếp.
- **1 bước nhảy (N=1)**: Mở rộng ngữ cảnh sang các tài liệu liên kết trực tiếp.
- **2 bước nhảy (N=2)**: Mở rộng ngữ cảnh sang các tài liệu liên kết 2 tầng.


## Câu hỏi 1: Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?

| Số bước nhảy | Tài liệu ngữ cảnh được duyệt | Tóm tắt câu trả lời |
| --- | --- | --- |
| N=0 | 163441, 112025, 166269 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |
| N=1 | 166269, 168220, 112025, 163441 | ❌ Lỗi khi gọi Gemini API: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high... |
| N=2 | 166269, 168220, 112025, 163441 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |

### So sánh chi tiết nội dung trả lời:

````carousel
#### Kết quả với N=0 (Vector RAG trực tiếp)
**Tài liệu ngữ cảnh:** 163441, 112025, 166269

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
<!-- slide -->
#### Kết quả với N=1 (Graph RAG 1 bước nhảy)
**Tài liệu ngữ cảnh:** 166269, 168220, 112025, 163441

❌ Lỗi khi gọi Gemini API: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
<!-- slide -->
#### Kết quả với N=2 (Graph RAG 2 bước nhảy)
**Tài liệu ngữ cảnh:** 166269, 168220, 112025, 163441

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
````


========================================


## Câu hỏi 2: Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?

| Số bước nhảy | Tài liệu ngữ cảnh được duyệt | Tóm tắt câu trả lời |
| --- | --- | --- |
| N=0 | 163441, 173695, 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |
| N=1 | 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 112025, 163441, 173695 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |
| N=2 | 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 112025, 163441, 173695 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |

### So sánh chi tiết nội dung trả lời:

````carousel
#### Kết quả với N=0 (Vector RAG trực tiếp)
**Tài liệu ngữ cảnh:** 163441, 173695, 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
<!-- slide -->
#### Kết quả với N=1 (Graph RAG 1 bước nhảy)
**Tài liệu ngữ cảnh:** 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 112025, 163441, 173695

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
<!-- slide -->
#### Kết quả với N=2 (Graph RAG 2 bước nhảy)
**Tài liệu ngữ cảnh:** 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 112025, 163441, 173695

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
````


========================================


## Câu hỏi 3: Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?

| Số bước nhảy | Tài liệu ngữ cảnh được duyệt | Tóm tắt câu trả lời |
| --- | --- | --- |
| N=0 | 185630, 168220, 163441 | ❌ Lỗi khi gọi Gemini API: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high... |
| N=1 | 166269, 168220, 112025, 177271, 163441, 185630 | Căn cứ vào Ngữ cảnh được cung cấp, câu hỏi của bạn được giải đáp như sau:  **1. Văn bản sửa đổi, bổ sung Thông tư số 01/... |
| N=2 | 166269, 168220, 112025, 177271, 163441, 185630 | Dựa trên Ngữ cảnh được cung cấp, xin trả lời câu hỏi của bạn như sau:  1. **Văn bản sửa đổi, bổ sung:**    Thông tư số 0... |

### So sánh chi tiết nội dung trả lời:

````carousel
#### Kết quả với N=0 (Vector RAG trực tiếp)
**Tài liệu ngữ cảnh:** 185630, 168220, 163441

❌ Lỗi khi gọi Gemini API: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
<!-- slide -->
#### Kết quả với N=1 (Graph RAG 1 bước nhảy)
**Tài liệu ngữ cảnh:** 166269, 168220, 112025, 177271, 163441, 185630

Căn cứ vào Ngữ cảnh được cung cấp, câu hỏi của bạn được giải đáp như sau:

**1. Văn bản sửa đổi, bổ sung Thông tư số 01/2025/TT-NHNN:**
Thông tư số 01/2025/TT-NHNN (quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân) được sửa đổi, bổ sung bởi **Thông tư số 63/2025/TT-NHNN** ("Sửa đổi, bổ sung một số điều của một số Thông tư về quỹ tín dụng nhân dân"), cụ thể tại **Chương II** [ Context 1].

**2. Về các nội dung sửa đổi, bổ sung chính:**
Ngữ cảnh được cung cấp chỉ bao gồm tên/tiêu đề của **Chương II thuộc Thông tư số 63/2025/TT-NHNN** ("Sửa đổi, bổ sung một số điều của Thông tư số 01/2025/TT-NHNN quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân") mà không chứa các điều khoản chi tiết thể hiện nội dung sửa đổi, bổ sung cụ thể. 

Do đó, **ngữ cảnh được cung cấp không chứa đủ thông tin để trả lời chi tiết về các nội dung sửa đổi, bổ sung cụ thể này.**
<!-- slide -->
#### Kết quả với N=2 (Graph RAG 2 bước nhảy)
**Tài liệu ngữ cảnh:** 166269, 168220, 112025, 177271, 163441, 185630

Dựa trên Ngữ cảnh được cung cấp, xin trả lời câu hỏi của bạn như sau:

1. **Văn bản sửa đổi, bổ sung:**
   Thông tư số 01/2025/TT-NHNN quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi **Thông tư số 63/2025/TT-NHNN** (*Sửa đổi, bổ sung một số điều của một số Thông tư về quỹ tín dụng nhân dân*), cụ thể tại **Chương II** [Trích dẫn 1].

2. **Nội dung sửa đổi, bổ sung chính:**
   Ngữ cảnh được cung cấp chỉ đề cập tên Chương II của Thông tư số 63/2025/TT-NHNN về việc *"Sửa đổi, bổ sung một số điều của Thông tư số 01/2025/TT-NHNN quy định về cấp Giấy phép lần đầu, cấp đổi Giấy phép của quỹ tín dụng nhân dân"* [Trích dẫn 1], **không chứa thông tin chi tiết về các nội dung sửa đổi, bổ sung cụ thể**.
````


========================================


## Câu hỏi 4: Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?

| Số bước nhảy | Tài liệu ngữ cảnh được duyệt | Tóm tắt câu trả lời |
| --- | --- | --- |
| N=0 | 168220, 44209, 166269 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |
| N=1 | 44209, 166269, 168220, 169221 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |
| N=2 | 44209, 166269, 168220, 169221 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |

### So sánh chi tiết nội dung trả lời:

````carousel
#### Kết quả với N=0 (Vector RAG trực tiếp)
**Tài liệu ngữ cảnh:** 168220, 44209, 166269

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
<!-- slide -->
#### Kết quả với N=1 (Graph RAG 1 bước nhảy)
**Tài liệu ngữ cảnh:** 44209, 166269, 168220, 169221

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
<!-- slide -->
#### Kết quả với N=2 (Graph RAG 2 bước nhảy)
**Tài liệu ngữ cảnh:** 44209, 166269, 168220, 169221

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
````


========================================


## Câu hỏi 5: Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?

| Số bước nhảy | Tài liệu ngữ cảnh được duyệt | Tóm tắt câu trả lời |
| --- | --- | --- |
| N=0 | 174218, 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 173695, 112025 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |
| N=1 | 112025, 174218, 25692, 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 173695, 163441 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |
| N=2 | 117310, 112025, 174218, 25692, 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 173695, 163441 | Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.... |

### So sánh chi tiết nội dung trả lời:

````carousel
#### Kết quả với N=0 (Vector RAG trực tiếp)
**Tài liệu ngữ cảnh:** 174218, 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 173695, 112025

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
<!-- slide -->
#### Kết quả với N=1 (Graph RAG 1 bước nhảy)
**Tài liệu ngữ cảnh:** 112025, 174218, 25692, 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 173695, 163441

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
<!-- slide -->
#### Kết quả với N=2 (Graph RAG 2 bước nhảy)
**Tài liệu ngữ cảnh:** 117310, 112025, 174218, 25692, 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793, 173695, 163441

Ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi này.
````


========================================
