import os
import sys
import json
import re
import numpy as np
import pandas as pd
from pathlib import Path
from google import genai
from google.genai import types
from neo4j import GraphDatabase

from src.bm25_retriever import BM25Retriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import Reranker
from src.config import VALID_ROLES

class SecureDenseRetriever:
    def __init__(self, df, emb_dict, api_key, model_name='text-embedding-004', dimension=768):
        self.df = df.copy()
        self.api_key = api_key
        self.model_name = model_name
        self.dimension = dimension
        self.client = genai.Client(api_key=api_key)
        self.emb_dict = emb_dict
        
        # Filter df to match available embeddings
        self.df = self.df[self.df['chunk_id'].isin(self.emb_dict)].reset_index(drop=True)
        
        # Build numpy matrix of embeddings
        if len(self.df) > 0:
            self.embeddings_matrix = np.array([self.emb_dict[cid] for cid in self.df['chunk_id']], dtype=np.float32)
        else:
            self.embeddings_matrix = np.empty((0, self.dimension), dtype=np.float32)
            
    def retrieve(self, query, top_k=5):
        if len(self.df) == 0:
            return []
            
        try:
            # Call Gemini embedding API
            res = self.client.models.embed_content(
                model=self.model_name,
                contents=query,
                config=types.EmbedContentConfig(output_dimensionality=self.dimension)
            )
            if hasattr(res, "embedding") and res.embedding and hasattr(res.embedding, "values"):
                query_vector = res.embedding.values
            elif hasattr(res, "embeddings") and res.embeddings and len(res.embeddings) > 0 and hasattr(res.embeddings[0], "values"):
                query_vector = res.embeddings[0].values
            else:
                raise ValueError("No embedding vector found in API response.")
                
            query_vector = np.array(query_vector, dtype=np.float32)
            
            # Cosine similarity
            dot_products = np.dot(self.embeddings_matrix, query_vector)
            matrix_norms = np.linalg.norm(self.embeddings_matrix, axis=1)
            query_norm = np.linalg.norm(query_vector)
            similarities = dot_products / (matrix_norms * query_norm + 1e-10)
        except Exception as e:
            print(f"[WARNING] Gemini API Call failed: {e}. Running fallback Jaccard similarity.")
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
            
        top_k_actual = min(top_k, len(self.df))
        top_indices = np.argsort(similarities)[::-1][:top_k_actual]
        
        results = []
        for rank_idx, idx in enumerate(top_indices, start=1):
            row = self.df.iloc[idx]
            
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
                'citation': citation,
                'allowed_roles': json.loads(row['allowed_roles'])
            })
        return results

