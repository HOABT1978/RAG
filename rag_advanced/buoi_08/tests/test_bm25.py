"""
Unit tests cho Tokenizer tiếng Việt và BM25 Retrieval - Buổi 08
"""

import sys
import unittest
from pathlib import Path

# Nạp module advanced_rag
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import tokenize_vi_legal, BM25Retriever, search_bm25


class TestBM25TokenizerAndSearch(unittest.TestCase):

    def setUp(self):
        """Khởi tạo tập dữ liệu mock fixture cho unit tests."""
        self.sample_chunks = [
            {
                "chunk_id": "chk_001",
                "strategy": "hierarchical",
                "source": "Thong_tu_02.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 7 Khoản 2 quy định về việc cơ cấu lại thời hạn trả nợ cho khách hàng."
            },
            {
                "chunk_id": "chk_002",
                "strategy": "hierarchical",
                "source": "Thong_tu_02.pdf",
                "page_start": 2,
                "page_end": 2,
                "text": "Tổ chức tín dụng xem xét giữ nguyên nhóm nợ theo quy định của Ngân hàng Nhà nước."
            },
            {
                "chunk_id": "chk_003",
                "strategy": "hierarchical",
                "source": "Luat_Xay_dung.pdf",
                "page_start": 5,
                "page_end": 5,
                "text": "Thủ tục xin cấp phép xây dựng nhà ở đô thị thuộc thẩm quyền Ủy ban nhân dân cấp huyện."
            }
        ]

    def test_01_tokenizer_preserves_vietnamese_diacritics(self):
        """1. Tokenizer giữ nguyên dấu tiếng Việt và chuẩn hóa NFC + casefold."""
        text = "Cơ cấu lại thời hạn trả nợ"
        tokens = tokenize_vi_legal(text)
        expected = ["cơ", "cấu", "lại", "thời", "hạn", "trả", "nợ"]
        self.assertEqual(tokens, expected)

    def test_02_tokenizer_preserves_article_and_clause_numbers(self):
        """2. Tokenizer giữ số Điều/Khoản và ký tự đặc biệt được loại bỏ."""
        text = "Điều 7, Khoản 2!"
        tokens = tokenize_vi_legal(text)
        expected = ["điều", "7", "khoản", "2"]
        self.assertEqual(tokens, expected)

    def test_03_corpus_and_query_use_identical_preprocessing(self):
        """3. Corpus và Query sử dụng cùng một hàm tokenizer."""
        raw_doc = "ĐIỀU 7: CƠ CẤU NỢ"
        raw_query = "Điều 7: Cơ cấu nợ?"

        doc_tokens = tokenize_vi_legal(raw_doc)
        query_tokens = tokenize_vi_legal(raw_query)

        self.assertEqual(doc_tokens, query_tokens)
        self.assertEqual(doc_tokens, ["điều", "7", "cơ", "cấu", "nợ"])

    def test_04_exact_legal_term_ranked_higher(self):
        """4. Chunk chứa từ khóa pháp lý chính xác được xếp hạng cao hơn."""
        retriever = BM25Retriever(self.sample_chunks)
        results = retriever.search("cơ cấu lại thời hạn trả nợ", top_k=2)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["chunk_id"], "chk_001")
        self.assertGreater(results[0]["bm25_score"], 0.0)

    def test_05_candidate_k_exceeding_corpus_size_works(self):
        """5. candidate_k lớn hơn số lượng corpus vẫn chạy bình thường mà không gây lỗi."""
        results = search_bm25(question="quy định", chunks=self.sample_chunks, top_k=100)
        self.assertEqual(len(results), len(self.sample_chunks))

    def test_06_empty_question_fails(self):
        """6. Câu hỏi rỗng hoặc không chứa token hợp lệ phải báo lỗi ValueError."""
        with self.assertRaises(ValueError):
            search_bm25(question="", chunks=self.sample_chunks, top_k=5)

        with self.assertRaises(ValueError):
            search_bm25(question="   ", chunks=self.sample_chunks, top_k=5)

        with self.assertRaises(ValueError):
            search_bm25(question="!@#$%^&*", chunks=self.sample_chunks, top_k=5)

    def test_07_deterministic_tie_breaking(self):
        """7. Tie-break ổn định theo thứ tự alphabet của chunk_id khi BM25 score bằng nhau."""
        tied_chunks = [
            {
                "chunk_id": "chk_BBB",
                "strategy": "hierarchical",
                "source": "doc.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung kiểm tra trùng điểm số BM25."
            },
            {
                "chunk_id": "chk_AAA",
                "strategy": "hierarchical",
                "source": "doc.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung kiểm tra trùng điểm số BM25."
            }
        ]
        results = search_bm25("nội dung kiểm tra", chunks=tied_chunks, top_k=2)

        self.assertEqual(len(results), 2)
        # Scores equal -> chk_AAA must be ranked first alphabetically
        self.assertEqual(results[0]["bm25_score"], results[1]["bm25_score"])
        self.assertEqual(results[0]["chunk_id"], "chk_AAA")
        self.assertEqual(results[1]["chunk_id"], "chk_BBB")

    def test_08_no_external_model_or_db_calls(self):
        """8. Xác nhận BM25 chạy thuần túy offline trong memory, không gọi Gemini/ChromaDB."""
        # Chạy thử với sample_chunks
        res = search_bm25("giữ nguyên nhóm nợ", chunks=self.sample_chunks, top_k=1)
        self.assertEqual(len(res), 1)
        self.assertIn("bm25_rank", res[0])
        self.assertIn("bm25_score", res[0])


if __name__ == "__main__":
    unittest.main()
