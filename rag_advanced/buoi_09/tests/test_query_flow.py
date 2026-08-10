"""
Unit tests cho RAG Query Flow (Flat vs Parent modes, Rerank, Gating, Generation, Citations) - Buổi 09
"""

import sys
import json
import shutil
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import query_hierarchical_rag


class TestQueryFlow(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = BASE_DIR / "tests" / "tmp_query_storage"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.hier_dir = self.tmp_dir / "storage" / "hierarchy"
        self.hier_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    def test_01_mode_routing_and_reranking_gating_citations(self):
        """1, 3, 4, 5, 6, 9 & 10. Flat/Parent routing, Rerank, Gating, Citation validation và Không evidence không generation."""
        import hierarchical_rag
        original_base = hierarchical_rag.BASE_DIR
        hierarchical_rag.BASE_DIR = self.tmp_dir
        
        try:
            # Ghi cấu hình .env ảo
            with open(self.tmp_dir / ".env", "w") as f:
                f.write("PARENT_MAX_CHARS=6000\nPARENT_SCORE_CHILD_LIMIT=2\nPARENT_RRF_K=60\nPARENT_CANDIDATES=5\nTOTAL_CONTEXT_MAX_CHARS=16000\nGEMINI_EMBEDDING_MODEL=gemini-embedding-2\nGEMINI_GENERATION_MODEL=gemini-3.5-flash-lite\nRERANKER_MODEL=BAAI/bge-reranker-v2-m3\nRERANK_MIN_SCORE=0.5\nRERANK_CANDIDATES=5\nFINAL_PARENT_TOP_K=3\nFINAL_TOP_K=3\nMULTI_QUERY_COUNT=2\nBM25_CANDIDATES=5\nSEMANTIC_CANDIDATES=5\nPER_QUERY_CANDIDATES=5\nSTRATEGY=hierarchical\n")
            
            # Ghi manifest.json, children.json, parents.json
            manifest_payload = {
                "strategy": "hierarchical",
                "config_identity": {
                    "parent_max_chars": 6000,
                    "parent_score_child_limit": 2
                },
                "input_file_fingerprints": {}
            }
            with open(self.hier_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest_payload, f)
                
            children_data = [
                {
                    "child_id": "c1",
                    "parent_id": "p1",
                    "source": "s1.pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "t1",
                    "structural_path": {"chapter": "Chương I", "article": "Điều 1"},
                    "ambiguous": False,
                    "warnings": []
                }
            ]
            with open(self.hier_dir / "children.json", "w", encoding="utf-8") as f:
                json.dump(children_data, f)
                
            parents_data = [
                {
                    "parent_id": "p1",
                    "source": "s1.pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "text": "nội dung Điều 1 pháp luật ngân hàng",
                    "child_ids": ["c1"],
                    "warnings": []
                }
            ]
            with open(self.hier_dir / "parents.json", "w", encoding="utf-8") as f:
                json.dump(parents_data, f)

            # Injected fakes
            def fake_generator(q):
                return {
                    "status": "ready",
                    "queries": [
                        {"query_id": "Q0", "text": "Vay vốn?", "origin": "original", "focus": "original_intent"},
                        {"query_id": "Q1", "text": "Điều kiện vay?", "origin": "generated", "focus": "paraphrase"}
                    ],
                    "cache_hit": True
                }

            def fake_bm25(q, limit):
                return [{"chunk_id": "c1", "text": "t1", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}]

            def fake_reranker(question, candidates):
                # Gán score cao hơn 0.5 để vượt gate
                for c in candidates:
                    c["rerank_score"] = 0.8
                    c["rerank_raw_score"] = 1.3
                return candidates

            # Test 1: multi_parent mode thành công
            res_multi = query_hierarchical_rag(
                question="Vay vốn?",
                mode="multi_parent",
                custom_query_generator=fake_generator,
                custom_bm25_retriever=fake_bm25,
                custom_semantic_retriever=lambda q, k: [],
                custom_reranker=fake_reranker,
                custom_generator=lambda prompt: "Theo [P1] quy định ngân hàng...",
            )
            
            self.assertEqual(res_multi["status"], "answered")
            self.assertEqual(res_multi["mode"], "multi_parent")
            self.assertEqual(len(res_multi["accepted_evidence"]), 1)
            self.assertEqual(res_multi["accepted_evidence"][0]["parent_id"], "p1")
            
            # Kiểm tra trích dẫn citations
            self.assertEqual(len(res_multi["citations"]), 1)
            self.assertEqual(res_multi["citations"][0]["evidence_id"], "P1")
            self.assertEqual(res_multi["citations"][0]["parent_id"], "p1")
            self.assertEqual(res_multi["citations"][0]["anchor_child_id"], "c1")

            # Test 2: Reranker failure (throws exception) -> status 'reranker_unavailable'
            def fake_reranker_fail(question, candidates):
                raise RuntimeError("Reranker model corrupted")

            res_fail = query_hierarchical_rag(
                question="Vay vốn?",
                mode="multi_parent",
                custom_query_generator=fake_generator,
                custom_bm25_retriever=fake_bm25,
                custom_semantic_retriever=lambda q, k: [],
                custom_reranker=fake_reranker_fail,
                custom_generator=lambda prompt: "Theo [P1]..."
            )
            self.assertEqual(res_fail["status"], "reranker_unavailable")

            # Test 3: Citation label mismatch / validation fail
            res_cite_fail = query_hierarchical_rag(
                question="Vay vốn?",
                mode="multi_parent",
                custom_query_generator=fake_generator,
                custom_bm25_retriever=fake_bm25,
                custom_semantic_retriever=lambda q, k: [],
                custom_reranker=fake_reranker,
                # LLM trả về nhãn [P9] không tồn tại trong evidence
                custom_generator=lambda prompt: "Theo [P9]...",
            )
            self.assertEqual(res_cite_fail["status"], "insufficient_evidence")
            self.assertEqual(len(res_cite_fail["citations"]), 0)

            # Test 4: Gating rejected (rerank_score < 0.5) -> insufficient_evidence
            def fake_reranker_low(question, candidates):
                for c in candidates:
                    c["rerank_score"] = 0.2
                    c["rerank_raw_score"] = -1.3
                return candidates

            res_low = query_hierarchical_rag(
                question="Vay vốn?",
                mode="multi_parent",
                custom_query_generator=fake_generator,
                custom_bm25_retriever=fake_bm25,
                custom_semantic_retriever=lambda q, k: [],
                custom_reranker=fake_reranker_low,
                custom_generator=lambda prompt: "Theo [P1]..."
            )
            self.assertEqual(res_low["status"], "insufficient_evidence")

        finally:
            hierarchical_rag.BASE_DIR = original_base


if __name__ == "__main__":
    unittest.main()
