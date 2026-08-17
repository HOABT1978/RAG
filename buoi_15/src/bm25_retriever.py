import re
import pandas as pd
from rank_bm25 import BM25Okapi

class BM25Retriever:
    def __init__(self, df):
        self.df = df.copy()
        self.corpus_texts = self.df['text'].fillna('').tolist()
        self.tokenized_corpus = [self.tokenize(text) for text in self.corpus_texts]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
    def tokenize(self, text):
        # Convert to lowercase and strip special characters except slashes and dashes
        # This keeps terms like "73/2016/NĐ-CP" intact which is critical for legal references.
        text = text.lower()
        text = re.sub(r'[^\w\s\-\/]', ' ', text)
        return text.split()
        
    def retrieve(self, query, top_k=5):
        tokenized_query = self.tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for rank_idx, idx in enumerate(top_indices, start=1):
            row = self.df.iloc[idx]
            
            # Construct citation based on structural metadata
            hierarchy_parts = []
            if row.get('chapter'):
                hierarchy_parts.append(str(row['chapter']))
            if row.get('section'):
                hierarchy_parts.append(str(row['section']))
            if row.get('article'):
                hierarchy_parts.append(str(row['article']))
            if row.get('clause'):
                hierarchy_parts.append(str(row['clause']))
                
            hierarchy_str = " | ".join(hierarchy_parts) if hierarchy_parts else "Nội dung"
            citation = f"[{row['title']} | {hierarchy_str} | {row['chunk_id']}]"
            
            results.append({
                'rank': rank_idx,
                'chunk_id': row['chunk_id'],
                'document_id': row['document_id'],
                'text': row['text'],
                'retrieval_score': float(scores[idx]),
                'retrieval_method': 'BM25',
                'citation': citation
            })
            
        return results
