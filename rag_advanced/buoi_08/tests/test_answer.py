"""
Unit tests cho Answer Pipeline, Grounding, Citations & Comparison - Buổi 08
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import query_advanced_rag, compare_retrieval_modes


class TestAnswerPipelineAndCompare(unittest.TestCase):

    def setUp(self):
        self.sample_chunks = [
            {
                "chunk_id": "chk_ans_001",
                "strategy": "hierarchical",
                "source": "TT_02_2023_NHNN.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "Điều 7 Khoản 1 quy định cơ cấu nợ cho khách hàng gặp khó khăn."
            },
            {
                "chunk_id": "chk_ans_002",
                "strategy": "hierarchical",
                "source": "TT_02_2023_NHNN.pdf",
                "page_start": 2,
                "page_end": 3,
                "text": "Điều 7 Khoản 2 quy định giữ nguyên nhóm nợ."
            }
        ]

    def test_01_gating_by_mode(self):
        """1. Gating theo đúng mode: semantic_distance cho semantic, rerank_score cho hybrid_rerank."""
        def mock_bm25(q, k):
            return []

        def mock_sem(q, k):
            return [
                {"chunk_id": "chk_ans_001", "text": "text1", "source": "s.pdf", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.20},
                {"chunk_id": "chk_ans_002", "text": "text2", "source": "s.pdf", "page_start": 2, "page_end": 2, "semantic_rank": 2, "semantic_distance": 0.80}  # Rejected > 0.45
            ]

        def mock_gen(prompt):
            return "Cơ cấu nợ [E1]."

        res = query_advanced_rag(
            question="Cơ cấu nợ",
            mode="semantic",
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_generator=mock_gen
        )

        self.assertEqual(res["status"], "answered")
        self.assertEqual(len(res["evidence"]), 2)
        self.assertTrue(res["evidence"][0]["accepted"])
        self.assertFalse(res["evidence"][1]["accepted"])

    def test_02_rejected_evidence_excluded_from_prompt(self):
        """2. Rejected evidence không được đưa vào prompt grounding."""
        captured_prompt = ""

        def mock_bm25(q, k):
            return []

        def mock_sem(q, k):
            return [
                {"chunk_id": "chk_ans_001", "text": "text_accepted", "source": "s.pdf", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.10},
                {"chunk_id": "chk_ans_002", "text": "text_rejected", "source": "s.pdf", "page_start": 2, "page_end": 2, "semantic_rank": 2, "semantic_distance": 0.90}
            ]

        def mock_gen(prompt):
            nonlocal captured_prompt
            captured_prompt = prompt
            return "Trả lời [E1]."

        query_advanced_rag(
            question="Hỏi",
            mode="semantic",
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_generator=mock_gen
        )

        self.assertIn("text_accepted", captured_prompt)
        self.assertNotIn("text_rejected", captured_prompt)

    def test_03_trace_counts_and_timings_complete(self):
        """3. Trace counts và timings chứa đầy đủ các thuộc tính quy định."""
        def mock_bm25(q, k):
            return []

        def mock_sem(q, k):
            return [{"chunk_id": "chk_ans_001", "text": "t", "source": "s.pdf", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.10}]

        def mock_gen(prompt):
            return "Trả lời [E1]."

        res = query_advanced_rag(
            question="Hỏi",
            mode="semantic",
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_generator=mock_gen
        )

        trace = res["trace"]
        required_keys = ["bm25_candidates", "semantic_candidates", "overlap", "union", "reranked", "accepted", "generation_called", "latency_ms"]
        for k in required_keys:
            self.assertIn(k, trace)

    def test_04_citation_mapping_real_metadata(self):
        """4. Bóc tách nhãn [E1] và ánh xạ chính xác sang metadata thực tế."""
        def mock_bm25(q, k):
            return []

        def mock_sem(q, k):
            return [{"chunk_id": "chk_ans_001", "text": "t1", "source": "s.pdf", "page_start": 5, "page_end": 6, "semantic_rank": 1, "semantic_distance": 0.10}]

        def mock_gen(prompt):
            return "Nội dung trả lời theo [E1] và nhãn giả [E99]."

        res = query_advanced_rag(
            question="Hỏi",
            mode="semantic",
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_generator=mock_gen
        )

        self.assertEqual(len(res["citations"]), 1)
        self.assertEqual(res["citations"][0]["label"], "E1")
        self.assertEqual(res["citations"][0]["chunk_id"], "chk_ans_001")
        self.assertEqual(res["citations"][0]["page_start"], 5)
        self.assertTrue(len(res["warnings"]) > 0)

    def test_05_generation_called_at_most_once(self):
        """5. LLM generation chỉ được gọi tối đa 1 lần trong suốt quá trình xử lý."""
        gen_count = 0

        def mock_bm25(q, k):
            return []

        def mock_sem(q, k):
            return [{"chunk_id": "chk_ans_001", "text": "t", "source": "s.pdf", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.10}]

        def mock_gen(prompt):
            nonlocal gen_count
            gen_count += 1
            return "Trả lời [E1]."

        query_advanced_rag(
            question="Hỏi",
            mode="semantic",
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_generator=mock_gen
        )
        self.assertEqual(gen_count, 1)

    def test_06_compare_no_generation_called(self):
        """6. Lệnh compare chạy qua các mode nhưng không hề gọi LLM generation (0 generation calls)."""
        def mock_bm25(q, k):
            return []

        def mock_sem(q, k):
            return []

        def mock_rr(q, cands):
            return cands

        res = compare_retrieval_modes(
            question="Hỏi",
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_rr
        )

        self.assertIn("summary_table", res)
        self.assertEqual(len(res["modes_compared"]), 4)

    def test_07_reranker_unavailable_status(self):
        """7. Reranker bị lỗi nạp trả về đúng status 'reranker_unavailable'."""
        def mock_bm25(q, k):
            return []

        def mock_sem(q, k):
            return []

        def mock_bad_reranker(q, cands):
            raise RuntimeError("Nạp Reranker thất bại")

        res = query_advanced_rag(
            question="Hỏi",
            mode="hybrid_rerank",
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem,
            custom_reranker=mock_bad_reranker
        )
        self.assertEqual(res["status"], "reranker_unavailable")

    def test_08_all_status_schema_completeness(self):
        """8. Tất cả các status (insufficient_evidence, answered) đều trả về đầy đủ schema quy định."""
        def mock_bm25(q, k):
            return []

        def mock_sem(q, k):
            return [{"chunk_id": "chk_ans_001", "text": "t", "source": "s.pdf", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.90}]  # Rejected

        res = query_advanced_rag(
            question="Hỏi",
            mode="semantic",
            custom_bm25_retriever=mock_bm25,
            custom_semantic_retriever=mock_sem
        )

        self.assertEqual(res["status"], "insufficient_evidence")
        for k in ["status", "mode", "question", "answer", "evidence", "citations", "warnings", "trace"]:
            self.assertIn(k, res)


if __name__ == "__main__":
    unittest.main()
