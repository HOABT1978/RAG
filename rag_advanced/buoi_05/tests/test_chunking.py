# -*- coding: utf-8 -*-
"""test_chunking.py — Kiểm thử đơn giản (thư viện chuẩn unittest).

Chạy:
    python -m unittest discover -s tests -v
hoặc:
    .venv\\Scripts\\python.exe -m unittest tests.test_chunking -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from src.chunking import (  # noqa: E402
    chunk_fixed_size,
    chunk_hierarchical,
    chunk_semantic,
)
from src.ocr import PageText, looks_corrupted, normalize_nfc  # noqa: E402

VAN_BAN = """Chương I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh

Thông tư này quy định về việc thực hiện chính sách tín dụng đối với lĩnh vực
nông nghiệp, nông thôn nhằm đáp ứng nhu cầu vốn phục vụ sản xuất kinh doanh.

Điều 2. Đối tượng áp dụng

Các tổ chức tín dụng, chi nhánh ngân hàng nước ngoài và các khách hàng vay vốn
theo quy định của pháp luật hiện hành.

Mục 1
Hạn mức cho vay

1. Hạn mức cho vay đối với khách hàng được xác định theo nhu cầu vốn.
2. Trường hợp khách hàng có nhu cầu vay vượt hạn mức thì tổ chức tín dụng xem xét.
"""


def _pages(text: str, n: int = 2) -> list[PageText]:
    half = len(text) // n
    return [
        PageText(page=i + 1, text=part, method="pymupdf")
        for i, part in enumerate([text[:half], text[half:]] if n > 1 else [text])
    ]


class TestHeuristic(unittest.TestCase):
    def test_empty(self):
        bad, reason = looks_corrupted("")
        self.assertTrue(bad)
        self.assertIn("rỗng", reason)

    def test_good_vietnamese(self):
        bad, _ = looks_corrupted("Thông tư này quy định về việc thực hiện chính sách tín dụng nông nghiệp nông thôn.")
        self.assertFalse(bad)

    def test_broken_encoding(self):
        bad, reason = looks_corrupted("CQNG HOAXA HQI CHU NGHiAVIET NAM DQc lQp -Tr; do - Hqnh phric 1234567890 abcd efgh ijkl mnop qrst uvwx")
        self.assertTrue(bad)
        self.assertIn("encoding", reason)

    def test_nfc(self):
        decomposed = __import__("unicodedata").normalize("NFD", "Việt Nam — thông tư")
        self.assertEqual(normalize_nfc(decomposed), "Việt Nam — thông tư")


class TestChunking(unittest.TestCase):
    def test_fixed_size_overlap(self):
        chunks = chunk_fixed_size(_pages(VAN_BAN), "demo.pdf", size=200, overlap=20)
        self.assertGreaterEqual(len(chunks), 2)
        for c in chunks:
            self.assertEqual(c.strategy, "fixed_size")
            self.assertTrue(c.page_start >= 1 and c.page_end <= 2)

    def test_fixed_size_overlap_connects(self):
        chunks = chunk_fixed_size(_pages("A" * 400), "d.pdf", size=200, overlap=40)
        self.assertEqual(chunks[0].text[-1], "A")
        self.assertTrue(chunks[1].text.startswith("A"))

    def test_semantic_no_mid_sentence_when_possible(self):
        text = "Câu thứ nhất kết thúc.\n\nCâu thứ hai bắt đầu.\n\n" * 30
        chunks = chunk_semantic(_pages(text), "d.pdf", target_size=150, max_size=300)
        for c in chunks:
            stripped = c.text.strip()
            if stripped:
                self.assertTrue(stripped.endswith("."))

    def test_hierarchical_finds_structures(self):
        chunks, warnings = chunk_hierarchical(_pages(VAN_BAN), "vb.pdf")
        types = [c.structure.get("type") for c in chunks if c.structure]
        self.assertIn("Chương", types)
        self.assertIn("Điều", types)
        self.assertIn("Mục", types)

    def test_hierarchical_warns_when_no_structure(self):
        chunks, warnings = chunk_hierarchical(_pages("Đây là văn bản không có cấu trúc tiêu đề gì cả." * 10), "x.pdf")
        self.assertTrue(any("KHÔNG phát hiện" in w for w in warnings))
        self.assertGreaterEqual(len(chunks), 1)


if __name__ == "__main__":
    unittest.main()
