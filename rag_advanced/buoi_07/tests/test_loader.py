import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import rag


class TestLoaderAndValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="loader_test_")).resolve()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_loader_reads_json_list(self):
        """1. Loader reads JSON list."""
        data = [
            {
                "chunk_id": "C1",
                "strategy": "hierarchical",
                "source": "doc.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung 1"
            }
        ]
        fpath = self.temp_dir / "sample_list.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        res = rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertEqual(len(res["chunks"]), 1)
        self.assertEqual(res["chunks"][0]["chunk_id"], "C1")

    def test_02_loader_reads_object_with_chunks_field(self):
        """2. Loader reads JSON object with field 'chunks'."""
        data = {
            "chunks": [
                {
                    "chunk_id": "C2",
                    "strategy": "hierarchical",
                    "source": "doc.pdf",
                    "page_start": 2,
                    "page_end": 2,
                    "text": "Nội dung 2"
                }
            ]
        }
        fpath = self.temp_dir / "sample_obj.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        res = rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertEqual(len(res["chunks"]), 1)
        self.assertEqual(res["chunks"][0]["chunk_id"], "C2")

    def test_03_loader_filters_strategy(self):
        """3. Only extracts requested strategy without mixing."""
        data = [
            {"chunk_id": "C1", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "H1"},
            {"chunk_id": "C2", "strategy": "semantic", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "S1"},
            {"chunk_id": "C3", "strategy": "fixed-size", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "F1"}
        ]
        fpath = self.temp_dir / "mixed.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        res_h = rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        res_s = rag.load_chunks(input_dir=self.temp_dir, strategy="semantic")
        res_f = rag.load_chunks(input_dir=self.temp_dir, strategy="fixed-size")

        self.assertEqual(len(res_h["chunks"]), 1)
        self.assertEqual(res_h["chunks"][0]["chunk_id"], "C1")
        self.assertEqual(len(res_s["chunks"]), 1)
        self.assertEqual(res_s["chunks"][0]["chunk_id"], "C2")
        self.assertEqual(len(res_f["chunks"]), 1)
        self.assertEqual(res_f["chunks"][0]["chunk_id"], "C3")

    def test_04_missing_required_field_fails(self):
        """4. Missing required field raises ValueError."""
        data = [
            {"chunk_id": "C1", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1} # missing text
        ]
        fpath = self.temp_dir / "invalid_missing.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertIn("Thiếu trường bắt buộc 'text'", str(ctx.exception))

    def test_05_field_wrong_type_fails(self):
        """5. Field wrong type raises TypeError."""
        data = [
            {"chunk_id": 123, "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "H1"}
        ]
        fpath = self.temp_dir / "wrong_type.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(TypeError) as ctx:
            rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertIn("phải là string", str(ctx.exception))

    def test_06_boolean_not_accepted_as_page_number(self):
        """6. Boolean is not accepted as page number."""
        data = [
            {"chunk_id": "C1", "strategy": "hierarchical", "source": "d.pdf", "page_start": True, "page_end": 2, "text": "H1"}
        ]
        fpath = self.temp_dir / "bool_page.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(TypeError) as ctx:
            rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertIn("phải là số nguyên (integer)", str(ctx.exception))

    def test_07_page_start_greater_than_page_end_fails(self):
        """7. page_start > page_end raises ValueError."""
        data = [
            {"chunk_id": "C1", "strategy": "hierarchical", "source": "d.pdf", "page_start": 5, "page_end": 2, "text": "H1"}
        ]
        fpath = self.temp_dir / "invalid_pages.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertIn("page_start (5) lớn hơn page_end (2)", str(ctx.exception))

    def test_08_empty_text_skipped_and_stat_incremented(self):
        """8. Empty text skipped and empty_text_skipped count incremented."""
        data = [
            {"chunk_id": "C1", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "  \n  "},
            {"chunk_id": "C2", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Hợp lệ"}
        ]
        fpath = self.temp_dir / "empty_text.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        res = rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertEqual(res["stats"]["empty_text_skipped"], 1)
        self.assertEqual(res["stats"]["valid_chunks"], 1)
        self.assertEqual(res["chunks"][0]["chunk_id"], "C2")

    def test_09_duplicate_chunk_id_fails(self):
        """9. Duplicate chunk_id raises ValueError with file and record position details."""
        data = [
            {"chunk_id": "DUP:001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "V1"},
            {"chunk_id": "DUP:001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 2, "page_end": 2, "text": "V2"}
        ]
        fpath = self.temp_dir / "dup.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertIn("Trùng lặp chunk_id 'DUP:001'", str(ctx.exception))

    def test_38_loader_blocks_non_dict_record(self):
        """38. Loader blocks record that is not a JSON object (dict)."""
        data = [
            "chuỗi không phải dict",
            {"chunk_id": "C1", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "H1"}
        ]
        fpath = self.temp_dir / "non_dict.json"
        fpath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(TypeError) as ctx:
            rag.load_chunks(input_dir=self.temp_dir, strategy="hierarchical")
        self.assertIn("Record không phải JSON object", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
