"""
Unit tests cho RRF Fusion & Hybrid Retrieval Stage - Buổi 08
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import rrf_fusion, search_hybrid


class TestRRFAndHybridSearch(unittest.TestCase):

    def setUp(self):
        self.bm25_sample = [
            {
                "chunk_id": "chk_001",
                "text": "Điều 7 cơ cấu nợ",
                "source": "TT02.pdf",
                "page_start": 1,
                "page_end": 2,
                "bm25_rank": 1,
                "bm25_score": 5.0
            },
            {
                "chunk_id": "chk_002",
                "text": "Điều 7 giữ nguyên nhóm nợ",
                "source": "TT02.pdf",
                "page_start": 2,
                "page_end": 3,
                "bm25_rank": 2,
                "bm25_score": 3.5
            }
        ]

        self.semantic_sample = [
            {
                "chunk_id": "chk_002",
                "text": "Điều 7 giữ nguyên nhóm nợ",
                "source": "TT02.pdf",
                "page_start": 2,
                "page_end": 3,
                "semantic_rank": 1,
                "semantic_distance": 0.10
            },
            {
                "chunk_id": "chk_003",
                "text": "Điều 6 trích lập dự phòng",
                "source": "TT02.pdf",
                "page_start": 3,
                "page_end": 4,
                "semantic_rank": 2,
                "semantic_distance": 0.25
            }
        ]

    def test_01_rrf_formula_arithmetic_accuracy(self):
        """1. Tính toán số học của công thức RRF chính xác từng phần thập phân."""
        # For chk_002: bm25_rank=2, sem_rank=1, k=60, w=1.0
        # rrf = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.032522
        res = rrf_fusion(self.bm25_sample, self.semantic_sample, rrf_k=60, w_bm25=1.0, w_sem=1.0)
        chk2 = next(c for c in res if c["chunk_id"] == "chk_002")
        expected_score = round(1.0 / 62.0 + 1.0 / 61.0, 6)
        self.assertEqual(chk2["rrf_score"], expected_score)

    def test_02_candidate_overlap_no_duplicate(self):
        """2. Candidate xuất hiện ở cả 2 nhánh không bị nhân bản (no duplicate chunk_id)."""
        res = rrf_fusion(self.bm25_sample, self.semantic_sample, rrf_k=60)
        chunk_ids = [c["chunk_id"] for c in res]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))
        self.assertEqual(len(res), 3)

    def test_03_candidate_only_in_bm25_preserved(self):
        """3. Candidate chỉ xuất hiện ở nhánh BM25 vẫn được giữ lại với matched_by=['bm25']."""
        res = rrf_fusion(self.bm25_sample, self.semantic_sample, rrf_k=60)
        chk1 = next(c for c in res if c["chunk_id"] == "chk_001")
        self.assertEqual(chk1["matched_by"], ["bm25"])
        self.assertIsNone(chk1["semantic_rank"])
        self.assertIsNone(chk1["semantic_distance"])

    def test_04_candidate_only_in_semantic_preserved(self):
        """4. Candidate chỉ xuất hiện ở nhánh Semantic vẫn được giữ lại với matched_by=['semantic']."""
        res = rrf_fusion(self.bm25_sample, self.semantic_sample, rrf_k=60)
        chk3 = next(c for c in res if c["chunk_id"] == "chk_003")
        self.assertEqual(chk3["matched_by"], ["semantic"])
        self.assertIsNone(chk3["bm25_rank"])
        self.assertIsNone(chk3["bm25_score"])

    def test_05_weight_zero_excludes_branch_contribution(self):
        """5. Đặt weight = 0.0 loại bỏ hoàn toàn đóng góp của nhánh tương ứng."""
        res = rrf_fusion(self.bm25_sample, self.semantic_sample, rrf_k=60, w_bm25=0.0, w_sem=1.0)
        chk1 = next(c for c in res if c["chunk_id"] == "chk_001")
        self.assertEqual(chk1["rrf_score"], 0.0)

    def test_06_deterministic_tie_breaking(self):
        """6. Quyết định thứ tự xếp hạng (tie-break) ổn định khi rrf_score bằng nhau."""
        bm25_tied = [{"chunk_id": "chk_Z", "text": "t1", "source": "s.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 1.0}]
        sem_tied = [{"chunk_id": "chk_A", "text": "t2", "source": "s.pdf", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.1}]
        # Same rank (1) -> same rrf_score (1/61)
        res = rrf_fusion(bm25_tied, sem_tied, rrf_k=60)
        self.assertEqual(res[0]["chunk_id"], "chk_A")
        self.assertEqual(res[1]["chunk_id"], "chk_Z")

    def test_07_metadata_mismatch_raises_value_error(self):
        """7. Mismatch metadata cùng chunk giữa 2 nhánh bị phát hiện và raise ValueError."""
        bad_sem = [
            {
                "chunk_id": "chk_001",
                "text": "Nội dung sai khác hoàn toàn",
                "source": "TT02.pdf",
                "page_start": 1,
                "page_end": 2,
                "semantic_rank": 1,
                "semantic_distance": 0.1
            }
        ]
        with self.assertRaises(ValueError):
            rrf_fusion(self.bm25_sample, bad_sem)

    def test_08_pipeline_trace_counts_accuracy(self):
        """8. Các thông số đếm trong Pipeline Trace chính xác tuyệt đối."""
        def mock_bm25(q, k):
            return self.bm25_sample

        def mock_sem(q, k):
            return self.semantic_sample

        res = search_hybrid("cơ cấu nợ", custom_bm25_retriever=mock_bm25, custom_semantic_retriever=mock_sem)
        trace = res["trace"]

        self.assertEqual(trace["bm25_candidate_count"], 2)
        self.assertEqual(trace["semantic_candidate_count"], 2)
        self.assertEqual(trace["union_count"], 3)
        self.assertEqual(trace["overlap_count"], 1)
        self.assertEqual(trace["fused_count"], 3)
        self.assertEqual(trace["pipeline_stage"], "rrf_hybrid")

    def test_09_hybrid_calls_each_retriever_once(self):
        """9. Hybrid search gọi đúng từng retriever một lần và trả về pipeline_stage='rrf_hybrid'."""
        called = {"bm25": 0, "sem": 0}

        def mock_bm25(q, k):
            called["bm25"] += 1
            return self.bm25_sample

        def mock_sem(q, k):
            called["sem"] += 1
            return self.semantic_sample

        res = search_hybrid("test", custom_bm25_retriever=mock_bm25, custom_semantic_retriever=mock_sem)
        self.assertEqual(called["bm25"], 1)
        self.assertEqual(called["sem"], 1)
        self.assertEqual(res["trace"]["pipeline_stage"], "rrf_hybrid")

    def test_10_no_reranker_loaded_and_no_generation(self):
        """10. RRF Hybrid Search hoàn toàn không khởi tạo Reranker model và không gọi LLM generation."""
        def mock_bm25(q, k):
            return self.bm25_sample

        def mock_sem(q, k):
            return self.semantic_sample

        res = search_hybrid("test", custom_bm25_retriever=mock_bm25, custom_semantic_retriever=mock_sem)
        self.assertNotIn("answer", res)
        self.assertNotIn("rerank_score", res["results"][0])


if __name__ == "__main__":
    unittest.main()
