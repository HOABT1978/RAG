import os
import pandas as pd
from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import Reranker

class UnifiedRetriever:
    def __init__(self, corpus_df, embeddings_path, api_key, reranker_model='BAAI/bge-reranker-v2-m3'):
        self.bm25 = BM25Retriever(corpus_df)
        self.dense = DenseRetriever(corpus_df, embeddings_path, api_key)
        self.hybrid = HybridRetriever(self.bm25, self.dense)
        self.reranker = Reranker(model_name=reranker_model)
        
    def retrieve(self, question, method='hybrid_rerank', top_k=5):
        method = method.lower().strip()
        
        if method == 'bm25':
            res = self.bm25.retrieve(question, top_k=top_k)
            return [{
                'rank': item['rank'],
                'chunk_id': item['chunk_id'],
                'document_id': item['document_id'],
                'text': item['text'],
                'score': float(item['retrieval_score']),
                'citation': item['citation'],
                'retrieval_method': 'bm25'
            } for item in res]
            
        elif method == 'dense':
            res = self.dense.retrieve(question, top_k=top_k)
            return [{
                'rank': item['rank'],
                'chunk_id': item['chunk_id'],
                'document_id': item['document_id'],
                'text': item['text'],
                'score': float(item['retrieval_score']),
                'citation': item['citation'],
                'retrieval_method': 'dense'
            } for item in res]
            
        elif method == 'hybrid':
            res = self.hybrid.retrieve(question, candidate_k=20, top_k=top_k)
            return [{
                'rank': item['final_rank'],
                'chunk_id': item['chunk_id'],
                'document_id': item['document_id'],
                'text': item['text'],
                'score': float(item['rrf_score']),
                'citation': item['citation'],
                'retrieval_method': 'hybrid',
                'bm25_rank': item['bm25_rank'],
                'dense_rank': item['dense_rank']
            } for item in res]
            
        elif method == 'hybrid_rerank':
            # Run hybrid search to gather candidates
            candidates = self.hybrid.retrieve(question, candidate_k=20, top_k=20)
            res = self.reranker.rerank(question, candidates, top_k=top_k)
            
            output = []
            for item in res:
                out_item = {
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
                    'dense_rank': item.get('dense_rank', None)
                }
                output.append(out_item)
            return output
        else:
            raise ValueError(f"Unknown retrieval method: {method}")
