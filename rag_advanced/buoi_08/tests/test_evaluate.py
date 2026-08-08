"""
Unit tests cho Evaluator Metrics (Recall@K, MRR@K, nDCG@K) và Evaluation Pipeline - Buổi 08
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from evaluate import (
    calculate_recall_at_k,
    calculate_mrr_at_k,
    calculate_ndcg_at_k,
    run_evaluation
)


class TestEvaluatorMetrics(unittest.TestCase):

    def test_01_recall_at_k_hand_calculated(self):
        """1. Kiểm tra Recall@K tính tay: Gold=['c2', 'c4'], Retrieved=['c1', 'c2', 'c3'], K=3 -> Recall=0.5."""
        retrieved = ["c1", "c2", "c3"]
        gold = ["c2", "c4"]
        recall = calculate_recall_at_k(retrieved, gold, k=3)
        self.assertAlmostEqual(recall, 0.5, places=4)

    def test_02_mrr_at_k_hand_calculated(self):
        """2. Kiểm tra MRR@K tính tay: Gold=['c3'], Retrieved=['c1', 'c2', 'c3'], K=3 -> MRR = 1/3."""
        retrieved = ["c1", "c2", "c3"]
        gold = ["c3"]
        mrr = calculate_mrr_at_k(retrieved, gold, k=3)
        self.assertAlmostEqual(mrr, 1.0 / 3.0, places=4)

    def test_03_ndcg_at_k_hand_calculated(self):
        """3. Kiểm tra nDCG@K tính tay: Gold=['c2'], Retrieved=['c1', 'c2', 'c3'], K=3 -> DCG = 1/log2(3), IDCG = 1 -> nDCG = 0.63093."""
        retrieved = ["c1", "c2", "c3"]
        gold = ["c2"]
        ndcg = calculate_ndcg_at_k(retrieved, gold, k=3)
        expected_ndcg = 1.0 / (math_log2(3))
        self.assertAlmostEqual(ndcg, expected_ndcg, places=4)

    def test_04_human_review_flag_generates_warning(self):
        """4. Tự động cảnh báo và không công nhận winner khi có needs_human_review=true trong câu hỏi."""
        def mock_bm25(q, k):
            return [{"chunk_id": "c1"}]

        res = run_evaluation(
            strategy="hierarchical",
            k=5,
            modes=["bm25"],
            custom_bm25_retriever=mock_bm25
        )

        report = res["report"]
        self.assertTrue(report["needs_human_review_warning"]["has_review_flag"])
        self.assertIn("CẢNH BÁO", report["needs_human_review_warning"]["message"])

    def test_05_query_failure_recorded_explicitly(self):
        """5. Lỗi truy xuất 1 query ghi nhận fail rõ ràng trong report, không nuốt lỗi âm thầm."""
        def mock_bad_retriever(q, k):
            raise RuntimeError("Lỗi truy xuất thử nghiệm")

        res = run_evaluation(
            strategy="hierarchical",
            k=5,
            modes=["bm25"],
            custom_bm25_retriever=mock_bad_retriever
        )

        query_res = res["report"]["results_by_mode"]["bm25"]["queries"][0]
        self.assertEqual(query_res["status"], "error")
        self.assertIn("Lỗi truy xuất thử nghiệm", query_res["error"])


def math_log2(x):
    import math
    return math.log2(x)


if __name__ == "__main__":
    unittest.main()
