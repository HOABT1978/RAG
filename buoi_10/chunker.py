"""
Chunking & Parsing - Buổi 10
Làm sạch HTML, phân tách phân cấp (Chapter ➔ Section ➔ Article ➔ Clause ➔ Item ➔ Content/Table),
nối NEXT quan hệ anh em, và lưu kết quả JSON sạch.
"""

import csv
import sys
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')
csv.field_size_limit(500 * 1024 * 1024)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path("d:/Rag_thuchanh/RAG/kb+hops")
OUTPUT_PATH = DATA_DIR / "chunks_parsed.json"

def clean_html_text(soup_node):
    """Làm sạch HTML. Bảng biểu được chuyển sang định dạng Markdown."""
    if soup_node.name == 'table':
        rows = []
        for tr in soup_node.find_all('tr'):
            cols = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            rows.append(cols)
        if not rows:
            return ""
        max_cols = max(len(r) for r in rows)
        for r in rows:
            while len(r) < max_cols:
                r.append("")
        lines = []
        for i, r in enumerate(rows):
            lines.append("| " + " | ".join(r) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        return "\n".join(lines)
    else:
        t = soup_node.get_text(separator=" ", strip=True)
        t = re.sub(r"\s+", " ", t)
        return t

def parse_document(doc_id, html_content):
    """Phân tách tài liệu HTML thành các chunks phân cấp."""
    soup = BeautifulSoup(html_content, "html.parser")
    body = soup.body if soup.body else soup
    
    # 1. Thu thập tất cả các tags khối tiềm năng có chứa nội dung
    elements = []
    for child in body.descendants:
        if child.name in ['p', 'table', 'div'] and child.get_text(strip=True):
            classes = child.get('class', [])
            if any(c in ['prov-chapter', 'prov-section', 'prov-subsection', 'prov-article', 'prov-clause', 'prov-item', 'prov-content', 'prov-table', 'detailcontent'] for c in classes) or child.name == 'table':
                # Tránh lấy lặp lại các nút lồng nhau
                ancestor_in_list = False
                for el in elements:
                    if el['node'] in child.parents:
                        ancestor_in_list = True
                        break
                if not ancestor_in_list:
                    elements.append({
                        'node': child,
                        'classes': classes,
                        'name': child.name
                    })

    # 2. Hợp nhất các dòng tiêu đề liền kề bị tách rời trong HTML gốc
    merged_elements = []
    for el in elements:
        classes = el['classes']
        tag_name = el['name']
        
        chunk_type = 'content'
        if 'prov-chapter' in classes:
            chunk_type = 'chapter'
        elif 'prov-section' in classes:
            chunk_type = 'section'
        elif 'prov-subsection' in classes:
            chunk_type = 'subsection'
        elif 'prov-article' in classes:
            chunk_type = 'article'
        elif 'prov-clause' in classes:
            chunk_type = 'clause'
        elif 'prov-item' in classes:
            chunk_type = 'item'
        elif 'prov-table' in classes or tag_name == 'table':
            chunk_type = 'table'
            
        clean_text = clean_html_text(el['node'])
        if not clean_text:
            continue
            
        # Kiểm tra xem tiêu đề này có phải phần viết tiếp của tiêu đề trước không
        if merged_elements and chunk_type in ['chapter', 'section', 'subsection', 'article']:
            prev_el = merged_elements[-1]
            if prev_el['type'] == chunk_type:
                is_continuation = False
                if chunk_type == 'chapter' and not re.match(r"^chương\s+", clean_text.lower()):
                    is_continuation = True
                elif chunk_type == 'section' and not re.match(r"^mục\s+", clean_text.lower()):
                    is_continuation = True
                elif chunk_type == 'subsection' and not re.match(r"^tiểu\s*mục\s+", clean_text.lower()):
                    is_continuation = True
                elif chunk_type == 'article' and not re.match(r"^điều\s+", clean_text.lower()):
                    is_continuation = True
                    
                if is_continuation:
                    prev_el['text'] += " " + clean_text
                    continue
                    
        merged_elements.append({
            'type': chunk_type,
            'text': clean_text
        })

    # 3. Phân tích cấu trúc cây phân cấp cha-con
    chunks = []
    current_parent_by_level = {
        'document': doc_id,
        'chapter': None,
        'section': None,
        'subsection': None,
        'article': None,
        'clause': None,
        'item': None
    }
    
    level_hierarchy = {
        'document': 0,
        'chapter': 1,
        'section': 2,
        'subsection': 3,
        'article': 4,
        'clause': 5,
        'item': 6,
        'content': 7,
        'table': 7
    }

    def get_active_parent(child_level):
        target_val = level_hierarchy[child_level]
        best_parent = doc_id
        best_parent_type = 'document'
        for lvl_name, lvl_val in level_hierarchy.items():
            if lvl_val < target_val:
                p_node = current_parent_by_level[lvl_name]
                if p_node:
                    best_parent = p_node
                    best_parent_type = lvl_name
        return best_parent, best_parent_type

    chunk_idx = 1
    for el in merged_elements:
        chunk_type = el['type']
        clean_text = el['text']
        
        chunk_id = f"chk_{doc_id}_{chunk_idx:04d}"
        chunk_idx += 1
        
        parent_id, parent_type = get_active_parent(chunk_type if chunk_type != 'table' else 'content')
        
        # Cập nhật trạng thái parent
        if chunk_type in current_parent_by_level:
            current_parent_by_level[chunk_type] = chunk_id
            target_val = level_hierarchy[chunk_type]
            for lvl_name, lvl_val in level_hierarchy.items():
                if lvl_val > target_val and lvl_name not in ['content', 'table']:
                    current_parent_by_level[lvl_name] = None
                    
        chunks.append({
            'chunk_id': chunk_id,
            'doc_id': doc_id,
            'type': chunk_type,
            'text': clean_text,
            'parent_id': parent_id,
            'parent_type': parent_type
        })
        
    # 4. Thiết lập liên kết NEXT cho các node anh em cùng cha
    parent_to_children = {}
    for c in chunks:
        pid = c['parent_id']
        if pid not in parent_to_children:
            parent_to_children[pid] = []
        parent_to_children[pid].append(c)
        
    for pid, child_list in parent_to_children.items():
        for i in range(len(child_list) - 1):
            child_list[i]['next_sibling_id'] = child_list[i+1]['chunk_id']
            
    return chunks

def main():
    content_csv = DATA_DIR / "content.csv"
    if not content_csv.exists():
        print(f"❌ Không tìm thấy tệp {content_csv}")
        return
        
    all_chunks = []
    print("⏳ Đang phân tách cấu trúc HTML từ content.csv...")
    
    with open(content_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        for row in reader:
            doc_id = row[0]
            html_content = row[1]
            
            doc_chunks = parse_document(doc_id, html_content)
            all_chunks.extend(doc_chunks)
            
    # Lưu kết quả ra JSON
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Đã phân tách xong! Tổng số chunks được tạo: {len(all_chunks)}")
    print(f"📁 Đã lưu danh sách chunks tại: {OUTPUT_PATH}")
    
    # In kết quả phân tách mẫu cho 15 chunks đầu tiên của văn bản thứ nhất để minh họa trực quan
    print("\n================== MINH HỌA TRỰC QUAN KẾT QUẢ CHUNKING (MẪU) ==================")
    sample_doc_id = all_chunks[0]['doc_id']
    sample_chunks = [c for c in all_chunks if c['doc_id'] == sample_doc_id][:20]
    
    for c in sample_chunks:
        indent = "  " * (['document', 'chapter', 'section', 'subsection', 'article', 'clause', 'item', 'content', 'table'].index(c['type']) if c['type'] in ['chapter', 'section', 'subsection', 'article', 'clause', 'item'] else 6)
        next_sibling = c.get('next_sibling_id', 'None')
        print(f"{indent}[{c['type'].upper()}] ID: {c['chunk_id']} | Parent: {c['parent_id']} | NEXT: {next_sibling}")
        print(f"{indent}Text: {c['text'][:120]}...")
        print("-" * 80)

if __name__ == "__main__":
    main()
