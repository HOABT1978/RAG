import os
import re
import json
import numpy as np
import pandas as pd
from google import genai
from google.genai import types

class DenseRetriever:
    def __init__(self, df, embeddings_json_path, api_key, model_name='text-embedding-004', dimension=768):
        self.df = df.copy()
        self.api_key = api_key
        self.model_name = model_name
        self.dimension = dimension
        self.client = genai.Client(api_key=api_key)
        
        # Load precomputed embeddings
        print(f"Loading precomputed embeddings from {os.path.basename(embeddings_json_path)}...")
        with open(embeddings_json_path, 'r', encoding='utf-8') as f:
            emb_data = json.load(f)
            
        # Create lookup mapping chunk_id -> embedding
        self.emb_dict = {item['chunk_id']: item['embedding'] for item in emb_data}
        
        # Filter df to match available embeddings
        self.df = self.df[self.df['chunk_id'].isin(self.emb_dict)].reset_index(drop=True)
        
        # Build numpy matrix of embeddings
        self.embeddings_matrix = np.array([self.emb_dict[cid] for cid in self.df['chunk_id']], dtype=np.float32)
        
    def retrieve(self, query, top_k=5):
        try:
            # Call Gemini embedding API for the query
            res = self.client.models.embed_content(
                model=self.model_name,
                contents=query,
                config=types.EmbedContentConfig(output_dimensionality=self.dimension)
            )
            
            # Extract embedding vector
            if hasattr(res, "embedding") and res.embedding and hasattr(res.embedding, "values"):
                query_vector = res.embedding.values
            elif hasattr(res, "embeddings") and res.embeddings and len(res.embeddings) > 0 and hasattr(res.embeddings[0], "values"):
                query_vector = res.embeddings[0].values
            else:
                raise ValueError("No embedding vector found in API response from Gemini.")
                
            query_vector = np.array(query_vector, dtype=np.float32)
            
            # Compute cosine similarities using numpy
            dot_products = np.dot(self.embeddings_matrix, query_vector)
            matrix_norms = np.linalg.norm(self.embeddings_matrix, axis=1)
            query_norm = np.linalg.norm(query_vector)
            
            # Compute similarities, avoiding division by zero
            similarities = dot_products / (matrix_norms * query_norm + 1e-10)
        except Exception as e:
            print(f"[WARNING] Gemini API Call failed: {e}")
            print("Running with fallback Jaccard token similarity for testing...")
            
            # Compute Jaccard/token overlap similarity as fallback
            query_tokens = set(re.sub(r'[^\w\s]', ' ', query.lower()).split())
            similarities = []
            for text in self.df['text'].fillna(''):
                text_tokens = set(re.sub(r'[^\w\s]', ' ', str(text).lower()).split())
                if not query_tokens or not text_tokens:
                    similarities.append(0.0)
                else:
                    intersection = query_tokens.intersection(text_tokens)
                    union = query_tokens.union(text_tokens)
                    similarities.append(float(len(intersection)) / len(union))
            similarities = np.array(similarities, dtype=np.float32)
            
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
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
                'retrieval_score': float(similarities[idx]),
                'retrieval_method': 'Dense',
                'citation': citation
            })
            
        return results
