import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import rag


class TestEmbeddingAndIndexing(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="idx_test_")).resolve()
        self.config = {
            "api_key": "mock_test_key",
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 128,
            "generation_model": "gemini-3.5-flash-lite",
            "default_top_k": 5,
            "max_distance": 0.45
        }
        self.chunks = [
            {"chunk_id": "C1", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 1, "page_end": 1, "text": "Text 1"},
            {"chunk_id": "C2", "strategy": "hierarchical", "source": "doc.pdf", "page_start": 2, "page_end": 2, "text": "Text 2"}
        ]
        self.valid_vectors = [[0.1] * 128, [0.2] * 128]
        self.patcher = patch("rag.load_config", return_value=self.config)
        self.mock_load_config = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_10_index_two_times_does_not_increase_count(self):
        """10. Indexing twice does not increase record count (Idempotent)."""
        res1 = rag.index_chunks(self.chunks, self.valid_vectors, "hierarchical", self.config, reset=False, chroma_dir=self.temp_dir)
        self.assertEqual(res1["count"], 2)

        res2 = rag.index_chunks(self.chunks, self.valid_vectors, "hierarchical", self.config, reset=False, chroma_dir=self.temp_dir)
        self.assertEqual(res2["count"], 2)

    def test_11_metadata_citation_saved_completely(self):
        """11. Metadata citation attributes are completely stored in ChromaDB."""
        rag.index_chunks(self.chunks, self.valid_vectors, "hierarchical", self.config, reset=False, chroma_dir=self.temp_dir)
        client = rag.get_chroma_client(self.temp_dir)
        col_name = rag.get_collection_name("hierarchical", 128, "gemini-embedding-2")
        col = client.get_collection(col_name)

        item = col.get(ids=["C1"], include=["metadatas"])
        meta = item["metadatas"][0]
        self.assertEqual(meta["source"], "doc.pdf")
        self.assertEqual(meta["page_start"], 1)
        self.assertEqual(meta["page_end"], 1)
        self.assertEqual(meta["chunk_id"], "C1")

    def test_12_collection_identity_changes_with_strategy(self):
        """12. Collection identity changes when strategy changes."""
        col_h = rag.get_collection_name("hierarchical", 128, "gemini-embedding-2")
        col_s = rag.get_collection_name("semantic", 128, "gemini-embedding-2")
        self.assertNotEqual(col_h, col_s)
        self.assertIn("hierarchical", col_h)
        self.assertIn("semantic", col_s)

    def test_13_collection_identity_changes_with_model_or_dim(self):
        """13. Collection identity changes when model or dimension changes."""
        col1 = rag.get_collection_name("hierarchical", 128, "gemini-embedding-2")
        col2 = rag.get_collection_name("hierarchical", 768, "gemini-embedding-2")
        col3 = rag.get_collection_name("hierarchical", 128, "text-embedding-004")
        self.assertNotEqual(col1, col2)
        self.assertNotEqual(col1, col3)

    def test_15_embedding_wrong_count_fails(self):
        """15. Embedding returning wrong count fails validation."""
        with self.assertRaises(ValueError):
            rag.validate_embeddings([[0.1] * 128], expected_count=2, expected_dim=128)

    def test_16_embedding_empty_vector_fails(self):
        """16. Empty vector in embeddings fails validation."""
        with self.assertRaises(ValueError):
            rag.validate_embeddings([[]], expected_count=1, expected_dim=128)

    def test_17_embedding_wrong_dimension_fails(self):
        """17. Vector with wrong dimension fails validation."""
        with self.assertRaises(ValueError):
            rag.validate_embeddings([[0.1] * 64], expected_count=1, expected_dim=128)

    def test_18_embedding_nan_or_inf_fails(self):
        """18. Vector with NaN or Infinity fails validation."""
        with self.assertRaises(ValueError):
            rag.validate_embeddings([[float("nan")] * 128], expected_count=1, expected_dim=128)
        with self.assertRaises(ValueError):
            rag.validate_embeddings([[float("inf")] * 128], expected_count=1, expected_dim=128)

    def test_19_embedding_error_before_upsert_does_not_add_records(self):
        """19. Embedding error before upsert prevents adding new records."""
        with patch("rag.generate_single_embedding", side_effect=RuntimeError("Embedding Failed")):
            with self.assertRaises(RuntimeError):
                rag.generate_embeddings(self.chunks, self.config, client=MagicMock())

        # Verify no collection created
        client = rag.get_chroma_client(self.temp_dir)
        self.assertEqual(len(client.list_collections()), 0)

    def test_20_missing_api_key_fails_and_no_fake_vectors(self):
        """20. Missing API key fails clearly without creating fake vectors."""
        no_key_config = {**self.config, "has_api_key": False, "api_key": ""}
        with self.assertRaises(ValueError) as ctx:
            rag.generate_embeddings(self.chunks, no_key_config)
        self.assertIn("Thiếu GEMINI_API_KEY", str(ctx.exception))

    def test_39_embedding_blocks_boolean_and_zero_vector(self):
        """39. Embedding validation blocks boolean and zero vector."""
        # Zero vector -> FAIL
        with self.assertRaises(ValueError):
            rag.validate_embeddings([[0.0] * 128], expected_count=1, expected_dim=128)
        # Boolean in vector -> FAIL
        with self.assertRaises(TypeError):
            rag.validate_embeddings([[True] + [0.1] * 127], expected_count=1, expected_dim=128)

    def test_40_status_on_empty_storage_does_not_create_collection(self):
        """40. status command on empty storage does not create collection."""
        st_res = rag.get_status(strategy="hierarchical", chroma_dir=self.temp_dir)
        self.assertFalse(st_res["collection_exists"])
        self.assertEqual(st_res["record_count"], 0)

        client = rag.get_chroma_client(self.temp_dir)
        self.assertEqual(len(client.list_collections()), 0)

    def test_41_reset_on_embedding_error_preserves_old_valid_collection(self):
        """41. --reset with embedding error preserves old valid collection."""
        rag.index_chunks(self.chunks, self.valid_vectors, "hierarchical", self.config, reset=False, chroma_dir=self.temp_dir)
        st_before = rag.get_status(strategy="hierarchical", chroma_dir=self.temp_dir)
        self.assertEqual(st_before["record_count"], 2)

        with patch("rag.generate_single_embedding", side_effect=RuntimeError("API error")):
            with self.assertRaises(RuntimeError):
                rag.generate_embeddings(self.chunks, self.config, client=MagicMock())

        st_after = rag.get_status(strategy="hierarchical", chroma_dir=self.temp_dir)
        self.assertTrue(st_after["collection_exists"])
        self.assertEqual(st_after["record_count"], 2)

    def test_42_existing_collection_metadata_mismatch_blocked(self):
        """42. Mismatch collection metadata is blocked before query or upsert."""
        rag.index_chunks(self.chunks, self.valid_vectors, "hierarchical", self.config, reset=False, chroma_dir=self.temp_dir)
        client = rag.get_chroma_client(self.temp_dir)
        col_name = rag.get_collection_name("hierarchical", 128, "gemini-embedding-2")
        col = client.get_collection(col_name)

        mismatched_config = {**self.config, "embedding_dim": 768}
        with self.assertRaises(ValueError) as ctx:
            rag.verify_collection_metadata(col, "hierarchical", mismatched_config)
        self.assertIn("Mismatch collection embedding dimension", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
