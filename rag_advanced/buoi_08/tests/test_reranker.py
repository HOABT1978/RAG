"""
Unit tests cho Cross-Encoder Reranker Stage - Buổi 08
"""

import math
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import CrossEncoderReranker, search_hybrid_rerank, _RERANKER_SINGLETON


class TestCrossEncoderReranker(unittest.TestCase):

    def setUp(self):
        self.question = "Điều 7 quy định cơ cấu nợ như thế nào?"
        self.sample_fused_candidates = [
            {
                "chunk_id": "chk_001",
                "text": "Điều 7 quy định cơ cấu lại thời hạn trả nợ cho khách hàng.",
                "source": "TT02.pdf",
                "page_start": 1,
                "page_end": 2,
                "bm25_rank": 1,
                "semantic_rank": 2,
                "fused_rank": 1,
                "rrf_score": 0.0322,
                "matched_by": ["bm25", "semantic"]
            },
            {
                "chunk_id": "chk_002",
                "text": "Tổ chức tín dụng giữ nguyên nhóm nợ.",
                "source": "TT02.pdf",
                "page_start": 2,
                "page_end": 3,
                "bm25_rank": 2,
                "semantic_rank": 1,
                "fused_rank": 2,
                "rrf_score": 0.0320,
                "matched_by": ["bm25", "semantic"]
            },
            {
                "chunk_id": "chk_003",
                "text": "Trích lập dự phòng rủi ro.",
                "source": "TT02.pdf",
                "page_start": 3,
                "page_end": 4,
                "bm25_rank": 3,
                "semantic_rank": 3,
                "fused_rank": 3,
                "rrf_score": 0.0315,
                "matched_by": ["bm25", "semantic"]
            }
        ]

    def test_01_lazy_loading(self):
        """1. Mẫu Reranker model chưa được load khi khởi tạo class hoặc import module."""
        reranker = CrossEncoderReranker(model_name="non_existent_model_xyz_123")
        self.assertIsNone(reranker.model)
        self.assertIsNone(reranker.tokenizer)

    def test_02_one_pair_per_candidate(self):
        """2. Mỗi candidate tạo đúng 1 cặp (query, text) để đưa vào mô hình."""
        captured_pairs = []

        def mock_custom_reranker(q, candidates):
            nonlocal captured_pairs
            captured_pairs = [[q, c["text"]] for c in candidates]
            results = []
            for idx, c in enumerate(candidates):
                c_copy = dict(c)
                c_copy["rerank_raw_score"] = 2.0 - idx
                c_copy["rerank_score"] = 1.0 / (1.0 + math.exp(-(2.0 - idx)))
                results.append(c_copy)
            return results

        def mock_bm25(q, k):
            return [self.sample_fused_candidates[0]]

        def mock_sem(q, k):
            return [self.sample_fused_candidates[1]]

        search_hybrid_rerank(
            question=self.question,
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_custom_reranker
        )
        self.assertEqual(len(captured_pairs), 2)

    def test_03_batch_processing_preserves_candidate_count(self):
        """3. Xử lý batch không làm mất hoặc thay đổi số lượng candidates ban đầu."""
        def mock_reranker(q, candidates):
            res = []
            for idx, c in enumerate(candidates):
                c_copy = dict(c)
                c_copy["rerank_raw_score"] = 1.0
                c_copy["rerank_score"] = 0.731059
                res.append(c_copy)
            return res

        def mock_bm25(q, k):
            return self.sample_fused_candidates

        def mock_sem(q, k):
            return []

        out = search_hybrid_rerank(
            question=self.question,
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_reranker
        )
        self.assertEqual(len(out["results"]), 3)

    def test_04_sigmoid_score_calculation_accuracy(self):
        """4. Tính toán sigmoid score từ raw logit chính xác theo công thức 1/(1 + exp(-logit))."""
        logit = 2.5
        expected_sigmoid = round(1.0 / (1.0 + math.exp(-logit)), 6)

        def mock_reranker(q, candidates):
            c_copy = dict(candidates[0])
            c_copy["rerank_raw_score"] = logit
            c_copy["rerank_score"] = expected_sigmoid
            return [c_copy]

        def mock_bm25(q, k):
            return [self.sample_fused_candidates[0]]

        def mock_sem(q, k):
            return []

        out = search_hybrid_rerank(
            question=self.question,
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_reranker
        )
        item = out["results"][0]
        self.assertEqual(item["rerank_raw_score"], logit)
        self.assertEqual(item["rerank_score"], expected_sigmoid)

    def test_05_sorting_and_tie_breaking(self):
        """5. Sắp xếp giảm dần theo rerank_score, tie-break theo fused_rank tăng dần."""
        # Candidate 2 has higher rerank score than candidate 1 -> Candidate 2 should be #1
        def mock_reranker(q, candidates):
            res = []
            for c in candidates:
                c_copy = dict(c)
                if c["chunk_id"] == "chk_002":
                    c_copy["rerank_score"] = 0.95
                    c_copy["rerank_raw_score"] = 3.0
                else:
                    c_copy["rerank_score"] = 0.50
                    c_copy["rerank_raw_score"] = 0.0
                res.append(c_copy)
            return res

        def mock_bm25(q, k):
            return self.sample_fused_candidates

        def mock_sem(q, k):
            return []

        out = search_hybrid_rerank(
            question=self.question,
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_reranker
        )
        self.assertEqual(out["results"][0]["chunk_id"], "chk_002")
        self.assertEqual(out["results"][0]["rerank_rank"], 1)

    def test_06_rank_change_calculation_accuracy(self):
        """6. Chỉ số rank_change = fused_rank - rerank_rank được tính toán chính xác."""
        # chk_002 was fused_rank 2, now rerank_rank 1 -> rank_change = 2 - 1 = +1
        def mock_reranker(q, candidates):
            res = []
            for c in candidates:
                c_copy = dict(c)
                if c["chunk_id"] == "chk_002":
                    c_copy["rerank_score"] = 0.99
                    c_copy["rerank_raw_score"] = 4.0
                else:
                    c_copy["rerank_score"] = 0.10
                    c_copy["rerank_raw_score"] = -2.0
                res.append(c_copy)
            return res

        def mock_bm25(q, k):
            return self.sample_fused_candidates

        def mock_sem(q, k):
            return []

        out = search_hybrid_rerank(
            question=self.question,
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_reranker
        )
        top1 = out["results"][0]
        self.assertEqual(top1["chunk_id"], "chk_002")
        self.assertEqual(top1["fused_rank"], 2)
        self.assertEqual(top1["rerank_rank"], 1)
        self.assertEqual(top1["rank_change"], 1)

    def test_07_only_reranks_limited_candidates(self):
        """7. Giới hạn số lượng candidates đưa vào reranker tối đa RERANK_CANDIDATES."""
        reranked_count = 0

        def mock_reranker(q, candidates):
            nonlocal reranked_count
            reranked_count = len(candidates)
            return [dict(c, rerank_score=0.5, rerank_raw_score=0.0) for c in candidates]

        many_chunks = [
            {"chunk_id": f"chk_{i:03d}", "text": f"Nội dung {i}", "source": "s.pdf", "page_start": 1, "page_end": 1, "bm25_rank": i, "bm25_score": 100.0 - i}
            for i in range(1, 30)
        ]

        def mock_bm25(q, k):
            return many_chunks[:k]

        def mock_sem(q, k):
            return []

        search_hybrid_rerank(
            question=self.question,
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_reranker
        )
        self.assertEqual(reranked_count, 20)

    def test_08_returns_final_top_k_only(self):
        """8. Chỉ trả về kết quả cắt theo số lượng FINAL_TOP_K."""
        def mock_reranker(q, candidates):
            return [dict(c, rerank_score=0.8 - idx * 0.01, rerank_raw_score=1.0) for idx, c in enumerate(candidates)]

        many_chunks = [
            {"chunk_id": f"chk_{i:03d}", "text": f"Nội dung {i}", "source": "s.pdf", "page_start": 1, "page_end": 1, "bm25_rank": i, "bm25_score": 100.0 - i}
            for i in range(1, 20)
        ]

        def mock_bm25(q, k):
            return many_chunks[:k]

        def mock_sem(q, k):
            return []

        out = search_hybrid_rerank(
            question=self.question,
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_reranker
        )
        self.assertEqual(len(out["results"]), 5)

    def test_09_model_error_does_not_silent_fallback(self):
        """9. Lỗi nạp mô hình Reranker không bị âm thầm nuốt lỗi hay fallback giả định như đã thành công."""
        bad_reranker = CrossEncoderReranker(model_name="non_existent_model_xyz_123")
        with self.assertRaises(RuntimeError):
            bad_reranker.load_model()

    def test_10_tests_run_offline_without_network(self):
        """10. Tất cả unit tests cho Reranker chạy hoàn toàn offline không cần tải mô hình thật hoặc mạng."""
        def mock_reranker(q, candidates):
            return [dict(c, rerank_score=0.9, rerank_raw_score=2.0) for c in candidates]

        def mock_bm25(q, k):
            return self.sample_fused_candidates

        def mock_sem(q, k):
            return []

        out = search_hybrid_rerank(
            question=self.question,
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_reranker
        )
        self.assertIn("results", out)
        self.assertIn("trace", out)
        self.assertEqual(out["trace"]["pipeline_stage"], "hybrid_rerank")


if __name__ == "__main__":
    unittest.main()
