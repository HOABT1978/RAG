import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Đảm bảo import được module rag
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rag


class TestRAGPipeline(unittest.TestCase):

    def test_validate_chunk(self):
        """Kiểm tra validation dữ liệu chunk JSON."""
        valid_chunk = {
            "chunk_id": "TT_02:0001",
            "text": "Nội dung điều khoản...",
            "source": "TT_02.pdf",
            "page_start": 1,
            "page_end": 2
        }
        invalid_chunk_1 = {
            "chunk_id": "",
            "text": "Thiếu chunk_id",
            "source": "TT_02.pdf"
        }
        invalid_chunk_2 = {
            "chunk_id": "TT_02:0002",
            "text": "",
            "source": "TT_02.pdf"
        }
        invalid_chunk_3 = "not a dict"

        self.assertTrue(rag._validate_chunk(valid_chunk))
        self.assertFalse(rag._validate_chunk(invalid_chunk_1))
        self.assertFalse(rag._validate_chunk(invalid_chunk_2))
        self.assertFalse(rag._validate_chunk(invalid_chunk_3))

    @patch("rag._get_gemini_client")
    def test_no_fake_vectors_on_embedding_error(self, mock_get_client):
        """Kiểm tra không tạo vector giả khi client bị thiếu hoặc lỗi embedding."""
        mock_get_client.return_value = None

        # Khi gọi index không có client/API key -> Phải báo lỗi chứ không tạo vector giả
        with self.assertRaises(ValueError) as ctx:
            rag.index()

        self.assertIn("Không tạo vector giả", str(ctx.exception))

    @patch("rag._get_gemini_client")
    @patch("rag._get_chroma_collection")
    @patch("rag._get_db_connection")
    @patch("rag._embed_text")
    def test_ask_with_insufficient_context(self, mock_embed, mock_db_conn, mock_chroma, mock_get_client):
        """Kiểm tra xử lý khi tài liệu không tìm thấy chunk phù hợp."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_embed.return_value = [0.1] * 384

        # Mock ChromaDB trả về danh sách rỗng
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"ids": [[]]}
        mock_chroma.return_value = mock_collection

        # Mock DB connection
        mock_conn = MagicMock()
        mock_db_conn.return_value = (mock_conn, "sqlite")

        result = rag.ask("Câu hỏi không có trong tài liệu?", k=3)

        self.assertIn("Tài liệu không đủ thông tin", result["answer"])
        self.assertEqual(len(result["chunks"]), 0)

    @patch("rag._get_gemini_client")
    @patch("rag._get_chroma_collection")
    @patch("rag._get_db_connection")
    @patch("rag._embed_text")
    @patch("rag._get_chunks_by_ids")
    def test_ask_citations_metadata(self, mock_get_chunks, mock_embed, mock_db_conn, mock_chroma, mock_get_client):
        """Kiểm tra câu trả lời được gửi prompt đính kèm metadata thật từ chunk."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Căn cứ theo [Nguồn: TT_02_2023_NHNN.pdf, Trang: 1-2, Chunk: TT_02:0001], ngân hàng cho phép cơ cấu nợ."
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        mock_embed.return_value = [0.1] * 384

        mock_collection = MagicMock()
        mock_collection.query.return_value = {"ids": [["TT_02:0001"]]}
        mock_chroma.return_value = mock_collection

        mock_conn = MagicMock()
        mock_db_conn.return_value = (mock_conn, "sqlite")

        mock_get_chunks.return_value = [{
            "chunk_id": "TT_02:0001",
            "source": "TT_02_2023_NHNN.pdf",
            "strategy": "semantic",
            "page_start": 1,
            "page_end": 2,
            "text": "Ngân hàng được cơ cấu lại thời hạn trả nợ cho khách hàng."
        }]

        result = rag.ask("Điều kiện cơ cấu lại thời hạn trả nợ?", k=1)

        self.assertEqual(len(result["chunks"]), 1)
        self.assertEqual(result["chunks"][0]["source"], "TT_02_2023_NHNN.pdf")
        self.assertEqual(result["chunks"][0]["page_start"], 1)
        self.assertEqual(result["chunks"][0]["page_end"], 2)
        self.assertIn("Nguồn: TT_02_2023_NHNN.pdf", result["answer"])


if __name__ == "__main__":
    unittest.main()
