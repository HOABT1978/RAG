"""
Unit tests cho Semantic Candidate Retrieval và Status Command - Buổi 08
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Nạp module advanced_rag
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import chromadb
from advanced_rag import (
    get_advanced_status,
    search_semantic,
    get_chroma_client,
    get_collection_name,
    load_advanced_config
)


class TestSemanticCandidateRetrieval(unittest.TestCase):

    def setUp(self):
        """Tạo môi trường ChromaDB tạm thời trong tempdir cho unit testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.chroma_path = Path(self.temp_dir.name)
        self.config = load_advanced_config()
        self.strategy = "hierarchical"

        self.col_name = get_collection_name(
            self.strategy,
            self.config["embedding_dim"],
            self.config["embedding_model"]
        )

        self.sample_chunks = [
            {
                "chunk_id": "chk_sem_001",
                "strategy": self.strategy,
                "source": "DocA.pdf",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung văn bản quy định về cơ cấu lại nợ."
            },
            {
                "chunk_id": "chk_sem_002",
                "strategy": self.strategy,
                "source": "DocB.pdf",
                "page_start": 2,
                "page_end": 3,
                "text": "Nội dung quy định về phân loại nhóm nợ."
            }
        ]

        # Vector có hướng khác nhau rõ rệt để thử nghiệm Cosine Distance
        vec1 = [1.0] + [0.0] * 767
        vec2 = [0.0] + [1.0] + [0.0] * 766
        self.mock_embeddings = [vec1, vec2]
        self.mock_query_vec = [0.9] + [0.1] + [0.0] * 766  # Gần vec1 hơn nhiều so với vec2

        cli = get_chroma_client(self.chroma_path)
        col = cli.create_collection(
            name=self.col_name,
            metadata={
                "strategy": self.strategy,
                "embedding_model": self.config["embedding_model"],
                "embedding_dim": int(self.config["embedding_dim"]),
                "distance_metric": "cosine"
            },
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}}
        )

        col.upsert(
            ids=[c["chunk_id"] for c in self.sample_chunks],
            documents=[c["text"] for c in self.sample_chunks],
            embeddings=self.mock_embeddings,
            metadatas=[
                {
                    "chunk_id": c["chunk_id"],
                    "strategy": c["strategy"],
                    "source": c["source"],
                    "page_start": c["page_start"],
                    "page_end": c["page_end"]
                }
                for c in self.sample_chunks
            ]
        )

    def tearDown(self):
        """Dọn dẹp thư mục tạm an toàn trên Windows."""
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_semantic_top_k_count_and_order(self):
        """1. Semantic top-k, count và thứ tự khoảng cách Cosine trả về chính xác."""
        results = search_semantic(
            question="Cơ cấu lại nợ",
            strategy=self.strategy,
            candidate_k=2,
            chroma_dir=self.chroma_path,
            query_vec=self.mock_query_vec
        )

        self.assertEqual(len(results), 2)
        # Vector 1 gần query_vec hơn vector 2 -> chk_sem_001 xếp trước (rank 1)
        self.assertEqual(results[0]["chunk_id"], "chk_sem_001")
        self.assertEqual(results[0]["semantic_rank"], 1)
        self.assertEqual(results[1]["semantic_rank"], 2)
        self.assertLessEqual(results[0]["semantic_distance"], results[1]["semantic_distance"])

    def test_02_semantic_result_metadata_completeness(self):
        """2. Kết quả truy xuất chứa đầy đủ thuộc tính metadata chuẩn."""
        results = search_semantic(
            question="Cơ cấu lại nợ",
            strategy=self.strategy,
            candidate_k=1,
            chroma_dir=self.chroma_path,
            query_vec=self.mock_query_vec
        )

        res = results[0]
        required_fields = {"chunk_id", "text", "source", "page_start", "page_end", "semantic_rank", "semantic_distance"}
        self.assertTrue(required_fields.issubset(res.keys()))
        self.assertEqual(res["source"], "DocA.pdf")
        self.assertEqual(res["page_start"], 1)

    def test_03_collection_mismatch_blocked(self):
        """3. Collection metadata không khớp với cấu hình hiện tại bị chặn (ValueError)."""
        cli = get_chroma_client(self.chroma_path)
        mismatched_col_name = get_collection_name("semantic", 768, self.config["embedding_model"])

        # Tạo collection sai metadata strategy
        cli.create_collection(
            name=mismatched_col_name,
            metadata={
                "strategy": "fixed-size",  # Mismatch với "semantic"
                "embedding_model": self.config["embedding_model"],
                "embedding_dim": 768
            },
            embedding_function=None
        )

        with self.assertRaises(ValueError):
            search_semantic(
                question="Test Mismatch",
                strategy="semantic",
                candidate_k=1,
                chroma_dir=self.chroma_path,
                query_vec=self.mock_query_vec
            )

    def test_04_status_command_does_not_create_collection(self):
        """4. Status command hoạt động read-only, không tự tạo collection mới."""
        import shutil
        empty_dir = tempfile.mkdtemp()
        try:
            empty_path = Path(empty_dir)
            cli = get_chroma_client(empty_path)

            # Ban đầu chưa có collection nào
            self.assertEqual(len(cli.list_collections()), 0)

            # Gọi get_advanced_status
            st_res = get_advanced_status(strategy="hierarchical", chroma_dir=empty_path)

            self.assertFalse(st_res["collection_exists"])
            self.assertEqual(st_res["collection_count"], 0)
            # Kiểm tra không có collection nào bị tự động tạo
            self.assertEqual(len(cli.list_collections()), 0)
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)

    def test_05_missing_api_key_blocks_fake_vectors(self):
        """5. Thiếu GEMINI_API_KEY bị chặn rõ ràng, không tạo vector giả khi không có mock query_vec."""
        old_key = self.config["api_key"]
        os.environ["GEMINI_API_KEY"] = ""

        try:
            with self.assertRaises(ValueError):
                search_semantic(
                    question="Thiếu API Key",
                    strategy=self.strategy,
                    candidate_k=1,
                    chroma_dir=self.chroma_path,
                    client=None,
                    query_vec=None  # Phải gọi API thật -> fail
                )
        finally:
            os.environ["GEMINI_API_KEY"] = old_key

    def test_06_no_generation_call(self):
        """6. Chức năng Semantic candidate stage hoàn toàn không gọi LLM generation."""
        results = search_semantic(
            question="Cơ cấu nợ",
            strategy=self.strategy,
            candidate_k=1,
            chroma_dir=self.chroma_path,
            query_vec=self.mock_query_vec
        )
        self.assertIsInstance(results, list)
        self.assertNotIn("answer", results[0])


if __name__ == "__main__":
    unittest.main()
