"""
Unit tests cho Multi-Query Generator (Query Expansion) - Buổi 09
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import generate_query_variants


class TestQueryGenerator(unittest.TestCase):

    def test_01_q0_always_first_and_preserved(self):
        """1. Q0 luôn đứng đầu và giữ nguyên nội dung gốc sau chuẩn hóa."""
        def fake_generator(q):
            return {"queries": [{"text": "Biến thể 1", "focus": "paraphrase"}]}

        res = generate_query_variants(
            question="  Quy định cho vay vốn?  ",
            query_generator_fn=fake_generator
        )
        self.assertEqual(res["queries"][0]["query_id"], "Q0")
        self.assertEqual(res["queries"][0]["text"], "Quy định cho vay vốn?")
        self.assertEqual(res["queries"][0]["origin"], "original")

    def test_02_strict_schema_validation(self):
        """2. Strict schema validation cho kết quả trả về."""
        def fake_generator(q):
            return {"queries": [{"text": "Biến thể 1", "focus": "paraphrase"}]}

        res = generate_query_variants(
            question="Quy định cho vay vốn?",
            query_generator_fn=fake_generator
        )
        self.assertIn("original_question", res)
        self.assertIn("queries", res)
        self.assertIn("model", res)
        self.assertIn("generation_latency_ms", res)
        self.assertEqual(res["status"], "ready")

    def test_03_nfc_trim_and_max_length(self):
        """3. NFC/trim và lọc giới hạn độ dài ký tự tối đa."""
        def fake_generator(q):
            return {"queries": [
                {"text": "A" * 500, "focus": "paraphrase"}, # Sẽ bị loại nếu vượt quá MULTI_QUERY_MAX_CHARS (mặc định 300)
                {"text": "Hợp lệ", "focus": "exact_legal_terms"}
            ]}

        res = generate_query_variants(
            question="Hỏi ngắn?",
            query_generator_fn=fake_generator
        )
        # Q0 + "Hợp lệ" = 2 queries
        self.assertEqual(len(res["queries"]), 2)
        self.assertEqual(res["queries"][1]["text"], "Hợp lệ")

    def test_04_duplicate_removal(self):
        """4. Tự động lọc trùng lặp dựa trên Unicode NFC + casefold + whitespace."""
        def fake_generator(q):
            return {"queries": [
                {"text": "Biến thể 1", "focus": "paraphrase"},
                {"text": "biến thể 1.", "focus": "paraphrase"}, # trùng lặp sau normalise
                {"text": "BIẾN THỂ 1", "focus": "exact_legal_terms"} # trùng lặp sau normalise
            ]}

        res = generate_query_variants(
            question="Quy định cho vay?",
            query_generator_fn=fake_generator
        )
        self.assertEqual(len(res["queries"]), 2) # Q0 + "Biến thể 1"
        self.assertEqual(res["dropped_duplicate_count"], 2)

    def test_05_legal_reference_preservation(self):
        """5. Bảo toàn số Điều / Khoản nếu có trong câu hỏi gốc."""
        def fake_generator(q):
            return {"queries": [
                {"text": "Điều kiện theo Điều 7 quy định như thế nào?", "focus": "exact_legal_terms"},
                {"text": "Điều kiện theo Điều 8 quy định như thế nào?", "focus": "exact_legal_terms"} # Điều 8 bịa ra thêm (sẽ bị loại bỏ)
            ]}

        res = generate_query_variants(
            question="Điều kiện vay vốn theo Điều 7?",
            query_generator_fn=fake_generator
        )
        self.assertEqual(len(res["queries"]), 2) # Q0 + Điều 7 variant. Điều 8 bị loại bỏ.
        self.assertEqual(res["queries"][1]["text"], "Điều kiện theo Điều 7 quy định như thế nào?")

    def test_06_deterministic_ids(self):
        """6. Gán query ID tăng dần Q0, Q1, Q2... deterministic."""
        def fake_generator(q):
            return {"queries": [
                {"text": "Biến thể 1", "focus": "paraphrase"},
                {"text": "Biến thể 2", "focus": "paraphrase"}
            ]}

        res = generate_query_variants(
            question="Quy định chung?",
            query_generator_fn=fake_generator
        )
        q_ids = [q["query_id"] for q in res["queries"]]
        self.assertEqual(q_ids, ["Q0", "Q1", "Q2"])

    def test_07_cache_behavior(self):
        """7. Đảm bảo cache hit không gọi lại generator thực tế và ghi cache_hit=True."""
        call_count = 0
        def fake_generator(q):
            nonlocal call_count
            call_count += 1
            return {"queries": [{"text": f"Biến thể {call_count}", "focus": "paraphrase"}]}

        res1 = generate_query_variants(
            question="Câu hỏi cache test?",
            query_generator_fn=fake_generator
        )
        self.assertFalse(res1["cache_hit"])
        self.assertEqual(call_count, 1)

        res2 = generate_query_variants(
            question="Câu hỏi cache test?",
            query_generator_fn=fake_generator
        )
        self.assertTrue(res2["cache_hit"])
        self.assertEqual(call_count, 1) # Không tăng call_count

    def test_08_api_error_returns_explicit_status(self):
        """8. Trả về status query_generation_unavailable khi sinh lỗi."""
        def fake_generator(q):
            raise RuntimeError("API quota exceeded")

        res = generate_query_variants(
            question="Hỏi lỗi API?",
            query_generator_fn=fake_generator
        )
        self.assertEqual(res["status"], "query_generation_unavailable")
        self.assertEqual(len(res["queries"]), 1) # Chỉ chứa Q0 fallback
        self.assertEqual(res["queries"][0]["query_id"], "Q0")


if __name__ == "__main__":
    unittest.main()
