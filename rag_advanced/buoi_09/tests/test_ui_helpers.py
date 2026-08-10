"""
Unit tests cho UI Helper - Buổi 09
Kiểm thử offline các hàm định dạng hiển thị, xử lý ma trận và cây phân cấp.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ui_helpers import (
    citation_formatting,
    query_child_matrix,
    parent_tree_data,
    mode_comparison_row,
    warning_status_mapping
)


class TestUIHelpers(unittest.TestCase):

    def test_citation_formatting_flat(self):
        """Kiểm thử citation_formatting ở chế độ Flat."""
        citation = {
            "evidence_id": "E1",
            "source": "TT_02.pdf",
            "page_start": 2,
            "page_end": 2,
            "child_id": "chk_001",
            "rerank_score": 0.85421
        }
        res = citation_formatting(citation)
        self.assertIn("[E1]", res)
        self.assertIn("TT_02.pdf", res)
        self.assertIn("Trang 2", res)
        self.assertIn("Chunk: chk_001", res)
        self.assertIn("Score: 0.8542", res)

    def test_citation_formatting_parent(self):
        """Kiểm thử citation_formatting ở chế độ Parent."""
        citation = {
            "evidence_id": "P1",
            "source": "TT_39.pdf",
            "page_start": 3,
            "page_end": 5,
            "parent_id": "parent_doc_1",
            "structural_path": {
                "chapter": "Chương II",
                "article": "Điều 5"
            },
            "parent_rerank_score": 0.91234,
            "supporting_child_ids": ["c1", "c2"],
            "warnings": ["oversized_single_child"]
        }
        res = citation_formatting(citation)
        self.assertIn("[P1]", res)
        self.assertIn("TT_39.pdf", res)
        self.assertIn("Trang 3-5", res)
        self.assertIn("Chương: Chương II", res)
        self.assertIn("Điều: Điều 5", res)
        self.assertIn("Score: 0.9123", res)
        self.assertIn("Chunks: c1, c2", res)
        self.assertIn("⚠️ oversized_single_child", res)

    def test_query_child_matrix(self):
        """Kiểm thử sinh ma trận Query-Child."""
        child_hits = [
            {
                "child_id": "c1",
                "multi_query_rrf_score": 0.0452,
                "support_query_count": 2,
                "per_query_ranks": {"Q0": 1, "Q1": 3}
            },
            {
                "child_id": "c2",
                "multi_query_rrf_score": 0.0150,
                "support_query_count": 1,
                "per_query_ranks": {"Q0": 5}
            }
        ]
        query_list = [
            {"query_id": "Q0", "text": "Q0 text"},
            {"query_id": "Q1", "text": "Q1 text"},
            {"query_id": "Q2", "text": "Q2 text"}
        ]
        res = query_child_matrix(child_hits, query_list)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["Child ID"], "c1")
        self.assertEqual(res[0]["Q0"], "#1")
        self.assertEqual(res[0]["Q1"], "#3")
        self.assertEqual(res[0]["Q2"], "—")
        self.assertEqual(res[0]["MQ-RRF Score"], 0.0452)
        
        self.assertEqual(res[1]["Child ID"], "c2")
        self.assertEqual(res[1]["Q0"], "#5")
        self.assertEqual(res[1]["Q1"], "—")
        self.assertEqual(res[1]["Q2"], "—")

    def test_parent_tree_data(self):
        """Kiểm thử ánh xạ cấu trúc cây cha-con."""
        accepted_parents = [
            {
                "parent_id": "p1",
                "source": "s1.pdf",
                "page_start": 1,
                "page_end": 2,
                "parent_rank": 1,
                "parent_rerank_rank": 2,
                "parent_rrf_score": 0.032,
                "parent_rerank_score": 0.85,
                "text": "Parent text node",
                "structural_path": {"article": "Điều 1"},
                "supporting_child_ids": ["c1", "c2"]
            }
        ]
        child_hits = [
            {
                "child_id": "c1",
                "text": "Child text one",
                "per_query_ranks": {"Q0": 1}
            },
            {
                "child_id": "c2",
                "text": "Child text two that is very long" * 10,
                "per_query_ranks": {"Q1": 2}
            }
        ]
        tree = parent_tree_data(accepted_parents, child_hits)
        self.assertEqual(len(tree), 1)
        p_node = tree[0]
        self.assertEqual(p_node["parent_id"], "p1")
        self.assertEqual(p_node["rank_change"], "Rank: 1 ➔ 2")
        self.assertEqual(p_node["score_change"], "Score: 0.032 ➔ 0.85")
        self.assertEqual(len(p_node["children"]), 2)
        
        c1_node = p_node["children"][0]
        self.assertEqual(c1_node["child_id"], "c1")
        self.assertEqual(c1_node["query_ranks"], "Q0:#1")
        self.assertEqual(c1_node["anchor_snippet"], "Child text one")
        
        c2_node = p_node["children"][1]
        self.assertEqual(c2_node["child_id"], "c2")
        self.assertEqual(c2_node["query_ranks"], "Q1:#2")
        self.assertTrue(c2_node["anchor_snippet"].endswith("..."))

    def test_mode_comparison_row(self):
        """Kiểm thử mode_comparison_row."""
        run_res = {
            "status": "answered",
            "accepted_evidence": [
                {
                    "parent_id": "p1",
                    "text": "Accepted parent text",
                    "source": "s1.pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "parent_rank": 1,
                    "parent_rerank_rank": 1,
                    "best_child_rank": 1,
                    "warnings": []
                }
            ],
            "child_hits": [
                {"child_id": "c1", "text": "Child text", "multi_query_rank": 1}
            ],
            "parent_candidates": [
                {"parent_id": "p1"}
            ],
            "trace": {
                "api_calls": {"gemini_embedding": 1, "gemini_generation": 1},
                "stage_latencies": {"total_ms": 120.5}
            }
        }
        row = mode_comparison_row("multi_parent", run_res)
        self.assertEqual(row["Mode"], "multi_parent")
        self.assertEqual(row["Status"], "answered")
        self.assertEqual(row["Unit Type"], "Parent")
        self.assertEqual(row["Evidence IDs"], "P1:p1")
        self.assertIn("Raw:1, Rerank:1, BestChild:1", row["Ranks"])
        self.assertEqual(row["Sources/Pages"], "s1.pdf (p.1)")
        self.assertEqual(row["Context Chars"], len("Accepted parent text"))
        self.assertEqual(row["Latency (ms)"], 120.5)
        self.assertEqual(row["Embedding Calls"], 1)
        self.assertEqual(row["Generation Calls"], 1)

    def test_warning_status_mapping(self):
        """Kiểm thử warning_status_mapping."""
        warnings = ["oversized_single_child", "first_parent_oversized_context_limit", "mâu thuẫn xảy ra"]
        mapped = warning_status_mapping("insufficient_evidence", warnings)
        
        self.assertEqual(mapped["title"], "Không đủ bằng chứng")
        self.assertEqual(mapped["type"], "warning")
        self.assertIn("RERANK_MIN_SCORE", mapped["action"])
        self.assertEqual(len(mapped["warnings"]), 3)
        self.assertIn("oversized_single_child", mapped["warnings"][0])
        self.assertIn("first_parent_oversized_context_limit", mapped["warnings"][1])
        self.assertIn("mâu thuẫn xảy ra", mapped["warnings"][2])


if __name__ == "__main__":
    unittest.main()
