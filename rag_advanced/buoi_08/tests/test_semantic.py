"""
Unit tests cho Semantic Candidate Retrieval Stage & Advanced Status - Buổi 08
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import get_advanced_status, search_semantic
from rag import get_chroma_client, get_collection_name, index_chunks, load_config


class TestSemanticCandidateRetrieval(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.chroma_path = Path(self.temp_dir.name)

        self.strategy = "hierarchical"
        self.config = load_config()

        self.sample_chunks = [
            {
                "chunk_id": "chk_sem_001",
                "strategy": "hierarchical",
                "source": "TT_02_2023_NHNN.pdf",
                "page_start": 1,
                "page_end": 2,
                "text": "Điều 7 Khoản 1 quy định cơ cấu nợ."
            },
            {
                "chunk_id": "chk_sem_002",
                "strategy": "hierarchical",
                "source": "TT_02_2023_NHNN.pdf",
                "page_start": 2,
                "page_end": 3,
                "text": "Điều 7 Khoản 2 quy định giữ nguyên nhóm nợ."
            }
        ]

        self.dummy_dim = self.config["embedding_dim"]
        vec1 = [0.1] * self.dummy_dim
        vec2 = [0.8] * self.dummy_dim
        self.sample_embeddings = [vec1, vec2]

        index_chunks(
            chunks=self.sample_chunks,
            embeddings=self.sample_embeddings,
            strategy=self.strategy,
            config=self.config,
            reset=True,
            chroma_dir=self.chroma_path
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_semantic_top_k_count_and_order(self):
        """1. Semantic top-k, count và thứ tự khoảng cách Cosine trả về chính xác."""
        query_vec = [0.1] * self.dummy_dim
        results = search_semantic(
            question="Cơ cấu nợ quy định thế nào?",
            strategy=self.strategy,
            candidate_k=2,
            chroma_dir=self.chroma_path,
            mock_query_vec=query_vec
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["chunk_id"], "chk_sem_001")
        self.assertEqual(results[0]["semantic_rank"], 1)
        self.assertLessEqual(results[0]["semantic_distance"], results[1]["semantic_distance"])

    def test_02_semantic_result_metadata_completeness(self):
        """2. Kết quả truy xuất chứa đầy đủ thuộc tính metadata chuẩn."""
        query_vec = [0.1] * self.dummy_dim
        results = search_semantic(
            question="Cơ cấu nợ quy định thế nào?",
            strategy=self.strategy,
            candidate_k=1,
            chroma_dir=self.chroma_path,
            mock_query_vec=query_vec
        )

        item = results[0]
        required_keys = ["chunk_id", "text", "source", "page_start", "page_end", "semantic_rank", "semantic_distance"]
        for k in required_keys:
            self.assertIn(k, item)
            self.assertIsNotNone(item[k])

    def test_03_collection_mismatch_blocked(self):
        """3. Collection metadata không khớp với cấu hình hiện tại bị chặn (ValueError)."""
        client = get_chroma_client(self.chroma_path)
        col_name = get_collection_name(self.strategy, self.dummy_dim, self.config["embedding_model"])
        col = client.get_collection(name=col_name)

        col.modify(metadata={"strategy": "fixed-size", "embedding_model": self.config["embedding_model"], "embedding_dim": self.dummy_dim})

        query_vec = [0.1] * self.dummy_dim
        with self.assertRaises(ValueError):
            search_semantic(
                question="Cơ cấu nợ",
                strategy=self.strategy,
                candidate_k=1,
                chroma_dir=self.chroma_path,
                mock_query_vec=query_vec
            )

    def test_04_status_command_does_not_create_collection(self):
        """4. Status command hoạt động read-only, không tự tạo collection mới."""
        empty_dir = tempfile.TemporaryDirectory()
        try:
            empty_path = Path(empty_dir.name)
            st = get_advanced_status(strategy="hierarchical", chroma_dir=empty_path)
            self.assertFalse(st["collection_exists"])
            self.assertEqual(st["collection_count"], 0)

            client = get_chroma_client(empty_path)
            self.assertEqual(len(client.list_collections()), 0)
        finally:
            try:
                empty_dir.cleanup()
            except Exception:
                pass

    def test_05_missing_api_key_blocks_fake_vectors(self):
        """5. Thiếu GEMINI_API_KEY bị chặn rõ ràng, không tạo vector giả khi không có mock query_vec."""
        orig_key = os.environ.get("GEMINI_API_KEY", "")
        os.environ["GEMINI_API_KEY"] = ""

        try:
            with self.assertRaises(ValueError):
                search_semantic(
                    question="Cơ cấu nợ",
                    strategy=self.strategy,
                    candidate_k=1,
                    chroma_dir=self.chroma_path,
                    mock_query_vec=None
                )
        finally:
            os.environ["GEMINI_API_KEY"] = orig_key

    def test_06_no_generation_call(self):
        """6. Chức năng Semantic candidate stage hoàn toàn không gọi LLM generation."""
        query_vec = [0.1] * self.dummy_dim
        results = search_semantic(
            question="Cơ cấu nợ",
            strategy=self.strategy,
            candidate_k=1,
            chroma_dir=self.chroma_path,
            mock_query_vec=query_vec
        )
        self.assertNotIn("answer", results[0])


if __name__ == "__main__":
    unittest.main()
