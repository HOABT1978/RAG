class HybridRetriever:
    def __init__(self, bm25_retriever, dense_retriever, k=60, bm25_weight=1.0, dense_weight=1.0):
        self.bm25_retriever = bm25_retriever
        self.dense_retriever = dense_retriever
        self.k = k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        
    def retrieve(self, query, candidate_k=20, top_k=5):
        # 1. Get candidate_k results from both retrievers
        bm25_res = self.bm25_retriever.retrieve(query, top_k=candidate_k)
        dense_res = self.dense_retriever.retrieve(query, top_k=candidate_k)
        
        # 2. Build rank lookup dicts
        bm25_ranks = {item['chunk_id']: item['rank'] for item in bm25_res}
        dense_ranks = {item['chunk_id']: item['rank'] for item in dense_res}
        
        # Keep track of all unique chunks and their details
        chunks_lookup = {}
        for item in bm25_res:
            chunks_lookup[item['chunk_id']] = item
        for item in dense_res:
            chunks_lookup[item['chunk_id']] = item
            
        # 3. Calculate RRF Score for each unique chunk
        rrf_scores = {}
        for chunk_id in chunks_lookup:
            score = 0.0
            
            # BM25 rank contribution
            if chunk_id in bm25_ranks:
                score += self.bm25_weight / (self.k + bm25_ranks[chunk_id])
                
            # Dense rank contribution
            if chunk_id in dense_ranks:
                score += self.dense_weight / (self.k + dense_ranks[chunk_id])
                
            rrf_scores[chunk_id] = score
            
        # 4. Sort by RRF score descending
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
        
        # 5. Build final rank
        results = []
        for rank_idx, chunk_id in enumerate(sorted_chunk_ids[:top_k], start=1):
            item = chunks_lookup[chunk_id]
            results.append({
                'final_rank': rank_idx,
                'chunk_id': chunk_id,
                'document_id': item['document_id'],
                'bm25_rank': bm25_ranks.get(chunk_id, None),
                'dense_rank': dense_ranks.get(chunk_id, None),
                'rrf_score': float(rrf_scores[chunk_id]),
                'text': item['text'],
                'citation': item['citation']
            })
            
        return results
