"""
Unit tests cho Evaluator Offline - Buổi 09
Kiểm thử offline các metrics của evaluate.py sử dụng patch mock.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import evaluate


class TestEvaluatorOffline(unittest.TestCase):

    @patch("evaluate.query_hierarchical_rag")
    @patch("evaluate.load_hierarchical_config")
    def test_01_evaluate_hierarchical_rag_offline(self, mock_load_config, mock_query_rag):
        """Kiểm thử offline toàn bộ luồng tính toán của evaluate_hierarchical_rag."""
        mock_load_config.return_value = {
            "embedding_model": "fake-emb",
            "generation_model": "fake-gen",
            "reranker_model": "fake-rerank"
        }
        
        # Giả lập kết quả trả về của RAG pipeline
        mock_res = {
            "status": "answered",
            "mode": "multi_parent",
            "accepted_evidence": [
                {
                    "parent_id": "2222ca0c27c03966936318eb670c7128",
                    "text": "Parent text",
                    "source": "TT_02_2023_NHNN.pdf",
                    "page_start": 1,
                    "page_end": 1
                }
            ],
            "child_hits": [
                {
                    "child_id": "TT_02_2023_NHNN:hierarchical:0009",
                    "text": "Child text"
                }
            ],
            "parent_candidates": [
                {
                    "parent_id": "2222ca0c27c03966936318eb670c7128",
                    "supporting_child_ids": ["TT_02_2023_NHNN:hierarchical:0009"]
                }
            ],
            "trace": {
                "api_calls": {"gemini_embedding": 2, "gemini_generation": 0},
                "stage_latencies": {"total_ms": 15.0}
            }
        }
        mock_query_rag.return_value = mock_res
        
        # Chạy evaluate
        report = evaluate.evaluate_hierarchical_rag(k=3)
        
        # Xác nhận các trường trong report
        self.assertIn("timestamp", report)
        self.assertIn("config_identity", report)
        self.assertIn("corpus_identity", report)
        self.assertIn("per_question_results", report)
        self.assertIn("aggregate_metrics", report)
        self.assertTrue(report["human_review_warning"])
        
        # Kiểm tra các modes
        for mode in ["single_flat", "multi_flat", "single_parent", "multi_parent"]:
            self.assertIn(mode, report["aggregate_metrics"])
            metrics = report["aggregate_metrics"][mode]
            self.assertIn("Child Recall@K", metrics)
            self.assertIn("Parent Recall@K", metrics)
            self.assertIn("MRR@K", metrics)
            self.assertIn("nDCG@K", metrics)
            self.assertIn("Mean Latency (ms)", metrics)
            self.assertIn("Mean Context Chars", metrics)
            self.assertIn("Mean Expansion Factor", metrics)
            self.assertIn("Embedding Call Count", metrics)
            self.assertIn("Generation Call Count", metrics)


if __name__ == "__main__":
    unittest.main()
