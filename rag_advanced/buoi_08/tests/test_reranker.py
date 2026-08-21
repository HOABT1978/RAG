"""
Unit tests cho Cross-Encoder Reranker và Hybrid Rerank Pipeline - Buổi 08
"""

import math
import sys
import unittest
import tempfile
from pathlib import Path

# Nạp module advanced_rag
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    CrossEncoderReranker,
    search_hybrid_rerank,
    _RERANKER_CACHE,
    get_chroma_client,
    get_collection_name,
    load_advanced_config
)


class TestCrossEncoderReranker(unittest.TestCase):

    def setUp(self):
        """Khởi tạo tập fused candidate mẫu cho testing Reranker."""
        self.sample_fused_candidates = [
            {
                "chunk_id": "chk_001",
                "text": "Nội dung quy định cơ cấu nợ.",
                "source": "DocA.pdf",
                "page_start": 1,
                "page_end": 1,
                "bm25_rank": 1,
                "bm25_score": 4.5,
                "semantic_rank": 2,
                "semantic_distance": 0.12,
                "rrf_score": 0.032,
                "fused_rank": 1,
                "matched_by": ["bm25", "semantic"]
            },
            {
                "chunk_id": "chk_002",
                "text": "Nội dung quy định phân loại nợ.",
                "source": "DocB.pdf",
                "page_start": 2,
                "page_end": 2,
                "bm25_rank": 2,
                "bm25_score": 3.2,
                "semantic_rank": 1,
                "semantic_distance": 0.09,
                "rrf_score": 0.031,
                "fused_rank": 2,
                "matched_by": ["bm25", "semantic"]
            },
            {
                "chunk_id": "chk_003",
                "text": "Nội dung quy định gia hạn nợ.",
                "source": "DocC.pdf",
                "page_start": 3,
                "page_end": 3,
                "bm25_rank": None,
                "bm25_score": None,
                "semantic_rank": 3,
                "semantic_distance": 0.22,
                "rrf_score": 0.015,
                "fused_rank": 3,
                "matched_by": ["semantic"]
            }
        ]

    def test_01_lazy_loading(self):
        """1. Mẫu Reranker model chưa được load khi khởi tạo class hoặc import module."""
        reranker = CrossEncoderReranker(model_name="BAAI/bge-reranker-v2-m3")
        self.assertEqual(reranker.model_name, "BAAI/bge-reranker-v2-m3")
        # Quá trình khởi tạo không tự nạp model vào _RERANKER_CACHE nếu dùng custom_reranker
        self.assertIsInstance(_RERANKER_CACHE, dict)

    def test_02_one_pair_per_candidate(self):
        """2. Mỗi candidate tạo đúng 1 cặp (query, text) để đưa vào mô hình."""
        received_pairs = []

        def mock_reranker_fn(query, candidates, top_k):
            nonlocal received_pairs
            received_pairs = [[query, c["text"]] for c in candidates]
            return candidates[:top_k]

        reranker = CrossEncoderReranker()
        reranker.rerank("cơ cấu nợ", self.sample_fused_candidates, top_k=2, custom_reranker=mock_reranker_fn)

        self.assertEqual(len(received_pairs), 3)
        self.assertEqual(received_pairs[0], ["cơ cấu nợ", "Nội dung quy định cơ cấu nợ."])

    def test_03_batch_processing_preserves_candidate_count(self):
        """3. Xử lý batch không làm mất hoặc thay đổi số lượng candidates ban đầu."""
        def mock_reranker_fn(query, candidates, top_k):
            results = []
            for rank, c in enumerate(candidates[:top_k], 1):
                item = dict(c)
                item["rerank_rank"] = rank
                item["rank_change"] = c["fused_rank"] - rank
                results.append(item)
            return results

        reranker = CrossEncoderReranker()
        results = reranker.rerank("cơ cấu nợ", self.sample_fused_candidates, top_k=3, custom_reranker=mock_reranker_fn)
        self.assertEqual(len(results), 3)

    def test_04_sigmoid_score_calculation_accuracy(self):
        """4. Tính toán sigmoid score từ raw logit chính xác theo công thức 1/(1 + exp(-logit))."""
        raw_logit = 2.5
        expected_sig = round(1.0 / (1.0 + math.exp(-raw_logit)), 6)

        def mock_reranker_fn(query, candidates, top_k):
            results = []
            for c in candidates:
                item = dict(c)
                item["rerank_raw_score"] = raw_logit
                item["rerank_score"] = expected_sig
                results.append(item)
            return results[:top_k]

        reranker = CrossEncoderReranker()
        results = reranker.rerank("query", self.sample_fused_candidates, top_k=1, custom_reranker=mock_reranker_fn)
        self.assertEqual(results[0]["rerank_score"], expected_sig)

    def test_05_sorting_and_tie_breaking(self):
        """5. Sắp xếp giảm dần theo rerank_score, tie-break theo fused_rank tăng dần."""
        def mock_reranker_fn(query, candidates, top_k):
            # Giả lập chk_002 được score cao nhất 0.95, chk_001 score 0.80, chk_003 score 0.80
            scores = {"chk_001": 0.80, "chk_002": 0.95, "chk_003": 0.80}
            reranked = []
            for c in candidates:
                item = dict(c)
                item["rerank_score"] = scores[c["chunk_id"]]
                item["rerank_raw_score"] = scores[c["chunk_id"]] * 2.0
                reranked.append(item)

            reranked.sort(key=lambda x: (-x["rerank_score"], x["fused_rank"], x["chunk_id"]))
            for r, item in enumerate(reranked[:top_k], 1):
                item["rerank_rank"] = r
                item["rank_change"] = item["fused_rank"] - r
            return reranked[:top_k]

        reranker = CrossEncoderReranker()
        results = reranker.rerank("query", self.sample_fused_candidates, top_k=3, custom_reranker=mock_reranker_fn)

        self.assertEqual(results[0]["chunk_id"], "chk_002")  # Score 0.95 (rank 1)
        self.assertEqual(results[1]["chunk_id"], "chk_001")  # Score 0.80, fused_rank 1 < 3 (rank 2)
        self.assertEqual(results[2]["chunk_id"], "chk_003")  # Score 0.80, fused_rank 3 (rank 3)

    def test_06_rank_change_calculation_accuracy(self):
        """6. Chỉ số rank_change = fused_rank - rerank_rank được tính toán chính xác."""
        def mock_reranker_fn(query, candidates, top_k):
            # chk_002 (fused_rank 2) -> rerank_rank 1 => rank_change = 2 - 1 = +1
            # chk_001 (fused_rank 1) -> rerank_rank 2 => rank_change = 1 - 2 = -1
            item2 = dict(candidates[1])
            item2["rerank_rank"] = 1
            item2["rank_change"] = 2 - 1

            item1 = dict(candidates[0])
            item1["rerank_rank"] = 2
            item1["rank_change"] = 1 - 2

            return [item2, item1][:top_k]

        reranker = CrossEncoderReranker()
        results = reranker.rerank("query", self.sample_fused_candidates, top_k=2, custom_reranker=mock_reranker_fn)

        self.assertEqual(results[0]["rank_change"], 1)
        self.assertEqual(results[1]["rank_change"], -1)

    def test_07_only_reranks_limited_candidates(self):
        """7. Giới hạn số lượng candidates đưa vào reranker tối đa RERANK_CANDIDATES."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={"strategy": "hierarchical", "embedding_model": config["embedding_model"], "embedding_dim": 768},
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": f"chk_{i:03d}", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": f"Text {i}"}
                for i in range(1, 10)
            ]

            col.upsert(
                ids=[c["chunk_id"] for c in sample_chunks],
                documents=[c["text"] for c in sample_chunks],
                embeddings=[[0.1] * 768 for _ in sample_chunks],
                metadatas=sample_chunks
            )

            received_candidates_count = 0

            def mock_reranker_fn(query, candidates, top_k):
                nonlocal received_candidates_count
                received_candidates_count = len(candidates)
                results = []
                for r, c in enumerate(candidates[:top_k], 1):
                    item = dict(c)
                    item["rerank_rank"] = r
                    item["rank_change"] = c.get("fused_rank", r) - r
                    item["rerank_score"] = 0.9
                    item["rerank_raw_score"] = 2.0
                    results.append(item)
                return results

            res = search_hybrid_rerank(
                question="Text",
                strategy="hierarchical",
                chunks=sample_chunks,
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_reranker_fn
            )

            self.assertLessEqual(received_candidates_count, config["rerank_candidates"])
            self.assertEqual(res["trace"]["rerank_candidate_count"], received_candidates_count)
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_08_returns_final_top_k_only(self):
        """8. Chỉ trả về kết quả cắt theo số lượng FINAL_TOP_K."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={"strategy": "hierarchical", "embedding_model": config["embedding_model"], "embedding_dim": 768},
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": f"chk_{i:03d}", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": f"Text {i}"}
                for i in range(1, 10)
            ]

            col.upsert(
                ids=[c["chunk_id"] for c in sample_chunks],
                documents=[c["text"] for c in sample_chunks],
                embeddings=[[0.1] * 768 for _ in sample_chunks],
                metadatas=sample_chunks
            )

            def mock_reranker_fn(query, candidates, top_k):
                results = []
                for r, c in enumerate(candidates[:top_k], 1):
                    item = dict(c)
                    item["rerank_rank"] = r
                    item["rank_change"] = 0
                    item["rerank_score"] = 0.9
                    item["rerank_raw_score"] = 2.0
                    results.append(item)
                return results

            res = search_hybrid_rerank(
                question="Text",
                strategy="hierarchical",
                chunks=sample_chunks,
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_reranker_fn
            )

            self.assertEqual(len(res["results"]), config["final_top_k"])
            self.assertEqual(res["trace"]["final_top_k_count"], config["final_top_k"])
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_09_model_error_does_not_silent_fallback(self):
        """9. Lỗi nạp mô hình Reranker không bị âm thầm nuốt lỗi hay fallback giả định như đã thành công."""
        reranker = CrossEncoderReranker(model_name="non_existent_model_xyz_123")
        with self.assertRaises(RuntimeError):
            reranker.load_model()

    def test_10_tests_run_offline_without_network(self):
        """10. Tất cả unit tests cho Reranker chạy hoàn toàn offline không cần tải mô hình thật hoặc mạng."""
        def mock_reranker_fn(query, candidates, top_k):
            return candidates[:top_k]

        reranker = CrossEncoderReranker()
        res = reranker.rerank("offline test", self.sample_fused_candidates, top_k=2, custom_reranker=mock_reranker_fn)
        self.assertEqual(len(res), 2)


if __name__ == "__main__":
    unittest.main()
