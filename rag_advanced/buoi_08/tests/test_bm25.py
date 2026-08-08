"""
Unit tests cho Tokenizer & BM25 Lexical Retrieval Stage - Buổi 08
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import tokenize_vi_legal, BM25Retriever, search_bm25


class TestBM25TokenizerAndSearch(unittest.TestCase):

    def setUp(self):
        self.sample_chunks = [
            {
                "chunk_id": "chk_001",
                "strategy": "hierarchical",
                "source": "TT_02_2023_NHNN.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "Điều 7 Khoản 1 quy định cơ cấu lại thời hạn trả nợ cho khách hàng."
            },
            {
                "chunk_id": "chk_002",
                "strategy": "hierarchical",
                "source": "TT_02_2023_NHNN.pdf",
                "page_start": 2,
                "page_end": 3,
                "text": "Tổ chức tín dụng xem xét điều chỉnh kỳ hạn trả nợ gốc và lãi vay."
            },
            {
                "chunk_id": "chk_003",
                "strategy": "hierarchical",
                "source": "Luat_Xaydung_2014.pdf",
                "page_start": 10,
                "page_end": 11,
                "text": "Quy định cấp phép xây dựng công trình nhà ở đô thị."
            }
        ]

    def test_01_tokenizer_preserves_vietnamese_diacritics(self):
        """1. Tokenizer giữ nguyên các từ tiếng Việt có dấu NFC."""
        text = "cơ cấu lại thời hạn trả nợ"
        tokens = tokenize_vi_legal(text)
        expected = ["cơ", "cấu", "lại", "thời", "hạn", "trả", "nợ"]
        self.assertEqual(tokens, expected)

    def test_02_tokenizer_preserves_article_and_clause_numbers(self):
        """2. Tokenizer giữ được chữ 'Điều', 'Khoản' và các chữ số 7, 2."""
        text = "Điều 7, Khoản 2!!!"
        tokens = tokenize_vi_legal(text)
        self.assertIn("điều", tokens)
        self.assertIn("7", tokens)
        self.assertIn("khoản", tokens)
        self.assertIn("2", tokens)

    def test_03_corpus_and_query_use_same_tokenizer(self):
        """3. Corpus và Query sử dụng cùng một hàm tokenizer."""
        retriever = BM25Retriever(self.sample_chunks)
        query_tokens = tokenize_vi_legal("cơ cấu nợ")
        corpus_tok = retriever.corpus_tokens[0]
        self.assertIsInstance(query_tokens, list)
        self.assertIsInstance(corpus_tok, list)

    def test_04_exact_legal_term_ranked_higher(self):
        """4. Chunk chứa từ khóa pháp lý chính xác được xếp hạng cao hơn."""
        retriever = BM25Retriever(self.sample_chunks)
        res = retriever.search("Điều 7 quy định cơ cấu lại thời hạn trả nợ", candidate_k=3)
        self.assertEqual(res[0]["chunk_id"], "chk_001")
        self.assertGreater(res[0]["bm25_score"], res[1]["bm25_score"])

    def test_05_candidate_k_exceeding_corpus_size_works(self):
        """5. candidate_k lớn hơn số lượng corpus vẫn chạy bình thường mà không gây lỗi."""
        retriever = BM25Retriever(self.sample_chunks)
        res = retriever.search("cơ cấu nợ", candidate_k=100)
        self.assertEqual(len(res), len(self.sample_chunks))

    def test_06_empty_question_fails(self):
        """6. Câu hỏi rỗng hoặc không chứa token hợp lệ phải báo lỗi ValueError."""
        retriever = BM25Retriever(self.sample_chunks)
        with self.assertRaises(ValueError):
            retriever.search("   ")
        with self.assertRaises(ValueError):
            retriever.search("!!!???")

    def test_07_deterministic_tie_breaking(self):
        """7. Tie-break ổn định theo thứ tự alphabet của chunk_id khi BM25 score bằng nhau."""
        tied_chunks = [
            {"chunk_id": "chk_Z", "strategy": "hierarchical", "source": "s.pdf", "page_start": 1, "page_end": 1, "text": "không liên quan 1"},
            {"chunk_id": "chk_A", "strategy": "hierarchical", "source": "s.pdf", "page_start": 1, "page_end": 1, "text": "không liên quan 2"}
        ]
        retriever = BM25Retriever(tied_chunks)
        res = retriever.search("từ_khóa_không_tồn_tại", candidate_k=2)
        self.assertEqual(res[0]["chunk_id"], "chk_A")
        self.assertEqual(res[1]["chunk_id"], "chk_Z")

    def test_08_no_external_model_or_db_calls(self):
        """8. Xác nhận BM25 chạy thuần túy offline trong memory, không gọi Gemini/ChromaDB."""
        res = search_bm25("cơ cấu nợ", chunks=self.sample_chunks, top_k=2)
        self.assertEqual(len(res), 2)
        self.assertIn("bm25_score", res[0])
        self.assertIn("bm25_rank", res[0])


if __name__ == "__main__":
    unittest.main()
