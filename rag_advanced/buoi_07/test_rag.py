import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rag


class TestRAGPipelineBuoi07(unittest.TestCase):

    def test_validate_chunk(self):
        valid_chunk = {
            "chunk_id": "TT_02:0001",
            "text": "Nội dung điều khoản...",
            "source": "TT_02.pdf",
            "page_start": 1,
            "page_end": 2
        }
        invalid_chunk = {
            "chunk_id": "",
            "text": "Thiếu chunk_id",
            "source": "TT_02.pdf"
        }

        self.assertTrue(rag._validate_chunk(valid_chunk))
        self.assertFalse(rag._validate_chunk(invalid_chunk))

    @patch("rag._get_gemini_client")
    def test_no_fake_vectors_on_embedding_error(self, mock_get_client):
        mock_get_client.return_value = None

        with self.assertRaises(ValueError) as ctx:
            rag.index()

        self.assertIn("Không tạo vector giả", str(ctx.exception))

    @patch("rag._get_gemini_client")
    @patch("rag._get_chroma_collection")
    @patch("rag._get_db_connection")
    @patch("rag._embed_text")
    def test_ask_with_insufficient_context(self, mock_embed, mock_db_conn, mock_chroma, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_embed.return_value = [0.1] * 384

        mock_collection = MagicMock()
        mock_collection.query.return_value = {"ids": [[]]}
        mock_chroma.return_value = mock_collection

        mock_conn = MagicMock()
        mock_db_conn.return_value = (mock_conn, "sqlite")

        result = rag.ask("Câu hỏi không có trong tài liệu?", k=3)

        self.assertIn("Tài liệu không đủ thông tin", result["answer"])
        self.assertEqual(len(result["chunks"]), 0)


if __name__ == "__main__":
    unittest.main()
