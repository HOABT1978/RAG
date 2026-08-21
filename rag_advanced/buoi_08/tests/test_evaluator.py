"""
Unit tests cho Evaluator Framework và Metric Formulas - Buổi 08
"""

import os
import sys
import json
import unittest
import tempfile
from pathlib import Path

# Nạp module evaluate
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from evaluate import (
    calculate_recall_at_k,
    calculate_mrr_at_k,
    calculate_ndcg_at_k,
    calculate_p50,
    evaluate_dataset
)


class TestEvaluatorMetrics(unittest.TestCase):

    def test_01_recall_at_k_arithmetic(self):
        """1. Kiểm tra tính toán Recall@K bằng tay: hits / len(gold)."""
        retrieved = ["chunk_A", "chunk_B", "chunk_C", "chunk_D", "chunk_E"]
        gold = ["chunk_B", "chunk_X"]

        # In top-3: ["chunk_A", "chunk_B", "chunk_C"], hits = 1 (chunk_B). Recall@3 = 1 / 2 = 0.5
        recall3 = calculate_recall_at_k(retrieved, gold, k=3)
        self.assertEqual(recall3, 0.5)

        # In top-5: hits = 1 (chunk_B). Recall@5 = 1 / 2 = 0.5
        recall5 = calculate_recall_at_k(retrieved, gold, k=5)
        self.assertEqual(recall5, 0.5)

    def test_02_mrr_at_k_arithmetic(self):
        """2. Kiểm tra tính toán MRR@K bằng tay: 1 / rank vị trí phù hợp đầu tiên."""
        retrieved = ["chunk_A", "chunk_B", "chunk_C"]
        gold = ["chunk_B"]

        # rank of chunk_B is 2 -> MRR@3 = 1 / 2 = 0.5
        mrr = calculate_mrr_at_k(retrieved, gold, k=3)
        self.assertEqual(mrr, 0.5)

        # Non-matching gold -> MRR = 0.0
        mrr_zero = calculate_mrr_at_k(retrieved, ["chunk_Z"], k=3)
        self.assertEqual(mrr_zero, 0.0)

    def test_03_ndcg_at_k_arithmetic(self):
        """3. Kiểm tra tính toán nDCG@K bằng tay với binary relevance."""
        # Item 1 is relevant -> DCG@1 = 1 / log2(2) = 1.0, IDCG@1 = 1.0 -> nDCG@1 = 1.0
        retrieved = ["chunk_A", "chunk_B"]
        gold = ["chunk_A"]

        ndcg1 = calculate_ndcg_at_k(retrieved, gold, k=1)
        self.assertEqual(ndcg1, 1.0)

        # Item 2 is relevant -> DCG@2 = 0 + 1 / log2(3) = 0.6309297, IDCG@2 = 1 / log2(2) = 1.0 -> nDCG@2 = 0.63093
        retrieved2 = ["chunk_X", "chunk_A"]
        ndcg2 = calculate_ndcg_at_k(retrieved2, gold, k=2)
        self.assertAlmostEqual(ndcg2, 0.63093, places=4)

    def test_04_calculate_p50(self):
        """4. Kiểm tra tính toán vị trí P50 (median) latency."""
        values_odd = [10.0, 30.0, 20.0]
        self.assertEqual(calculate_p50(values_odd), 20.0)

        values_even = [10.0, 20.0, 30.0, 40.0]
        self.assertEqual(calculate_p50(values_even), 25.0)

    def test_05_evaluate_dataset_offline_runner(self):
        """5. Thực thi evaluate_dataset chạy 100% offline với mock custom retrievers và kiểm tra report JSON."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            questions_file = Path(temp_dir.name) / "questions_test.json"
            sample_questions = [
                {
                    "query_id": "Q01",
                    "question": "Quy định cơ cấu nợ?",
                    "relevant_chunk_ids": ["chk_001"],
                    "needs_human_review": True
                }
            ]

            with open(questions_file, "w", encoding="utf-8") as f:
                json.dump(sample_questions, f, ensure_ascii=False)

            def mock_retriever(query, top_k):
                return ["chk_001", "chk_002"]

            custom_retrievers = {
                "bm25": mock_retriever,
                "hybrid": mock_retriever
            }

            report = evaluate_dataset(
                questions_path=questions_file,
                modes=["bm25", "hybrid"],
                strategy="hierarchical",
                top_k=2,
                custom_retrievers=custom_retrievers
            )

            self.assertIn("timestamp", report)
            self.assertIn("results_by_mode", report)
            self.assertTrue(report["needs_human_review_warning"]["has_review_flag"])
            self.assertFalse(report["official_winner_declared"])
            self.assertEqual(report["results_by_mode"]["bm25"]["recall_at_k"], 1.0)
            self.assertEqual(report["results_by_mode"]["bm25"]["mrr_at_k"], 1.0)
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
