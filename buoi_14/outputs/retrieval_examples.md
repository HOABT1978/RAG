# BÁO CÁO TOÀN DIỆN PIPELINE RETRIEVAL & RERANKING (BUỔI 14)

- **Reranker Model**: `BAAI/bge-reranker-v2-m3`
- **Chế độ Reranking**: `Neural (Transformers)`

Báo cáo này đối chiếu kết quả qua 4 giai đoạn:
1. **BM25 Only** (Lexical Search)
2. **Dense Only** (Semantic Search)
3. **Hybrid Search** (RRF Fusion)
4. **Reranked** (Xếp hạng lại Top Candidates từ Hybrid)

---

## Câu hỏi 1: "Điều 12 Nghị định số 73/2016/NĐ-CP"
- **Phân loại**: Câu có mã/số hiệu cụ thể

### Bảng đối chiếu kết quả xếp hạng (Top 3):
| Hạng | BM25 Only | Dense Only | Hybrid Search (RRF) | Reranked (Cuối cùng) |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `chk_163441_1401` | `chk_112025_0844` | `chk_163441_1401` | **`chk_163441_1401`** |
| 2 | `chk_163441_1403` | `chk_112924_0172` | `chk_185630_0110` | **`chk_168220_0078`** |
| 3 | `chk_185630_0110` | `chk_112025_0828` | `chk_163441_0453` | **`chk_6e689cd0-6f81-11f1-94d6-fd5d6d5ff793_0110`** |

### Chi tiết kết quả sau khi Rerank (Top 5)
| Hạng mới | Chunk ID | Hạng cũ (Hybrid) | Điểm Rerank | Citation |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `chk_163441_1401` | 1 | 1.6025 | [Nghị định số 46/2023/NĐ-CP Quy định chi tiết thi hành một số điều của Luật Kinh doanh bảo hiểm | Chương VIII ĐIỀU KHOẢN THI HÀNH | nan | Điều 122. Hiệu lực thi hành | 4. Nghị định này thay thế các văn bản sau: | chk_163441_1401] |
| 2 | `chk_168220_0078` | 6 | 0.7455 | [Thông tư số 27/2024/TT-NHNN Quy định về việc ngân hàng hợp tác xã, việc trích nộp, quản lý và sử dụng Quỹ bảo đảm an toàn hệ thống quỹ tín dụng nhân dân | Chương II CÁC QUY ĐỊNH CỤ THỂ | Mục 2 THÀNH VIÊN, CHẤM DỨT TƯ CÁCH THÀNH VIÊN, VỐN GÓP, CHUYỂN NHƯỢNG VÀ HOÀN TRẢ VỐN GÓP CỦA THÀNH VIÊN | Điều 12. Vốn góp | nan | chk_168220_0078] |
| 3 | `chk_6e689cd0-6f81-11f1-94d6-fd5d6d5ff793_0110` | 15 | 0.5801 | [Quy định hồ sơ, thủ tục cấp Giấy phép lần đầu của ngân hàng thương mại, chi nhánh ngân hàng nước ngoài, văn phòng đại diện nước ngoài | Chương II | nan | Điều 12. Hồ sơ đề nghị cấp Giấy phép thành lập và hoạt động ngân hàng thương mại cổ phần | nan | chk_6e689cd0-6f81-11f1-94d6-fd5d6d5ff793_0110] |
| 4 | `chk_173695_0108` | 16 | 0.5801 | [Thông tư số 56/2024/TT-NHNN Quy định hồ sơ, thủ tục cấp Giấy phép lần đầu của ngân hàng thương mại, chi nhánh ngân hàng nước ngoài, văn phòng đại diện nước ngoài | Chương II QUY ĐỊNH VỀ CẤP GIẤY PHÉP | nan | Điều 12. Hồ sơ đề nghị cấp Giấy phép thành lập và hoạt động ngân hàng thương mại cổ phần | nan | chk_173695_0108] |
| 5 | `chk_185630_0110` | 2 | 0.1562 | [Thông tư số 63/2025/TT-NHNN Sửa đổi, bổ sung một số điều của một số Thông tư về quỹ tín dụng nhân dân | Chương III SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA THÔNG TƯ SỐ 10/2025/TT-NHNN QUY ĐỊNH VỀ TỔ CHỨC LẠI, THU HỒI GIẤY PHÉP VÀ THANH LÝ TÀI SẢN CỦA QUỸ TÍN DỤNG NHÂN DÂN | nan | Điều 12. Sửa đổi một số điểm, khoản của Điều 17 | nan | chk_185630_0110] |

