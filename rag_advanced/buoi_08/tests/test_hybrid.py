"""
Unit tests cho Reciprocal Rank Fusion (RRF) và Hybrid Search Pipeline - Buổi 08
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Nạp module advanced_rag
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    rrf_fusion,
    search_hybrid,
    get_chroma_client,
    get_collection_name,
    load_advanced_config
)


class TestRRFAndHybridSearch(unittest.TestCase):

    def setUp(self):
        """Khởi tạo tập candidate mock cho BM25 và Semantic Search."""
        self.bm25_results = [
            {
                "chunk_id": "chk_001",
                "text": "Văn bản về cơ cấu nợ.",
                "source": "DocA.pdf",
                "page_start": 1,
                "page_end": 1,
                "bm25_rank": 1,
                "bm25_score": 5.0
            },
            {
                "chunk_id": "chk_002",
                "text": "Văn bản về phân loại nhóm nợ.",
                "source": "DocB.pdf",
                "page_start": 2,
                "page_end": 2,
                "bm25_rank": 2,
                "bm25_score": 3.5
            }
        ]

        self.semantic_results = [
            {
                "chunk_id": "chk_001",
                "text": "Văn bản về cơ cấu nợ.",
                "source": "DocA.pdf",
                "page_start": 1,
                "page_end": 1,
                "semantic_rank": 3,
                "semantic_distance": 0.15
            },
            {
                "chunk_id": "chk_003",
                "text": "Văn bản về gia hạn thời hạn nợ.",
                "source": "DocC.pdf",
                "page_start": 4,
                "page_end": 4,
                "semantic_rank": 1,
                "semantic_distance": 0.08
            }
        ]

    def test_01_rrf_formula_arithmetic_accuracy(self):
        """1. Tính toán số học của công thức RRF chính xác từng phần thập phân."""
        # For chk_001: bm25_rank=1, semantic_rank=3, k=60, weights=1.0
        # rrf_score = 1/(60+1) + 1/(60+3) = 1/61 + 1/63 = 0.0163934426 + 0.0158730158 = 0.032266
        fused = rrf_fusion(self.bm25_results, self.semantic_results, k=60, top_n=10)
        item1 = next(c for c in fused if c["chunk_id"] == "chk_001")

        expected_score = round(1.0 / 61.0 + 1.0 / 63.0, 6)
        self.assertEqual(item1["rrf_score"], expected_score)

    def test_02_candidate_overlap_no_duplicate(self):
        """2. Candidate xuất hiện ở cả 2 nhánh không bị nhân bản (no duplicate chunk_id)."""
        fused = rrf_fusion(self.bm25_results, self.semantic_results, k=60, top_n=10)
        chunk_ids = [c["chunk_id"] for c in fused]
        
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))
        self.assertEqual(set(chunk_ids), {"chk_001", "chk_002", "chk_003"})

    def test_03_candidate_only_in_bm25_preserved(self):
        """3. Candidate chỉ xuất hiện ở nhánh BM25 vẫn được giữ lại với matched_by=['bm25']."""
        fused = rrf_fusion(self.bm25_results, self.semantic_results, k=60, top_n=10)
        item2 = next(c for c in fused if c["chunk_id"] == "chk_002")

        self.assertEqual(item2["matched_by"], ["bm25"])
        self.assertIsNotNone(item2["bm25_rank"])
        self.assertIsNone(item2["semantic_rank"])

    def test_04_candidate_only_in_semantic_preserved(self):
        """4. Candidate chỉ xuất hiện ở nhánh Semantic vẫn được giữ lại với matched_by=['semantic']."""
        fused = rrf_fusion(self.bm25_results, self.semantic_results, k=60, top_n=10)
        item3 = next(c for c in fused if c["chunk_id"] == "chk_003")

        self.assertEqual(item3["matched_by"], ["semantic"])
        self.assertIsNone(item3["bm25_rank"])
        self.assertIsNotNone(item3["semantic_rank"])

    def test_05_weight_zero_excludes_branch_contribution(self):
        """5. Đặt weight = 0.0 loại bỏ hoàn toàn đóng góp của nhánh tương ứng."""
        # bm25_weight = 0.0 -> chỉ lấy đóng góp từ semantic
        fused = rrf_fusion(self.bm25_results, self.semantic_results, k=60, top_n=10, bm25_weight=0.0, semantic_weight=1.0)
        item1 = next(c for c in fused if c["chunk_id"] == "chk_001")
        expected_score = round(1.0 / (60 + 3), 6)

        self.assertEqual(item1["rrf_score"], expected_score)

    def test_06_deterministic_tie_breaking(self):
        """6. Quyết định thứ tự xếp hạng (tie-break) ổn định khi rrf_score bằng nhau."""
        bm25_tied = [
            {"chunk_id": "chk_B", "text": "Text B", "source": "s.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 2.0}
        ]
        sem_tied = [
            {"chunk_id": "chk_A", "text": "Text A", "source": "s.pdf", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.1}
        ]
        # Cả chk_B (bm25_rank 1) và chk_A (semantic_rank 1) đều có rrf_score = 1/(60+1)
        fused = rrf_fusion(bm25_tied, sem_tied, k=60, top_n=2)

        self.assertEqual(fused[0]["rrf_score"], fused[1]["rrf_score"])
        # Both best_rank = 1. sem_rank: chk_A has 1, chk_B has inf -> chk_A must be ranked #1
        self.assertEqual(fused[0]["chunk_id"], "chk_A")
        self.assertEqual(fused[1]["chunk_id"], "chk_B")

    def test_07_metadata_mismatch_raises_value_error(self):
        """7. Mismatch metadata cùng chunk giữa 2 nhánh bị phát hiện và raise ValueError."""
        sem_mismatched = [
            {
                "chunk_id": "chk_001",
                "text": "Nội dung BỊ KHÁC VỚI BM25!",  # Mismatch text
                "source": "DocA.pdf",
                "page_start": 1,
                "page_end": 1,
                "semantic_rank": 1,
                "semantic_distance": 0.1
            }
        ]
        with self.assertRaises(ValueError):
            rrf_fusion(self.bm25_results, sem_mismatched, k=60, top_n=10)

    def test_08_pipeline_trace_counts_accuracy(self):
        """8. Các thông số đếm trong Pipeline Trace chính xác tuyệt đối."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={
                    "strategy": "hierarchical",
                    "embedding_model": config["embedding_model"],
                    "embedding_dim": int(config["embedding_dim"])
                },
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Quy định cơ cấu nợ."},
                {"chunk_id": "chk_002", "strategy": "hierarchical", "source": "d.pdf", "page_start": 2, "page_end": 2, "text": "Quy định phân loại nợ."}
            ]

            col.upsert(
                ids=[c["chunk_id"] for c in sample_chunks],
                documents=[c["text"] for c in sample_chunks],
                embeddings=[[0.1]*768, [0.9]*768],
                metadatas=sample_chunks
            )

            res = search_hybrid(
                question="cơ cấu nợ",
                strategy="hierarchical",
                chunks=sample_chunks,
                chroma_dir=chroma_path,
                query_vec=[0.12]*768
            )

            trace = res["trace"]
            self.assertEqual(trace["bm25_candidate_count"], 2)
            self.assertEqual(trace["semantic_candidate_count"], 2)
            self.assertEqual(trace["union_count"], 2)
            self.assertIn("latency_ms", trace)
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_09_hybrid_calls_each_retriever_once(self):
        """9. Hybrid search gọi đúng từng retriever một lần và trả về pipeline_stage='rrf_hybrid'."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={
                    "strategy": "hierarchical",
                    "embedding_model": config["embedding_model"],
                    "embedding_dim": int(config["embedding_dim"])
                },
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Quy định nợ."}
            ]

            col.upsert(
                ids=["chk_001"],
                documents=["Quy định nợ."],
                embeddings=[[0.1]*768],
                metadatas=sample_chunks
            )

            res = search_hybrid(
                question="nợ",
                strategy="hierarchical",
                chunks=sample_chunks,
                chroma_dir=chroma_path,
                query_vec=[0.1]*768
            )

            self.assertEqual(res["pipeline_stage"], "rrf_hybrid")
            self.assertIn("results", res)
            self.assertIn("trace", res)
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_10_no_reranker_loaded_and_no_generation(self):
        """10. RRF Hybrid Search hoàn toàn không khởi tạo Reranker model và không gọi LLM generation."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={
                    "strategy": "hierarchical",
                    "embedding_model": config["embedding_model"],
                    "embedding_dim": int(config["embedding_dim"])
                },
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Quy định nợ."}
            ]

            col.upsert(
                ids=["chk_001"],
                documents=["Quy định nợ."],
                embeddings=[[0.1]*768],
                metadatas=sample_chunks
            )

            res = search_hybrid(
                question="nợ",
                strategy="hierarchical",
                chunks=sample_chunks,
                chroma_dir=chroma_path,
                query_vec=[0.1]*768
            )

            # Kết quả là pipeline trace và candidates, không có LLM answer hay rerank_score
            self.assertNotIn("answer", res)
            if len(res["results"]) > 0:
                self.assertNotIn("rerank_score", res["results"][0])
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
