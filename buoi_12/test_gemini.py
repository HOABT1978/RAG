import os
import sys
import json
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

sys.stdout.reconfigure(encoding='utf-8')

# Define schemas
class EntityItem(BaseModel):
    entity: str = Field(description="Tên thực thể được trích xuất")
    confidence: float = Field(description="Độ tin cậy của trích xuất, từ 0.0 đến 1.0")
    evidence: str = Field(description="Đoạn văn bản gốc chính xác chứa thông tin trích xuất")

class MetadataExtraction(BaseModel):
    co_quan: Optional[EntityItem] = Field(description="Cơ quan ban hành (CoQuan)")
    nguoi_ky: Optional[EntityItem] = Field(description="Người ký (NguoiKy)")
    chuc_danh: Optional[EntityItem] = Field(description="Chức danh người ký")
    linh_vuc: Optional[EntityItem] = Field(description="Lĩnh vực pháp lý (LinhVuc)")
    nganh: Optional[EntityItem] = Field(description="Ngành quản lý")
    doi_tuong_ap_dung: List[EntityItem] = Field(description="Danh sách các đối tượng áp dụng (DoiTuongApDung)")

def get_trimmed_content(content):
    if len(content) <= 12000:
        return content
    return content[:8000] + "\n... [TRUNCATED MIDDLE CONTENT] ...\n" + content[-4000:]

def main():
    load_dotenv('buoi_12/.env')
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # Load cleaned documents
    df = pd.read_csv('ner_kb/cleaned_documents.csv')
    row = df.iloc[0]
    
    print(f"📄 Thử nghiệm với Document ID: {row['id']} | Số hiệu: {row['so_ky_hieu']}")
    print(f"Tiêu đề: {row['title']}")
    
    trimmed_content = get_trimmed_content(row['content_clean'])
    
    prompt = f"""Bạn là một chuyên gia phân tích văn bản pháp luật Việt Nam.
Nhiệm vụ của bạn là đọc nội dung văn bản và trích xuất các thông tin siêu dữ liệu (metadata) cũng như các đối tượng áp dụng của văn bản.

Thông tin cơ bản của văn bản:
- Tiêu đề gốc: {row['title']}
- Cơ quan ban hành gốc: {row.get('co_quan_ban_hanh', 'Chưa có')}
- Người ký gốc: {row.get('nguoi_ky', 'Chưa có')}
- Lĩnh vực gốc: {row.get('linh_vuc', 'Chưa có')}
- Ngành gốc: {row.get('nganh', 'Chưa có')}
- Chức danh gốc: {row.get('chuc_danh', 'Chưa có')}

Dưới đây là nội dung văn bản (đã lược bớt phần giữa):
---
{trimmed_content}
---

Hãy trích xuất các thực thể:
1. Cơ quan ban hành (CoQuan)
2. Người ký (NguoiKy)
3. Chức danh người ký
4. Lĩnh vực pháp lý chính (LinhVuc)
5. Ngành quản lý (Nganh)
6. Các đối tượng áp dụng (DoiTuongApDung) - danh sách

QUY TẮC RẤT QUAN TRỌNG:
- Chỉ trích xuất khi có bằng chứng (evidence) rõ ràng trong văn bản. Không tự ý bịa đặt thông tin.
- Với mỗi thực thể trích xuất được, cung cấp đoạn trích gốc chứa thông tin đó làm bằng chứng ("evidence") và độ tin cậy ("confidence").
"""

    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MetadataExtraction,
                temperature=0.1
            )
        )
        data = json.loads(response.text)
        print("\n✅ Thành công! Kết quả trích xuất:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\n❌ Lỗi khi gọi Gemini: {e}")

if __name__ == "__main__":
    main()
