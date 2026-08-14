import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

# Define schemas for structured output
class EntityItem(BaseModel):
    entity: str = Field(description="Tên thực thể được trích xuất (viết hoa các chữ cái đầu hoặc viết đúng tên riêng)")
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
    """Trims content to keep start and end sections, optimizing context window and token usage."""
    if len(content) <= 15000:
        return content
    return content[:10000] + "\n... [TRUNCATED MIDDLE CONTENT] ...\n" + content[-5000:]

def is_missing_or_unclassified(val):
    """Checks if a metadata value is NaN, empty, or unclassified."""
    if pd.isna(val):
        return True
    s = str(val).strip()
    return s == "" or s.lower() == "chưa phân loại" or s.lower() == "null" or s.lower() == "none"

def generate_content_with_retry(client, model, prompt, config, max_retries=5, initial_delay=35):
    """Generates content with retry and exponential backoff on 429 rate limit errors."""
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            return response
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt < max_retries:
                    print(f"⚠️ Hết quota/Rate limit (429). Chi tiết lỗi: {err_str}", flush=True)
                    print(f"⌛ Đang đợi {delay} giây trước khi thử lại (Lần thử {attempt + 1}/{max_retries})...", flush=True)
                    time.sleep(delay)
                    delay = int(delay * 1.5)
                    continue
            raise e

