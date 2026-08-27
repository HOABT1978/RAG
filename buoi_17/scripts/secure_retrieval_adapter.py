import os
import sys
import json
import pandas as pd
from pathlib import Path

# Add parent dir (buoi_17) or buoi_15 to sys.path to enable imports of src.*
PARENT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BUOI_15_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'buoi_15'))
if PARENT_PATH not in sys.path:
    sys.path.append(PARENT_PATH)
if BUOI_15_PATH not in sys.path:
    sys.path.append(BUOI_15_PATH)


from src.secure_retriever import SecureRetriever

class SecureRetrievalAdapter:
    def __init__(self, secure_csv_path=None, embeddings_json_path=None, api_key=None, reranker_model='BAAI/bge-reranker-v2-m3'):
        # Load environment variables if not provided
        if secure_csv_path is None:
            # relative to this script: ../../buoi_15/data/processed/chunks_secure.csv
            secure_csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'buoi_15', 'data', 'processed', 'chunks_secure.csv'))
        if embeddings_json_path is None:
            embeddings_json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'kb+hops', 'chunks_embedded.json'))
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')
            
        self.retriever = SecureRetriever(
            secure_csv_path=secure_csv_path,
            embeddings_json_path=embeddings_json_path,
            api_key=api_key,
            reranker_model=reranker_model
        )
        
    def retrieve(self, question, user_roles, method='hybrid_rerank', top_k=5, candidate_k=20):
        # 1. Call the original SecureRetriever
        original_results = self.retriever.retrieve(
            question=question,
            user_roles=user_roles,
            method=method,
            top_k=top_k,
            candidate_k=candidate_k
        )
        
        # 2. Normalize results
        normalized_results = []
        for item in original_results:
            chunk_id = item['chunk_id']
            
            # Fetch additional metadata (title, article) from the underlying master DataFrame
            matching_rows = self.retriever.df[self.retriever.df['chunk_id'] == chunk_id]
            if not matching_rows.empty:
                row = matching_rows.iloc[0]
                title = row.get('title', '')
                article = row.get('article', '')
            else:
                title = ''
                article = ''
                
            norm_item = {
                'rank': item.get('rank'),
                'chunk_id': chunk_id,
                'document_id': item.get('document_id'),
                'title': title,
                'article': article,
                'citation': item.get('citation'),
                'allowed_roles': item.get('allowed_roles'),
                'access_decision': 'GRANTED',
                'retrieval_method': item.get('retrieval_method', method),
                'retrieval method': item.get('retrieval_method', method), # support both keys
                'text': item.get('text', '') # keep text for LLM generation
            }
            normalized_results.append(norm_item)
            
        return normalized_results
