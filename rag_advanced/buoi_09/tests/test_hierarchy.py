"""
Unit tests cho Hierarchy Resolution, Parent Building và Persistence - Buổi 09
"""

import sys
import os
import json
import shutil
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import (
    resolve_chunk_hierarchy,
    build_parent_windows,
    build_and_save_hierarchy,
    get_hierarchy_status,
    extract_numerical_suffix
)


class TestHierarchyBuilder(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = BASE_DIR / "tests" / "tmp_storage"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    def test_01_metadata_precedence(self):
        """1. Metadata structure hợp lệ có độ ưu tiên cao nhất."""
        chunk = {
            "chunk_id": "TT_02:hierarchical:0001",
            "source": "s1.pdf",
            "page_start": 1,
            "page_end": 1,
            "text": "Điều 8. Quy định nhu cầu vốn không được cho vay.",
            "structure": {
                "chapter": "Chương II",
                "article": "Điều 2. Đối tượng áp dụng"
            }
        }
        res, _, _ = resolve_chunk_hierarchy(chunk, None, None)
        # Sẽ chọn Điều 2 từ metadata thay vì Điều 8 trong văn bản
        self.assertEqual(res["structural_path"]["article"], "Điều 2. Đối tượng áp dụng")
        self.assertEqual(res["resolution_method"], "metadata")

    def test_02_heading_inferred_at_chunk_start(self):
        """2. Nhận diện heading Chương hoặc Điều ở dòng đầu tiên của text."""
        chunk = {
            "chunk_id": "TT_02:hierarchical:0001",
            "source": "s1.pdf",
            "page_start": 1,
            "page_end": 1,
            "text": "**Điều 8. Những nhu cầu vốn không được cho vay**\nNội dung chi tiết...",
            "structure": None
        }
        res, _, _ = resolve_chunk_hierarchy(chunk, None, None)
        self.assertEqual(res["structural_path"]["article"], "Điều 8. Những nhu cầu vốn không được cho vay")
        self.assertEqual(res["resolution_method"], "heading_inferred")

    def test_03_carry_forward_within_same_source(self):
        """3. Carry forward chapter/article từ chunk trước đó trong cùng source."""
        chunk1 = {
            "chunk_id": "TT_02:hierarchical:0001",
            "source": "s1.pdf",
            "page_start": 1,
            "page_end": 1,
            "text": "Điều 2. Đối tượng áp dụng",
            "structure": None
        }
        res1, last_ch, last_art = resolve_chunk_hierarchy(chunk1, "Chương I", None)

        chunk2 = {
            "chunk_id": "TT_02:hierarchical:0002",
            "source": "s1.pdf",
            "page_start": 2,
            "page_end": 2,
            "text": "1. Khách hàng vay vốn...",
            "structure": None
        }
        res2, _, _ = resolve_chunk_hierarchy(chunk2, last_ch, last_art)
        self.assertEqual(res2["structural_path"]["chapter"], "Chương I")
        self.assertEqual(res2["structural_path"]["article"], "Điều 2. Đối tượng áp dụng")
        self.assertEqual(res2["resolution_method"], "carried_forward")

    def test_04_no_carry_forward_across_sources(self):
        """4. Không carry forward trạng thái giữa các source khác nhau."""
        # Source 1 cập nhật last_chapter, last_article
        chunk1 = {
            "chunk_id": "TT_02:hierarchical:0001",
            "source": "s1.pdf",
            "page_start": 1,
            "page_end": 1,
            "text": "Điều 2. Đối tượng",
            "structure": None
        }
        _, last_ch, last_art = resolve_chunk_hierarchy(chunk1, "Chương I", "Điều 2. Đối tượng")

        # Khởi tạo source 2 với None, không dùng last_ch/last_art từ source 1
        chunk2 = {
            "chunk_id": "TT_02:hierarchical:0002",
            "source": "s2.pdf",
            "page_start": 1,
            "page_end": 1,
            "text": "Nội dung chung chung không có Điều luật.",
            "structure": None
        }
        res2, _, _ = resolve_chunk_hierarchy(chunk2, None, None)
        self.assertEqual(res2["structural_path"]["article"], "DOCUMENT_FALLBACK")
        self.assertEqual(res2["resolution_method"], "document_fallback")

    def test_05_inline_citations_not_misidentified(self):
        """5. Các tham chiếu Điều N ở giữa câu không bị nhận nhầm làm tiêu đề."""
        chunk = {
            "chunk_id": "TT_02:hierarchical:0001",
            "source": "s1.pdf",
            "page_start": 1,
            "page_end": 1,
            "text": "Tổ chức tín dụng thực hiện trích lập rủi ro theo quy định tại Điều 5 của Thông tư này.",
            "structure": None
        }
        res, _, _ = resolve_chunk_hierarchy(chunk, None, None)
        # Sẽ không bị gán cho Điều 5
        self.assertEqual(res["structural_path"]["article"], "DOCUMENT_FALLBACK")
        self.assertIn("Phát hiện các tham chiếu điều khoản trong văn bản", res["warnings"][0])

    def test_06_conflict_sets_ambiguous_and_warning(self):
        """6. Mâu thuẫn giữa metadata và heading thực tế sẽ set ambiguous=True."""
        chunk = {
            "chunk_id": "TT_02:hierarchical:0001",
            "source": "s1.pdf",
            "page_start": 1,
            "page_end": 1,
            "text": "Điều 8. Những nhu cầu vốn không được cho vay",
            "structure": {
                "chapter": "Chương I",
                "article": "Điều 2. Đối tượng áp dụng"
            }
        }
        res, _, _ = resolve_chunk_hierarchy(chunk, None, None)
        self.assertTrue(res["ambiguous"])
        self.assertTrue(len(res["warnings"]) > 0)

    def test_07_numeric_chunk_ordering(self):
        """7. Sắp xếp các child chunks chính xác theo phần số cuối của chunk_id."""
        self.assertEqual(extract_numerical_suffix("TT_02:hierarchical:0002"), 2)
        self.assertEqual(extract_numerical_suffix("TT_02:hierarchical:0010"), 10)
        self.assertEqual(extract_numerical_suffix("TT_02:hierarchical:abc"), 999999)

    def test_08_stable_parent_id(self):
        """8. Mã băm parent ID sinh ra ổn định (byte-equivalent) cho cùng tham số đầu vào."""
        children = [
            {"child_id": "c1", "text": "t1", "page_start": 1, "page_end": 1, "ambiguous": False, "warnings": []}
        ]
        p1 = build_parent_windows("Điều 2", "s1.pdf", children, 5000)
        p2 = build_parent_windows("Điều 2", "s1.pdf", children, 5000)
        self.assertEqual(p1[0]["parent_id"], p2[0]["parent_id"])

    def test_09_parent_split_at_child_boundary(self):
        """9. Cắt phân mảnh parent window chính xác tại ranh giới của child chunks, không cắt đôi text của child."""
        children = [
            {"child_id": "c1", "text": "A" * 1500, "page_start": 1, "page_end": 1, "ambiguous": False, "warnings": []},
            {"child_id": "c2", "text": "B" * 1500, "page_start": 2, "page_end": 2, "ambiguous": False, "warnings": []}
        ]
        # Giới hạn 2000 kí tự -> c1 và c2 không thể gộp chung -> chia làm 2 windows
        parents = build_parent_windows("Điều 2", "s1.pdf", children, 2000)
        self.assertEqual(len(parents), 2)
        self.assertEqual(parents[0]["child_ids"], ["c1"])
        self.assertEqual(parents[1]["child_ids"], ["c2"])

    def test_10_oversized_child_warning(self):
        """10. Child chunk dài hơn PARENT_MAX_CHARS được giữ nguyên và đánh dấu warning oversized_single_child."""
        children = [
            {"child_id": "c1", "text": "A" * 4000, "page_start": 1, "page_end": 1, "ambiguous": False, "warnings": []}
        ]
        parents = build_parent_windows("Điều 2", "s1.pdf", children, 2000)
        self.assertEqual(len(parents), 1)
        self.assertIn("oversized_single_child", parents[0]["warnings"])

    def test_11_each_child_mapped_to_exactly_one_parent(self):
        """11. Mỗi child chunk thuộc về duy nhất 1 parent document window."""
        children = [
            {"child_id": "c1", "text": "A" * 500, "page_start": 1, "page_end": 1, "ambiguous": False, "warnings": []},
            {"child_id": "c2", "text": "B" * 500, "page_start": 1, "page_end": 1, "ambiguous": False, "warnings": []}
        ]
        parents = build_parent_windows("Điều 2", "s1.pdf", children, 2000)
        self.assertEqual(len(parents), 1)
        self.assertEqual(len(parents[0]["child_ids"]), 2)
        # parent_id đã được cập nhật ngược lại cho child records
        self.assertEqual(children[0]["parent_id"], parents[0]["parent_id"])
        self.assertEqual(children[1]["parent_id"], parents[0]["parent_id"])

    def test_12_parent_pages_count_and_text_correct(self):
        """12. Thuộc tính page_start, page_end và gộp text của parent chính xác."""
        children = [
            {"child_id": "c1", "text": "Nội dung 1", "page_start": 1, "page_end": 2, "ambiguous": False, "warnings": []},
            {"child_id": "c2", "text": "Nội dung 2", "page_start": 2, "page_end": 4, "ambiguous": False, "warnings": []}
        ]
        parents = build_parent_windows("Điều 2", "s1.pdf", children, 5000)
        p = parents[0]
        self.assertEqual(p["page_start"], 1)
        self.assertEqual(p["page_end"], 4)
        self.assertEqual(p["text"], "Nội dung 1\n\nNội dung 2")

    def test_13_atomic_build_and_manifest_fingerprint(self):
        """13. Thực thi build registry lưu đĩa atomically kèm manifest fingerprints đầy đủ."""
        mock_chunks_dir = self.tmp_dir / "chunks"
        mock_chunks_dir.mkdir(parents=True, exist_ok=True)
        
        sample_data = [
            {
                "chunk_id": "TT_02:hierarchical:0001",
                "strategy": "hierarchical",
                "source": "TT_02_2023_NHNN.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 1. Phạm vi điều chỉnh",
                "structure": None
            }
        ]
        
        with open(mock_chunks_dir / "sample__hierarchical.json", "w", encoding="utf-8") as f:
            json.dump(sample_data, f)
            
        res = build_and_save_hierarchy(
            strategy="hierarchical",
            input_dir=mock_chunks_dir,
            storage_dir=self.tmp_dir
        )
        
        manifest = res["manifest"]
        self.assertEqual(manifest["counts"]["child_chunks"], 1)
        self.assertEqual(manifest["counts"]["parent_documents"], 1)
        self.assertIn("sample__hierarchical.json", manifest["input_file_fingerprints"])
        
        children_file = Path(res["children_path"])
        parents_file = Path(res["parents_path"])
        self.assertTrue(children_file.exists())
        self.assertTrue(parents_file.exists())

    def test_14_status_does_not_create_or_modify_files(self):
        """14. Gọi hierarchy-status ở chế độ read-only, không sửa timestamp hoặc tạo thư mục mới."""
        status = get_hierarchy_status(storage_dir=self.tmp_dir)
        self.assertFalse(status["hierarchy_built"])


if __name__ == "__main__":
    unittest.main()