def main():
    print("==================================================", flush=True)
    print("🤖 BƯỚC 3: ENTITY EXTRACTION & METADATA ENRICHMENT", flush=True)
    print("==================================================", flush=True)
    
    root_dir = Path(__file__).resolve().parents[1]
    input_path = root_dir / "ner_kb" / "cleaned_documents.csv"
    entities_out_path = root_dir / "ner_kb" / "extracted_entities_raw.csv"
    metadata_out_path = root_dir / "ner_kb" / "enriched_metadata.csv"
    
    if not input_path.exists():
        print(f"❌ Không tìm thấy file cleaned_documents.csv tại: {input_path}", flush=True)
        sys.exit(1)
        
    load_dotenv(root_dir / "buoi_12" / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
        
    if not api_key:
        print("❌ Không tìm thấy GEMINI_API_KEY trong file .env.", flush=True)
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    print(f"📖 Đang đọc {input_path.name}...", flush=True)
    df_docs = pd.read_csv(input_path)
    
    # Select only metadata.csv columns for enriched_metadata.csv
    metadata_cols = [
        'id', 'title', 'so_ky_hieu', 'ngay_ban_hanh', 'loai_van_ban', 'ngay_co_hieu_luc',
        'ngay_het_hieu_luc', 'nguon_thu_thap', 'ngay_dang_cong_bao', 'nganh', 'linh_vuc',
        'co_quan_ban_hanh', 'chuc_danh', 'nguoi_ky', 'pham_vi', 'thong_tin_ap_dung', 'tinh_trang_hieu_luc'
    ]
    df_enriched = df_docs[metadata_cols].copy()
    
    # Cast all enrichment columns to object type to prevent float64 assignment errors
    cols_to_enrich = ["co_quan_ban_hanh", "nguoi_ky", "linh_vuc", "nganh", "chuc_danh", "thong_tin_ap_dung"]
    for col in cols_to_enrich:
        df_enriched[col] = df_enriched[col].astype(object)
        
    # Initialize the output CSV files on disk before starting
    # This prevents them from being empty if the script is interrupted early
    pd.DataFrame(columns=["source_doc_id", "entity", "entity_type", "source", "method", "confidence", "evidence"]).to_csv(entities_out_path, index=False, encoding='utf-8')
    df_enriched.to_csv(metadata_out_path, index=False, encoding='utf-8')
    
    all_raw_entities = []
    success_docs = 0
    fail_docs = 0
    failures_log = []
    
    enriched_counters = {
        "co_quan_ban_hanh": 0,
        "nguoi_ky": 0,
        "linh_vuc": 0,
        "nganh": 0,
        "chuc_danh": 0,
        "thong_tin_ap_dung": 0
    }
    
    comparison_data = [] # To display examples later
    total_docs = len(df_docs)
    
    for i, row in df_docs.iterrows():
        doc_id = row['id']
        title = row['title']
        so_ky_hieu = row['so_ky_hieu']
        content = row['content_clean']
        
        print(f"🔄 [{i+1}/{total_docs}] Đang xử lý ID: {doc_id} | Số hiệu: {so_ky_hieu}...", flush=True)
        
        trimmed_content = get_trimmed_content(content)
        
        prompt = f"""Bạn là một chuyên gia phân tích văn bản pháp luật Việt Nam.
Nhiệm vụ của bạn là đọc nội dung văn bản và trích xuất các thông tin siêu dữ liệu (metadata) cũng như các đối tượng áp dụng của văn bản.

Thông tin cơ bản của văn bản:
- Tiêu đề gốc: {title}
- Cơ quan ban hành gốc: {row.get('co_quan_ban_hanh', 'Chưa có')}
- Người ký gốc: {row.get('nguoi_ky', 'Chưa có')}
- Lĩnh vực gốc: {row.get('linh_vuc', 'Chưa có')}
- Ngành gốc: {row.get('nganh', 'Chưa có')}
- Chức danh gốc: {row.get('chuc_danh', 'Chưa có')}

Dưới đây là một phần nội dung văn bản (đã được lược bớt phần giữa nếu quá dài):
---
{trimmed_content}
---

Hãy trích xuất các thực thể sau từ nội dung văn bản:
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
            # 7s delay between requests to stay below RPM limit
            time.sleep(7)
            
            response = generate_content_with_retry(
                client=client,
                model='gemini-3.5-flash-lite',
                prompt=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MetadataExtraction,
                    temperature=0.1
                )
            )
            
            result = json.loads(response.text)
            success_docs += 1
            
            # Extract lists of entities for extracted_entities_raw.csv
            extracted_items = []
            
            # Map CoQuan
            if result.get("co_quan") and result["co_quan"].get("entity"):
                item = result["co_quan"]
                extracted_items.append((item["entity"], "CoQuan", item.get("confidence", 1.0), item.get("evidence", "")))
                
            # Map NguoiKy
            if result.get("nguoi_ky") and result["nguoi_ky"].get("entity"):
                item = result["nguoi_ky"]
                extracted_items.append((item["entity"], "NguoiKy", item.get("confidence", 1.0), item.get("evidence", "")))
                
            # Map LinhVuc
            if result.get("linh_vuc") and result["linh_vuc"].get("entity"):
                item = result["linh_vuc"]
                extracted_items.append((item["entity"], "LinhVuc", item.get("confidence", 1.0), item.get("evidence", "")))
                
            # Map DoiTuongApDung
            if result.get("doi_tuong_ap_dung"):
                for item in result["doi_tuong_ap_dung"]:
                    if item.get("entity"):
                        extracted_items.append((item["entity"], "DoiTuongApDung", item.get("confidence", 1.0), item.get("evidence", "")))
                        
            # Map ChucDanh and Nganh to save as raw entities too
            if result.get("chuc_danh") and result["chuc_danh"].get("entity"):
                item = result["chuc_danh"]
                extracted_items.append((item["entity"], "ChucDanh", item.get("confidence", 1.0), item.get("evidence", "")))
            if result.get("nganh") and result["nganh"].get("entity"):
                item = result["nganh"]
                extracted_items.append((item["entity"], "Nganh", item.get("confidence", 1.0), item.get("evidence", "")))
                
            # Append to master entities list
            doc_entities = []
            for ent, ent_type, conf, ev in extracted_items:
                entity_dict = {
                    "source_doc_id": doc_id,
                    "entity": ent,
                    "entity_type": ent_type,
                    "source": "content_clean",
                    "method": "gemini",
                    "confidence": conf,
                    "evidence": ev
                }
                all_raw_entities.append(entity_dict)
                doc_entities.append(entity_dict)
                
            # Incremental save of raw entities
            if doc_entities:
                pd.DataFrame(doc_entities).to_csv(entities_out_path, mode='a', header=False, index=False, encoding='utf-8')
                
            # --- Perform Metadata Enrichment ---
            orig_co_quan = row.get('co_quan_ban_hanh')
            orig_nguoi_ky = row.get('nguoi_ky')
            orig_linh_vuc = row.get('linh_vuc')
            orig_nganh = row.get('nganh')
            orig_chuc_danh = row.get('chuc_danh')
            orig_ap_dung = row.get('thong_tin_ap_dung')
            
            new_co_quan = orig_co_quan
            new_nguoi_ky = orig_nguoi_ky
            new_linh_vuc = orig_linh_vuc
            new_nganh = orig_nganh
            new_chuc_danh = orig_chuc_danh
            new_ap_dung = orig_ap_dung
            
            # Enrich only if missing or unclassified
            if is_missing_or_unclassified(orig_co_quan) and result.get("co_quan") and result["co_quan"].get("entity"):
                new_co_quan = result["co_quan"]["entity"]
                enriched_counters["co_quan_ban_hanh"] += 1
                
            if is_missing_or_unclassified(orig_nguoi_ky) and result.get("nguoi_ky") and result["nguoi_ky"].get("entity"):
                new_nguoi_ky = result["nguoi_ky"]["entity"]
                enriched_counters["nguoi_ky"] += 1
                
            if is_missing_or_unclassified(orig_linh_vuc) and result.get("linh_vuc") and result["linh_vuc"].get("entity"):
                new_linh_vuc = result["linh_vuc"]["entity"]
                enriched_counters["linh_vuc"] += 1
                
            if is_missing_or_unclassified(orig_nganh) and result.get("nganh") and result["nganh"].get("entity"):
                new_nganh = result["nganh"]["entity"]
                enriched_counters["nganh"] += 1
                
            if is_missing_or_unclassified(orig_chuc_danh) and result.get("chuc_danh") and result["chuc_danh"].get("entity"):
                new_chuc_danh = result["chuc_danh"]["entity"]
                enriched_counters["chuc_danh"] += 1
                
            if is_missing_or_unclassified(orig_ap_dung) and result.get("doi_tuong_ap_dung"):
                subjects = [item["entity"] for item in result["doi_tuong_ap_dung"] if item.get("entity")]
                if subjects:
                    new_ap_dung = "; ".join(subjects)
                    enriched_counters["thong_tin_ap_dung"] += 1
            
            # Apply to df_enriched
            df_enriched.loc[df_enriched['id'] == doc_id, 'co_quan_ban_hanh'] = new_co_quan
            df_enriched.loc[df_enriched['id'] == doc_id, 'nguoi_ky'] = new_nguoi_ky
            df_enriched.loc[df_enriched['id'] == doc_id, 'linh_vuc'] = new_linh_vuc
            df_enriched.loc[df_enriched['id'] == doc_id, 'nganh'] = new_nganh
            df_enriched.loc[df_enriched['id'] == doc_id, 'chuc_danh'] = new_chuc_danh
            df_enriched.loc[df_enriched['id'] == doc_id, 'thong_tin_ap_dung'] = new_ap_dung
            
            # Save enriched metadata incrementally
            df_enriched.to_csv(metadata_out_path, index=False, encoding='utf-8')
            
            # Track comparison data for reporting
            was_enriched = (new_co_quan != orig_co_quan or new_nguoi_ky != orig_nguoi_ky or
                            new_linh_vuc != orig_linh_vuc or new_nganh != orig_nganh or
                            new_chuc_danh != orig_chuc_danh or new_ap_dung != orig_ap_dung)
            
            if was_enriched or len(comparison_data) < 5:
                comparison_data.append({
                    "id": doc_id,
                    "so_ky_hieu": so_ky_hieu,
                    "orig": {
                        "co_quan_ban_hanh": orig_co_quan,
                        "nguoi_ky": orig_nguoi_ky,
                        "linh_vuc": orig_linh_vuc,
                        "nganh": orig_nganh,
                        "thong_tin_ap_dung": str(orig_ap_dung)[:50] + "..." if orig_ap_dung else "None"
                    },
                    "enriched": {
                        "co_quan_ban_hanh": new_co_quan,
                        "nguoi_ky": new_nguoi_ky,
                        "linh_vuc": new_linh_vuc,
                        "nganh": new_nganh,
                        "thong_tin_ap_dung": str(new_ap_dung)[:50] + "..." if new_ap_dung else "None"
                    }
                })
                
        except Exception as e:
            fail_docs += 1
            err_msg = f"Lỗi ở Document ID {doc_id} ({so_ky_hieu}): {str(e)}"
            print(f"❌ {err_msg}", flush=True)
            failures_log.append(err_msg)
            
    # --- Print statistics as requested ---
    print("\n" + "="*50, flush=True)
    print("📊 THỐNG KÊ KẾT QUẢ BƯỚC 3:", flush=True)
    print("="*50, flush=True)
    print(f"🔹 Số document xử lý thành công: {success_docs}", flush=True)
    print(f"🔹 Số document xử lý thất bại:   {fail_docs}", flush=True)
    
    if success_docs > 0:
        # Re-read raw entities to get exact count
        df_saved_entities = pd.read_csv(entities_out_path)
        print(f"\n📈 Số lượng thực thể trích xuất được theo loại (raw_entities):", flush=True)
        entity_counts = df_saved_entities['entity_type'].value_counts()
        for etype, count in entity_counts.items():
            print(f"  - {etype}: {count}", flush=True)
            
        print(f"\n📈 Số lượng giá trị metadata được bổ sung/làm giàu:", flush=True)
        for k, count in enriched_counters.items():
            print(f"  - {k}: {count}", flush=True)
            
        print(f"\n🔍 HIỂN THỊ 5 VÍ DỤ METADATA GỐC SO VỚI METADATA LÀM GIÀU:", flush=True)
        for idx, comp in enumerate(comparison_data[:5]):
            print("-" * 50, flush=True)
            print(f"Ví dụ {idx+1}: Document ID: {comp['id']} ({comp['so_ky_hieu']})", flush=True)
            print("  [GỐC]:", flush=True)
            for field, val in comp["orig"].items():
                print(f"    - {field}: {val}", flush=True)
            print("  [LÀM GIÀU]:", flush=True)
            for field, val in comp["enriched"].items():
                print(f"    - {field}: {val}", flush=True)
                
    if failures_log:
        print(f"\n❌ DANH SÁCH LỖI GẶP PHẢI ({len(failures_log)} lỗi):", flush=True)
        for err in failures_log:
            print(f"  - {err}", flush=True)
            
    print("==================================================", flush=True)
    if success_docs == total_docs:
        print("🎉 KẾT QUẢ BƯỚC 3: [PASS]", flush=True)
        sys.exit(0)
    else:
        print("❌ KẾT QUẢ BƯỚC 3: [FAIL]", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