class SecureRetriever:
    def __init__(self, secure_csv_path, embeddings_json_path, api_key, reranker_model='BAAI/bge-reranker-v2-m3'):
        # Master Data Frame
        self.df = pd.read_csv(secure_csv_path)
        self.api_key = api_key
        
        # Load embedding JSON
        print(f"Preloading embeddings from {os.path.basename(embeddings_json_path)}...")
        with open(embeddings_json_path, 'r', encoding='utf-8') as f:
            emb_data = json.load(f)
        self.emb_dict = {item['chunk_id']: item['embedding'] for item in emb_data}
        
        # Initialize Shared Reranker
        self.reranker = Reranker(model_name=reranker_model)
        
    def filter_authorized_df(self, user_roles):
        # Validate roles
        if not user_roles or not isinstance(user_roles, list):
            user_roles = ["Guest"]
            
        def is_authorized(row_roles_str):
            try:
                row_roles = json.loads(row_roles_str)
                return any(r in user_roles for r in row_roles)
            except Exception:
                return False
                
        mask = self.df['allowed_roles'].apply(is_authorized)
        return self.df[mask].reset_index(drop=True)
        
    def retrieve(self, question, user_roles, method='hybrid_rerank', top_k=5, candidate_k=20):
        method = method.lower().strip()
        
        # 1. Filter DataFrame to authorized subset (Pre-filtering)
        auth_df = self.filter_authorized_df(user_roles)
        if len(auth_df) == 0:
            print("[INFO] No authorized documents found for the user roles.")
            return []
            
        # 2. Instantiate temporary retrievers on the authorized subset
        bm25_retriever = BM25Retriever(auth_df)
        dense_retriever = SecureDenseRetriever(auth_df, self.emb_dict, self.api_key)
        
        if method == 'bm25':
            res = bm25_retriever.retrieve(question, top_k=top_k)
            output = []
            for item in res:
                chunk_id = item['chunk_id']
                allowed_roles = json.loads(auth_df[auth_df['chunk_id'] == chunk_id]['allowed_roles'].iloc[0])
                output.append({
                    'rank': item['rank'],
                    'chunk_id': item['chunk_id'],
                    'document_id': item['document_id'],
                    'text': item['text'],
                    'score': float(item['retrieval_score']),
                    'citation': item['citation'],
                    'retrieval_method': 'bm25',
                    'allowed_roles': allowed_roles
                })
            return output
            
        elif method == 'dense':
            res = dense_retriever.retrieve(question, top_k=top_k)
            output = []
            for item in res:
                output.append({
                    'rank': item['rank'],
                    'chunk_id': item['chunk_id'],
                    'document_id': item['document_id'],
                    'text': item['text'],
                    'score': float(item['retrieval_score']),
                    'citation': item['citation'],
                    'retrieval_method': 'dense',
                    'allowed_roles': item['allowed_roles']
                })
            return output
            
        elif method == 'hybrid':
            hybrid_retriever = HybridRetriever(bm25_retriever, dense_retriever)
            res = hybrid_retriever.retrieve(question, candidate_k=candidate_k, top_k=top_k)
            output = []
            for item in res:
                chunk_id = item['chunk_id']
                allowed_roles = json.loads(auth_df[auth_df['chunk_id'] == chunk_id]['allowed_roles'].iloc[0])
                output.append({
                    'rank': item['final_rank'],
                    'chunk_id': item['chunk_id'],
                    'document_id': item['document_id'],
                    'text': item['text'],
                    'score': float(item['rrf_score']),
                    'citation': item['citation'],
                    'retrieval_method': 'hybrid',
                    'bm25_rank': item['bm25_rank'],
                    'dense_rank': item['dense_rank'],
                    'allowed_roles': allowed_roles
                })
            return output
            
        elif method == 'hybrid_rerank':
            hybrid_retriever = HybridRetriever(bm25_retriever, dense_retriever)
            # Rerank candidates are secured since they come from hybrid_retriever built on auth_df
            candidates = hybrid_retriever.retrieve(question, candidate_k=candidate_k, top_k=candidate_k)
            
            rerank_candidates = []
            for item in candidates:
                rerank_candidates.append({
                    'chunk_id': item['chunk_id'],
                    'document_id': item['document_id'],
                    'text': item['text'],
                    'final_rank': item['final_rank'],
                    'rrf_score': item['rrf_score'],
                    'citation': item['citation']
                })
                
            res = self.reranker.rerank(question, rerank_candidates, top_k=top_k)
            
            output = []
            for item in res:
                chunk_id = item['chunk_id']
                allowed_roles = json.loads(auth_df[auth_df['chunk_id'] == chunk_id]['allowed_roles'].iloc[0])
                output.append({
                    'rank': item['final_rank'],
                    'chunk_id': item['chunk_id'],
                    'document_id': item['document_id'],
                    'text': item['text'],
                    'score': float(item['rerank_score']),
                    'citation': item['citation'],
                    'retrieval_method': 'hybrid_rerank',
                    'hybrid_score': float(item['hybrid_score']),
                    'hybrid_rank': item['hybrid_rank'],
                    'bm25_rank': item.get('bm25_rank', None),
                    'dense_rank': item.get('dense_rank', None),
                    'allowed_roles': allowed_roles
                })
            return output
        else:
            raise ValueError(f"Unknown retrieval method: {method}")
            
    def get_graph_hints(self, doc_ids, chunk_ids, user_roles):
        # Database configs loaded from environmental variables
        uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
        user = os.getenv("NEO4J_USER", "BUOI_15")
        password = os.getenv("NEO4J_PASSWORD", "12345678")
        db_name = os.getenv("NEO4J_DATABASE", "neo4j")
        
        if not user_roles or not isinstance(user_roles, list):
            user_roles = ["Guest"]
            
        hints = {
            'doc_relations': [],
            'contains_relations': [],
            'next_relations': []
        }
        
        driver = None
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            
            with driver.session(database=db_name) as session:
                # 1. Document relations with allowed_roles verification
                doc_rel_query = """
                MATCH (v1:VanBan {lab_session: 'buoi_15'})-[r]->(v2:VanBan {lab_session: 'buoi_15'})
                WHERE v1.id IN $doc_ids AND type(r) <> 'CONTAINS'
                  AND any(role IN v1.allowed_roles WHERE role IN $user_roles)
                  AND any(role IN v2.allowed_roles WHERE role IN $user_roles)
                RETURN v1.id AS source, type(r) AS rel_type, v2.id AS target, v1.so_ky_hieu as skh1, v2.so_ky_hieu as skh2
                """
                res_doc = session.run(doc_rel_query, doc_ids=doc_ids, user_roles=user_roles)
                for record in res_doc:
                    hints['doc_relations'].append(
                        f"📄 {record['source']} ({record['skh1']}) -[:{record['rel_type']}]-> {record['target']} ({record['skh2']})"
                    )
                    
                # 2. Contains relations with allowed_roles verification
                contains_query = """
                MATCH (v:VanBan {lab_session: 'buoi_15'})-[r:CONTAINS]->(d:DieuKhoan {lab_session: 'buoi_15'})
                WHERE d.id IN $chunk_ids
                  AND any(role IN v.allowed_roles WHERE role IN $user_roles)
                  AND any(role IN d.allowed_roles WHERE role IN $user_roles)
                RETURN v.id AS doc_id, d.id AS chunk_id, v.so_ky_hieu as skh
                """
                res_contains = session.run(contains_query, chunk_ids=chunk_ids, user_roles=user_roles)
                for record in res_contains:
                    hints['contains_relations'].append(
                        f"📄 Văn bản {record['doc_id']} ({record['skh']}) -[:CONTAINS]-> 🧩 Phân đoạn {record['chunk_id']}"
                    )
                    
                # 3. Next relations with allowed_roles verification
                next_query = """
                MATCH (d1:DieuKhoan {lab_session: 'buoi_15'})-[r:NEXT]->(d2:DieuKhoan {lab_session: 'buoi_15'})
                WHERE (d1.id IN $chunk_ids OR d2.id IN $chunk_ids)
                  AND any(role IN d1.allowed_roles WHERE role IN $user_roles)
                  AND any(role IN d2.allowed_roles WHERE role IN $user_roles)
                RETURN d1.id AS source, d2.id AS target
                """
                res_next = session.run(next_query, chunk_ids=chunk_ids, user_roles=user_roles)
                for record in res_next:
                    hints['next_relations'].append(
                        f"🧩 Phân đoạn {record['source']} -[:NEXT]-> 🧩 Phân đoạn {record['target']}"
                    )
        except Exception as e:
            print(f"[WARNING] Graph DB secure fetch failed: {e}")
            return None
        finally:
            if driver:
                driver.close()
                
        return hints
