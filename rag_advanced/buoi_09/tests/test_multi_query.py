"""
Unit tests cho Multi-Query Hybrid Retrieval và Cross-Query RRF - Buổi 09
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import retrieve_multi_query_hybrid


class TestMultiQueryRetrieval(unittest.TestCase):

    def test_01_mq_rrf_formula_calculation_and_weights(self):
        """1 & 2. Công thức MQ-RRF tính tay, áp dụng trọng số original/variant chính xác."""
        def fake_generator(q):
            return {
                "queries": [
                    {"text": "Q1_query", "focus": "paraphrase"}
                ]
            }

        def fake_bm25(question, limit):
            if question == "Vay vốn?":
                return [
                    {"chunk_id": "c1", "text": "t1", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0},
                    {"chunk_id": "c2", "text": "t2", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 2, "bm25_score": 8.0}
                ]
            elif question == "Q1_query":
                return [
                    {"chunk_id": "c1", "text": "t1", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}
                ]
            return []

        res = retrieve_multi_query_hybrid(
            question="Vay vốn?",
            custom_query_generator=fake_generator,
            custom_bm25_retriever=fake_bm25,
            custom_semantic_retriever=lambda q, k: []
        )
        
        results = res["results"]
        self.assertEqual(results[0]["child_id"], "c1")
        # Điểm c1 = 1.5 / (60 + 1) + 1.0 / (60 + 1) = 2.5 / 61 = 0.040984
        self.assertEqual(results[0]["multi_query_rrf_score"], 0.040984)
        self.assertEqual(results[1]["child_id"], "c2")
        # Điểm c2 = 1.5 / (60 + 2) = 1.5/62 = 0.024194
        self.assertEqual(results[1]["multi_query_rrf_score"], 0.024194)

    def test_03_deduplicate_union_and_missing_query(self):
        """3, 4 & 5. Hợp nhất không trùng lặp, giữ đóng góp từ query riêng biệt, tính support count/ids."""
        def fake_generator(q):
            return {
                "queries": [
                    {"text": "Q1_query", "focus": "paraphrase"}
                ]
            }

        def fake_bm25(question, limit):
            if question == "Test": # Q0
                return [{"chunk_id": "c1", "text": "t1", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}]
            elif question == "Q1_query": # Q1
                return [{"chunk_id": "c2", "text": "t2", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}]
            return []

        res = retrieve_multi_query_hybrid(
            question="Test",
            custom_query_generator=fake_generator,
            custom_bm25_retriever=fake_bm25,
            custom_semantic_retriever=lambda q, k: []
        )
        self.assertEqual(len(res["results"]), 2)
        c1 = next(x for x in res["results"] if x["child_id"] == "c1")
        c2 = next(x for x in res["results"] if x["child_id"] == "c2")
        self.assertEqual(c1["support_query_count"], 1)
        self.assertEqual(c1["support_query_ids"], ["Q0"])
        self.assertEqual(c2["support_query_count"], 1)
        self.assertEqual(c2["support_query_ids"], ["Q1"])

    def test_06_metadata_mismatch_fails(self):
        """6. Metadata của cùng child không khớp giữa các query sẽ báo lỗi ValueError."""
        def fake_generator(q):
            return {
                "queries": [
                    {"text": "Q1_query", "focus": "paraphrase"}
                ]
            }

        def fake_bm25(question, limit):
            if question == "Test Mismatch":
                return [{"chunk_id": "c1", "text": "Nội dung cũ", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}]
            elif question == "Q1_query":
                return [{"chunk_id": "c1", "text": "Nội dung MỚI", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}]
            return []

        with self.assertRaises(ValueError):
            retrieve_multi_query_hybrid(
                question="Test Mismatch",
                custom_query_generator=fake_generator,
                custom_bm25_retriever=fake_bm25,
                custom_semantic_retriever=lambda q, k: []
            )

    def test_08_q0_failure_fails_entire_pipeline(self):
        """10. Lỗi ở Q0 làm toàn bộ pipeline thất bại."""
        def fake_generator(q):
            return {
                "queries": [
                    {"text": "Q1_query", "focus": "paraphrase"}
                ]
            }

        def fake_bm25(question, limit):
            raise RuntimeError("Chroma connection timeout")

        with self.assertRaises(ValueError):
            retrieve_multi_query_hybrid(
                question="Lỗi Q0",
                custom_query_generator=fake_generator,
                custom_bm25_retriever=fake_bm25,
                custom_semantic_retriever=lambda q, k: []
            )

    def test_09_generated_query_failure_returns_partial_status(self):
        """10. Lỗi ở generated query trả về status 'partial' hoặc 'multi_query_partial'."""
        def fake_generator(q):
            return {
                "queries": [
                    {"text": "Q1_query", "focus": "paraphrase"},
                    {"text": "Q2_query", "focus": "exact_legal_terms"}
                ]
            }

        def fake_bm25(question, limit):
            if question == "Partial Error Test":
                return [{"chunk_id": "c1", "text": "t1", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}]
            elif question == "Q1_query":
                raise RuntimeError("API Rate limit")
            elif question == "Q2_query":
                return [{"chunk_id": "c1", "text": "t1", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}]
            return []

        # Q1 lỗi nhưng Q2 thành công -> status = "partial"
        res = retrieve_multi_query_hybrid(
            question="Partial Error Test",
            custom_query_generator=fake_generator,
            custom_bm25_retriever=fake_bm25,
            custom_semantic_retriever=lambda q, k: []
        )
        self.assertEqual(res["status"], "partial")
        self.assertIn("Q1", res["trace"]["failed_queries"])

        # Cả Q1 và Q2 đều lỗi -> status = "multi_query_partial"
        def fake_bm25_all_fail(question, limit):
            if question == "Partial Error Test":
                return [{"chunk_id": "c1", "text": "t1", "source": "s1.pdf", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}]
            raise RuntimeError("API Rate limit")

        res_all = retrieve_multi_query_hybrid(
            question="Partial Error Test",
            custom_query_generator=fake_generator,
            custom_bm25_retriever=fake_bm25_all_fail,
            custom_semantic_retriever=lambda q, k: []
        )
        self.assertEqual(res_all["status"], "multi_query_partial")


if __name__ == "__main__":
    unittest.main()