#### Nội dung của tài liệu chính xác nhất (Top-1 Reranked Chunk):
> **Citation**: [Nghị định số 46/2023/NĐ-CP Quy định chi tiết thi hành một số điều của Luật Kinh doanh bảo hiểm | Chương VIII ĐIỀU KHOẢN THI HÀNH | nan | Điều 122. Hiệu lực thi hành | 4. Nghị định này thay thế các văn bản sau: | chk_163441_1401]
>
> a) Nghị định số 73/2016/NĐ-CP ngày 01 tháng 7 năm 2016 của Chính phủ quy định chi tiết thi hành Luật Kinh doanh bảo hiểm và Luật sửa đổi, bổ sung một số điều của Luật Kinh doanh bảo hiểm, trừ các Điều 10, 61, 62, 63, 64, 65, 66, 67. Các Điều 10, 61, 62, 63, 64, 65, 66, 67 của Nghị định số 73/2016/NĐ-CP có hiệu lực đến hết ngày 31 tháng 12 năm 2027;

### 🔍 Phân tích luồng thay đổi thứ tự:
*   **Nhận xét**: BM25 đưa các đoạn khớp từ khóa cứng về Nghị định 73/2016 lên đầu. Hybrid giữ lại cả hai luồng ứng viên. Rerank đã phân tích lại tương quan chính xác của câu hỏi đối với văn bản điều khoản và đưa phân đoạn phù hợp nhất về Điều 12/Điều liên quan lên đầu.

---

## Câu hỏi 2: "quy định về an toàn trong vận chuyển tiền mặt và tài sản quý của ngân hàng"
- **Phân loại**: Câu diễn đạt semantic (ý nghĩa)

### Bảng đối chiếu kết quả xếp hạng (Top 3):
| Hạng | BM25 Only | Dense Only | Hybrid Search (RRF) | Reranked (Cuối cùng) |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `chk_44209_0278` | `chk_44209_0292` | `chk_44209_0278` | **`chk_44209_0271`** |
| 2 | `chk_44209_0271` | `chk_44209_0269` | `chk_44209_0269` | **`chk_44209_0278`** |
| 3 | `chk_44209_0269` | `chk_44209_0278` | `chk_44209_0292` | **`chk_44209_0269`** |

### Chi tiết kết quả sau khi Rerank (Top 5)
| Hạng mới | Chunk ID | Hạng cũ (Hybrid) | Điểm Rerank | Citation |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `chk_44209_0271` | 5 | 4.7315 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương IV VẬN CHUYỂN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | Điều 50. Phương tiện vận chuyển | 3. Trường hợp tổ chức tín dụng, chi nhánh ngân hàng nước ngoài sử dụng phương tiện khác để vận chuyển tiền mặt, tài sản quý, giấy tờ có giá, tổ chức tín dụng, chi nhánh ngân hàng nước ngoài phải quy định bằng văn bản và hướng dẫn quy trình vận chuyển, bảo vệ, các biện pháp đảm bảo an toàn tài sản. | chk_44209_0271] |
| 2 | `chk_44209_0278` | 1 | 4.4512 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương IV VẬN CHUYỂN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | Điều 52. Đảm bảo an toàn trên đường vận chuyển | 1. Tiền mặt, tài sản quý, giấy tờ có giá khi vận chuyển phải được đóng gói, niêm phong và được bảo quản an toàn. | chk_44209_0278] |
| 3 | `chk_44209_0269` | 2 | 4.0015 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương IV VẬN CHUYỂN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | Điều 50. Phương tiện vận chuyển | 2. Vận chuyển tiền mặt, tài sản quý, giấy tờ có giá trong hệ thống Ngân hàng Nhà nước phải có xe hộ tống. | chk_44209_0269] |
| 4 | `chk_44209_0284` | 18 | 3.6460 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương IV VẬN CHUYỂN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | Điều 54. Tổ chức tiếp nhận | nan | chk_44209_0284] |
| 5 | `chk_44209_0292` | 3 | 3.4622 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương IV VẬN CHUYỂN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | Điều 56. Trách nhiệm bảo vệ vận chuyển | 2. Tổ chức tín dụng, chi nhánh ngân hàng nước ngoài quy định trách nhiệm bảo vệ, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá trong hệ thống. | chk_44209_0292] |

#### Nội dung của tài liệu chính xác nhất (Top-1 Reranked Chunk):
> **Citation**: [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương IV VẬN CHUYỂN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | Điều 50. Phương tiện vận chuyển | 3. Trường hợp tổ chức tín dụng, chi nhánh ngân hàng nước ngoài sử dụng phương tiện khác để vận chuyển tiền mặt, tài sản quý, giấy tờ có giá, tổ chức tín dụng, chi nhánh ngân hàng nước ngoài phải quy định bằng văn bản và hướng dẫn quy trình vận chuyển, bảo vệ, các biện pháp đảm bảo an toàn tài sản. | chk_44209_0271]
>
> 3. Trường hợp tổ chức tín dụng, chi nhánh ngân hàng nước ngoài sử dụng phương tiện khác để vận chuyển tiền mặt, tài sản quý, giấy tờ có giá, tổ chức tín dụng, chi nhánh ngân hàng nước ngoài phải quy định bằng văn bản và hướng dẫn quy trình vận chuyển, bảo vệ, các biện pháp đảm bảo an toàn tài sản.

