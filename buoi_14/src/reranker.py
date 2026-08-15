import os
import sys
import difflib

class Reranker:
    def __init__(self, model_name='BAAI/bge-reranker-v2-m3', device=None):
        self.model_name = model_name
        self.use_neural = False
        
        # Try to import torch and transformers for BGE Reranker
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            
            if device is None:
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            else:
                self.device = device
                
            print(f"Attempting to load Neural Reranker '{model_name}' on '{self.device}'...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            self.torch = torch
            self.use_neural = True
            print("Successfully loaded Neural Reranker!")
            
        except Exception as e:
            print(f"[WARNING] Failed to load Neural Reranker: {e}")
            print("Falling back to Python-based sequence similarity reranking (difflib)...")
            
    def rerank(self, query, candidates, top_k=5):
        if not candidates:
            return []
            
        if self.use_neural:
            try:
                pairs = [[query, item['text']] for item in candidates]
                with self.torch.no_grad():
                    inputs = self.tokenizer(
                        pairs, 
                        padding=True, 
                        truncation=True, 
                        max_length=512, 
                        return_tensors='pt'
                    )
                    # Move to device
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    outputs = self.model(**inputs)
                    scores = outputs.logits.view(-1).float().cpu().numpy().tolist()
                    
                reranked = []
                for idx, item in enumerate(candidates):
                    new_item = item.copy()
                    new_item['rerank_score'] = float(scores[idx])
                    new_item['hybrid_rank'] = item['final_rank']
                    new_item['hybrid_score'] = item['rrf_score']
                    reranked.append(new_item)
                    
                # Sort by rerank score descending
                reranked = sorted(reranked, key=lambda x: x['rerank_score'], reverse=True)
                for rank_idx, item in enumerate(reranked, start=1):
                    item['final_rank'] = rank_idx
                    
                return reranked[:top_k]
                
            except Exception as e:
                print(f"[WARNING] Neural Reranker inference failed: {e}. Falling back to text matching.")
                # Proceed to fallback logic below
                
        # Fallback ranking logic (SequenceMatcher ratio)
        print("[INFO] Running FALLBACK Reranker (difflib SequenceMatcher)...")
        reranked = []
        for item in candidates:
            new_item = item.copy()
            # Calculate match ratio
            ratio = difflib.SequenceMatcher(None, query.lower(), new_item['text'].lower()).ratio()
            new_item['rerank_score'] = float(ratio)
            new_item['hybrid_rank'] = item['final_rank']
            new_item['hybrid_score'] = item['rrf_score']
            reranked.append(new_item)
            
        # Sort descending
        reranked = sorted(reranked, key=lambda x: x['rerank_score'], reverse=True)
        for rank_idx, item in enumerate(reranked, start=1):
            item['final_rank'] = rank_idx
            
        return reranked[:top_k]
