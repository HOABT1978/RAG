import os
import sys
import io
import json
import pandas as pd
from pathlib import Path

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # Normalize whitespace and strip
    text = text.strip()
    # Normalize multiple newlines and spaces
    text = os.linesep.join([line.strip() for line in text.splitlines() if line.strip()])
    return text

def main():
    script_dir = Path(__file__).resolve().parent
    buoi_14_dir = script_dir.parent
    project_root = buoi_14_dir.parent
    kb_hops_dir = project_root / "kb+hops"
    
    # Define paths
    metadata_path = kb_hops_dir / "metadata.csv"
    chunks_path = kb_hops_dir / "chunks_parsed.json"
    output_dir = buoi_14_dir / "data" / "processed"
    os.makedirs(output_dir, exist_ok=True)
    output_path = output_dir / "chunks_normalized.csv"
    
    # 1. Read metadata.csv
    print(f"Reading metadata from {metadata_path.name}...")
    df_meta = pd.read_csv(metadata_path, dtype={'id': str})
    # Create metadata lookup dict
    meta_lookup = {}
    for _, row in df_meta.iterrows():
        doc_id = str(row['id']).strip()
        meta_lookup[doc_id] = {
            'title': row.get('title', ''),
            'document_type': row.get('loai_van_ban', ''),
            'effective_date': row.get('ngay_co_hieu_luc', ''),
            'status': row.get('tinh_trang_hieu_luc', '')
        }
        
    # 2. Read chunks_parsed.json
    print(f"Reading chunks from {chunks_path.name}...")
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)
        
    # Build lookup for hierarchy traversal
    chunk_by_id = {c['chunk_id']: c for c in chunks_data}
    
    # Normalize chunks
    normalized_chunks = []
    
    for c in chunks_data:
        chunk_id = c['chunk_id']
        doc_id = str(c['doc_id']).strip()
        text = clean_text(c.get('text', ''))
        
        # Traverse hierarchy to find chapter, section, article, clause names
        chapter_val = None
        section_val = None
        article_val = None
        clause_val = None
        
        # Check self
        ctype = c.get('type')
        first_line = text.split('\n')[0] if text else ""
        if ctype == 'chapter':
            chapter_val = first_line
        elif ctype == 'section':
            section_val = first_line
        elif ctype == 'article':
            article_val = first_line
        elif ctype == 'clause':
            clause_val = first_line
            
        # Traverse up parents
        curr = c
        while curr.get('parent_type') != 'document':
            p_id = curr.get('parent_id')
            parent = chunk_by_id.get(p_id)
            if not parent:
                break
            ptype = parent.get('type')
            p_text = parent.get('text', '')
            p_first_line = p_text.split('\n')[0] if p_text else ""
            
            if ptype == 'chapter' and chapter_val is None:
                chapter_val = p_first_line
            elif ptype == 'section' and section_val is None:
                section_val = p_first_line
            elif ptype == 'article' and article_val is None:
                article_val = p_first_line
            elif ptype == 'clause' and clause_val is None:
                clause_val = p_first_line
                
            curr = parent
            
        # Get document metadata
        meta = meta_lookup.get(doc_id, {})
        
        normalized_chunks.append({
            'chunk_id': chunk_id,
            'document_id': doc_id,
            'text': text,
            'source_file': 'content.csv',
            'title': meta.get('title', c.get('doc_title', '')),
            'document_type': meta.get('document_type', ''),
            'chapter': chapter_val if chapter_val else '',
            'section': section_val if section_val else '',
            'article': article_val if article_val else '',
            'clause': clause_val if clause_val else '',
            'effective_date': meta.get('effective_date', ''),
            'status': meta.get('status', '')
        })
        
    # Convert to DataFrame
    df_normalized = pd.DataFrame(normalized_chunks)
    
    # 3. Validation & Metrics
    total_chunks = len(df_normalized)
    total_docs = df_normalized['document_id'].nunique()
    missing_text = df_normalized['text'].isna().sum() + (df_normalized['text'].str.strip() == '').sum()
    duplicate_chunks = df_normalized['chunk_id'].duplicated().sum()
    
    print("\n==================================================")
    print("STATISTICS & METRICS")
    print("==================================================")
    print(f"Total chunks: {total_chunks}")
    print(f"Total unique documents: {total_docs}")
    print(f"Chunks with missing text: {missing_text}")
    print(f"Duplicate chunk_ids: {duplicate_chunks}")
    
    # Write to outputs
    df_normalized.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\nNormalized corpus written to: {output_path}")
    
    # 3 Sample records
    print("\nSAMPLE RECORDS (3 examples):")
    sample_records = df_normalized.head(3).to_dict('records')
    for idx, sample in enumerate(sample_records):
        print(f"\n--- Sample {idx + 1} ---")
        print(f"Chunk ID: {sample['chunk_id']}")
        print(f"Doc ID: {sample['document_id']}")
        print(f"Title: {sample['title']}")
        print(f"Chapter: {sample['chapter']}")
        print(f"Section: {sample['section']}")
        print(f"Article: {sample['article']}")
        print(f"Clause: {sample['clause']}")
        print(f"Text snippet: {sample['text'][:150]}...")

if __name__ == '__main__':
    main()