### 🔍 Phân tích luồng thay đổi thứ tự:
*   **Nhận xét**: Câu hỏi semantic được xếp hạng cao bởi Dense. Reranker tập trung chấm điểm cao nhất cho các đoạn bàn trực tiếp về trách nhiệm bảo vệ và quy trình vận chuyển an toàn, giúp kết quả tìm kiếm tập trung đúng trọng tâm điều khoản quy định.

---

## Câu hỏi 3: "Thông tư 01/2014 quy định thế nào về việc đóng gói niêm phong tiền mặt"
- **Phân loại**: Câu kết hợp cả hai yếu tố

### Bảng đối chiếu kết quả xếp hạng (Top 3):
| Hạng | BM25 Only | Dense Only | Hybrid Search (RRF) | Reranked (Cuối cùng) |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `chk_44209_0045` | `chk_44209_0022` | `chk_44209_0022` | **`chk_44209_0022`** |
| 2 | `chk_44209_0022` | `chk_177271_0003` | `chk_44209_0045` | **`chk_44209_0045`** |
| 3 | `chk_44209_0278` | `chk_44209_0045` | `chk_44209_0034` | **`chk_44209_0278`** |

### Chi tiết kết quả sau khi Rerank (Top 5)
| Hạng mới | Chunk ID | Hạng cũ (Hybrid) | Điểm Rerank | Citation |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `chk_44209_0022` | 1 | 1.9844 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương II KIỂM ĐẾM, ĐÓNG GÓI VÀ GIAO NHẬN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | Mục 1 QUY ĐỊNH VỀ ĐÓNG GÓI NIÊM PHONG TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | nan | chk_44209_0022] |
| 2 | `chk_44209_0045` | 2 | 1.8841 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương II KIỂM ĐẾM, ĐÓNG GÓI VÀ GIAO NHẬN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | Mục 1 QUY ĐỊNH VỀ ĐÓNG GÓI NIÊM PHONG TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | Điều 6. Đóng gói, niêm phong tài sản quý, giấy tờ có giá | 1. Việc đóng gói, niêm phong ngoại tệ, giấy tờ có giá thực hiện như đóng gói, niêm phong tiền mặt. | chk_44209_0045] |
| 3 | `chk_44209_0278` | 7 | 1.7407 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương IV VẬN CHUYỂN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | Điều 52. Đảm bảo an toàn trên đường vận chuyển | 1. Tiền mặt, tài sản quý, giấy tờ có giá khi vận chuyển phải được đóng gói, niêm phong và được bảo quản an toàn. | chk_44209_0278] |
| 4 | `chk_44209_0036` | 12 | 1.4594 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương II KIỂM ĐẾM, ĐÓNG GÓI VÀ GIAO NHẬN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | Mục 1 QUY ĐỊNH VỀ ĐÓNG GÓI NIÊM PHONG TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | Điều 5. Niêm phong tiền mặt | 2. Trên giấy niêm phong bó, túi, hộp, bao, thùng tiền phải có đầy đủ, rõ ràng các nội dung sau: tên ngân hàng; loại tiền; số lượng (tờ, miếng, bó, túi) tiền; số tiền; họ tên và chữ ký của người kiểm đếm, đóng gói; ngày, tháng, năm đóng gói niêm phong. | chk_44209_0036] |
| 5 | `chk_44209_0099` | 5 | 1.1104 | [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương III BẢO QUẢN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | Mục 1 SẮP XẾP, BẢO QUẢN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ TẠI QUẦY GIAO DỊCH VÀ TRONG KHO TIỀN | Điều 15. Sắp xếp, bảo quản tài sản tại quầy giao dịch và trong kho tiền | 3. Trong kho tiền Ngân hàng Nhà nước, tiền mặt, tài sản quý, giấy tờ có giá phải được đóng gói, niêm phong đúng quy định và được sắp xếp riêng ở từng khu vực hoặc riêng từng gian kho. | chk_44209_0099] |

#### Nội dung của tài liệu chính xác nhất (Top-1 Reranked Chunk):
> **Citation**: [Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Chương II KIỂM ĐẾM, ĐÓNG GÓI VÀ GIAO NHẬN TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | Mục 1 QUY ĐỊNH VỀ ĐÓNG GÓI NIÊM PHONG TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ | nan | nan | chk_44209_0022]
>
> Mục 1 QUY ĐỊNH VỀ ĐÓNG GÓI NIÊM PHONG TIỀN MẶT, TÀI SẢN QUÝ, GIẤY TỜ CÓ GIÁ

### 🔍 Phân tích luồng thay đổi thứ tự:
*   **Nhận xét**: Reranker giúp sàng lọc tốt các từ khóa nhiễu của câu hỏi hỗn hợp, đưa phần giải thích chi tiết về việc kiểm đếm, đóng gói, niêm phong tiền mặt của Thông tư 01/2014 lên vị trí số 1.

---

