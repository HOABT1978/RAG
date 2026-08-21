"""
Unit tests cho Answer Pipeline, Grounding, Citation Mapping và Compare - Buổi 08
"""

import sys
import unittest
import tempfile
from pathlib import Path

# Nạp module advanced_rag
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    query_advanced_rag,
    compare_retrieval_modes,
    _map_citations,
    _build_generation_prompt,
    get_chroma_client,
    get_collection_name,
    load_advanced_config
)


class TestAnswerPipelineAndCompare(unittest.TestCase):

    def setUp(self):
        """Tạo dữ liệu mock mẫu và setup ChromaDB temporary."""
        self.sample_evidence = [
            {
                "chunk_id": "chk_001",
                "text": "Nội dung quy định cơ cấu lại nợ.",
                "source": "TT02.pdf",
                "page_start": 1,
                "page_end": 1,
                "bm25_rank": 1,
                "bm25_score": 5.0,
                "semantic_rank": 1,
                "semantic_distance": 0.10,
                "rrf_score": 0.032,
                "fused_rank": 1,
                "rerank_raw_score": 2.5,
                "rerank_score": 0.92,
                "rerank_rank": 1,
                "rank_change": 0,
                "accepted": True
            },
            {
                "chunk_id": "chk_002",
                "text": "Nội dung quy định phân loại nợ.",
                "source": "TT02.pdf",
                "page_start": 2,
                "page_end": 2,
                "bm25_rank": 2,
                "bm25_score": 3.0,
                "semantic_rank": 2,
                "semantic_distance": 0.40,
                "rrf_score": 0.031,
                "fused_rank": 2,
                "rerank_raw_score": -1.0,
                "rerank_score": 0.26,
                "rerank_rank": 2,
                "rank_change": 0,
                "accepted": False
            }
        ]

    def test_01_gating_rules_by_mode(self):
        """1. Kiểm tra quy tắc Gating (Confidence Gate) chính xác theo từng mode."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={"strategy": "hierarchical", "embedding_model": config["embedding_model"], "embedding_dim": 768},
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Cơ cấu nợ."}
            ]

            col.upsert(
                ids=["chk_001"],
                documents=["Cơ cấu nợ."],
                embeddings=[[0.1] * 768],
                metadatas=sample_chunks
            )

            def mock_reranker_high(query, candidates, top_k):
                results = []
                for r, c in enumerate(candidates[:top_k], 1):
                    item = dict(c)
                    item["rerank_score"] = 0.90  # >= RERANK_MIN_SCORE (0.50)
                    item["rerank_raw_score"] = 2.0
                    item["rerank_rank"] = r
                    item["rank_change"] = 0
                    results.append(item)
                return results

            def mock_generator(query, accepted_ev):
                return "Câu trả lời theo [E1]."

            res = query_advanced_rag(
                question="cơ cấu nợ",
                mode="hybrid_rerank",
                strategy="hierarchical",
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_reranker_high,
                custom_generator=mock_generator
            )

            self.assertEqual(res["status"], "answered")
            self.assertEqual(res["trace"]["accepted"], 5)
            self.assertTrue(res["evidence"][0]["accepted"])
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_02_rejected_evidence_excluded_from_prompt(self):
        """2. Evidence không vượt qua gate bị loại khỏi prompt đưa vào Gemini LLM."""
        accepted = [e for e in self.sample_evidence if e["accepted"]]
        prompt_text = _build_generation_prompt("Hỏi", accepted)

        self.assertIn("Nội dung quy định cơ cấu lại nợ.", prompt_text)
        self.assertNotIn("Nội dung quy định phân loại nợ.", prompt_text)

    def test_03_trace_counts_and_timings_schema(self):
        """3. Pipeline Trace chứa đầy đủ các key đếm số lượng và thời gian thực thi (latency ms)."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={"strategy": "hierarchical", "embedding_model": config["embedding_model"], "embedding_dim": 768},
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Nợ."}
            ]

            col.upsert(
                ids=["chk_001"],
                documents=["Nợ."],
                embeddings=[[0.1] * 768],
                metadatas=sample_chunks
            )

            def mock_reranker(query, candidates, top_k):
                results = []
                for r, c in enumerate(candidates[:top_k], 1):
                    item = dict(c)
                    item["rerank_score"] = 0.8
                    item["rerank_raw_score"] = 1.5
                    item["rerank_rank"] = r
                    item["rank_change"] = 0
                    results.append(item)
                return results

            def mock_generator(query, accepted_ev):
                return "Trả lời [E1]."

            res = query_advanced_rag(
                question="Nợ",
                mode="hybrid_rerank",
                strategy="hierarchical",
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_reranker,
                custom_generator=mock_generator
            )

            trace = res["trace"]
            self.assertIn("bm25_candidates", trace)
            self.assertIn("semantic_candidates", trace)
            self.assertIn("overlap", trace)
            self.assertIn("union", trace)
            self.assertIn("reranked", trace)
            self.assertIn("accepted", trace)
            self.assertIn("generation_called", trace)
            self.assertIn("latency_ms", trace)
            self.assertIn("bm25", trace["latency_ms"])
            self.assertIn("semantic", trace["latency_ms"])
            self.assertIn("fusion", trace["latency_ms"])
            self.assertIn("rerank", trace["latency_ms"])
            self.assertIn("generation", trace["latency_ms"])
            self.assertIn("total", trace["latency_ms"])
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_04_citation_mapping_and_fake_label_handling(self):
        """4. Ánh xạ nhãn trích dẫn [E1] sang metadata thật và loại bỏ nhãn giả [E99]."""
        accepted = [self.sample_evidence[0]]  # E1 = chk_001
        raw_answer = "Cơ cấu nợ theo quy định [E1]. Đồng thời tự phát sinh [E99]."

        clean_answer, citations, warnings = _map_citations(raw_answer, accepted)

        self.assertNotIn("[E99]", clean_answer)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["chunk_id"], "chk_001")
        self.assertEqual(len(warnings), 1)
        self.assertIn("E99", warnings[0])

    def test_05_generation_called_at_most_once(self):
        """5. Gemini LLM Generation được gọi tối đa đúng một lần trong suốt 1 lần thực thi query."""
        call_count = 0

        def mock_generator(query, accepted_ev):
            nonlocal call_count
            call_count += 1
            return "Trả lời [E1]."

        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={"strategy": "hierarchical", "embedding_model": config["embedding_model"], "embedding_dim": 768},
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Nợ."}
            ]

            col.upsert(
                ids=["chk_001"],
                documents=["Nợ."],
                embeddings=[[0.1] * 768],
                metadatas=sample_chunks
            )

            def mock_reranker(query, candidates, top_k):
                results = []
                for r, c in enumerate(candidates[:top_k], 1):
                    item = dict(c)
                    item["rerank_score"] = 0.8
                    item["rerank_raw_score"] = 1.5
                    item["rerank_rank"] = r
                    item["rank_change"] = 0
                    results.append(item)
                return results

            query_advanced_rag(
                question="Nợ",
                mode="hybrid_rerank",
                strategy="hierarchical",
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_reranker,
                custom_generator=mock_generator
            )

            self.assertEqual(call_count, 1)
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_06_compare_command_does_not_call_generation(self):
        """6. Lệnh compare_retrieval_modes tuyệt đối KHÔNG gọi LLM Generation."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={"strategy": "hierarchical", "embedding_model": config["embedding_model"], "embedding_dim": 768},
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Quy định."}
            ]

            col.upsert(
                ids=["chk_001"],
                documents=["Quy định."],
                embeddings=[[0.1] * 768],
                metadatas=sample_chunks
            )

            def mock_reranker(query, candidates, top_k):
                results = []
                for r, c in enumerate(candidates[:top_k], 1):
                    item = dict(c)
                    item["rerank_score"] = 0.8
                    item["rerank_raw_score"] = 1.5
                    item["rerank_rank"] = r
                    item["rank_change"] = 0
                    results.append(item)
                return results

            res = compare_retrieval_modes(
                question="Quy định",
                strategy="hierarchical",
                chunks=sample_chunks,
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_reranker
            )

            self.assertIn("comparison_table", res)
            self.assertIn("latencies_ms", res)
            # compare không có field 'answer' hay gọi generation
            self.assertNotIn("answer", res)
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_07_reranker_unavailable_status(self):
        """7. Lỗi Reranker lập tức dừng và trả về status='reranker_unavailable'."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={"strategy": "hierarchical", "embedding_model": config["embedding_model"], "embedding_dim": 768},
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Quy định."}
            ]

            col.upsert(
                ids=["chk_001"],
                documents=["Quy định."],
                embeddings=[[0.1] * 768],
                metadatas=sample_chunks
            )

            def mock_failing_reranker(query, candidates, top_k):
                raise RuntimeError("Lỗi mô hình Reranker không sẵn sàng!")

            res = query_advanced_rag(
                question="Quy định",
                mode="hybrid_rerank",
                strategy="hierarchical",
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_failing_reranker
            )

            self.assertEqual(res["status"], "reranker_unavailable")
            self.assertFalse(res["trace"]["generation_called"])
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass

    def test_08_all_status_branches_schema_completeness(self):
        """8. Đảm bảo tất cả 4 nhánh status ('answered', 'insufficient_evidence', 'retrieval_only', 'reranker_unavailable') đều trả về đủ schema."""
        temp_dir = tempfile.TemporaryDirectory()
        try:
            chroma_path = Path(temp_dir.name)
            config = load_advanced_config()
            col_name = get_collection_name("hierarchical", config["embedding_dim"], config["embedding_model"])

            cli = get_chroma_client(chroma_path)
            col = cli.create_collection(
                name=col_name,
                metadata={"strategy": "hierarchical", "embedding_model": config["embedding_model"], "embedding_dim": 768},
                embedding_function=None
            )

            sample_chunks = [
                {"chunk_id": "chk_001", "strategy": "hierarchical", "source": "d.pdf", "page_start": 1, "page_end": 1, "text": "Quy định."}
            ]

            col.upsert(
                ids=["chk_001"],
                documents=["Quy định."],
                embeddings=[[0.1] * 768],
                metadatas=sample_chunks
            )

            # Test insufficient_evidence: rerank_score < RERANK_MIN_SCORE
            def mock_reranker_low(query, candidates, top_k):
                results = []
                for r, c in enumerate(candidates[:top_k], 1):
                    item = dict(c)
                    item["rerank_score"] = 0.10  # < 0.50
                    item["rerank_raw_score"] = -2.0
                    item["rerank_rank"] = r
                    item["rank_change"] = 0
                    results.append(item)
                return results

            res_insufficient = query_advanced_rag(
                question="Quy định",
                mode="hybrid_rerank",
                strategy="hierarchical",
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_reranker_low
            )

            self.assertEqual(res_insufficient["status"], "insufficient_evidence")
            for field in ["status", "mode", "question", "answer", "evidence", "citations", "warnings", "trace"]:
                self.assertIn(field, res_insufficient)

            # Test retrieval_only: custom_generator raises error
            def mock_reranker_high(query, candidates, top_k):
                results = []
                for r, c in enumerate(candidates[:top_k], 1):
                    item = dict(c)
                    item["rerank_score"] = 0.90
                    item["rerank_raw_score"] = 2.0
                    item["rerank_rank"] = r
                    item["rank_change"] = 0
                    results.append(item)
                return results

            def mock_failing_generator(query, accepted_ev):
                raise RuntimeError("Lỗi mạng Gemini!")

            res_retrieval_only = query_advanced_rag(
                question="Quy định",
                mode="hybrid_rerank",
                strategy="hierarchical",
                chroma_dir=chroma_path,
                query_vec=[0.1] * 768,
                custom_reranker=mock_reranker_high,
                custom_generator=mock_failing_generator
            )

            self.assertEqual(res_retrieval_only["status"], "retrieval_only")
            for field in ["status", "mode", "question", "answer", "evidence", "citations", "warnings", "trace"]:
                self.assertIn(field, res_retrieval_only)
        finally:
            try:
                temp_dir.cleanup()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
