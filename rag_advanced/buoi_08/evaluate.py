"""
Module Đánh giá Offline (Evaluator) - Buổi 08
Tính toán các chỉ số Retrieval Quality Metrics: Recall@K, MRR@K, nDCG@K và Latency (Mean, P50).
Không gọi LLM Generation. Xuất báo cáo JSON trong thư mục reports/.
"""

import os
import sys
import json
import time
import math
import statistics
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    load_advanced_config,
    load_chunks,
    search_bm25,
    search_semantic,
    search_hybrid,
    search_hybrid_rerank
)


# ---------------------------------------------------------------------------
# 1. RETRIEVAL QUALITY METRIC FORMULAS (BINARY RELEVANCE)
# ---------------------------------------------------------------------------

def calculate_recall_at_k(retrieved_ids: List[str], gold_ids: List[str], k: int) -> float:
    """
    Tính Recall@K = |Retrieved@K ∩ Gold| / |Gold|
    """
    if not gold_ids or k <= 0:
        return 0.0
    top_k_retrieved = set(retrieved_ids[:k])
    gold_set = set(gold_ids)
    intersection = top_k_retrieved & gold_set
    return len(intersection) / len(gold_set)


def calculate_mrr_at_k(retrieved_ids: List[str], gold_ids: List[str], k: int) -> float:
    """
    Tính Mean Reciprocal Rank (MRR@K) = 1 / rank_dầu_tiên_đúng trong Top-K (nếu không thấy trả về 0.0).
    """
    if not gold_ids or k <= 0:
        return 0.0
    gold_set = set(gold_ids)
    for rank, cid in enumerate(retrieved_ids[:k], 1):
        if cid in gold_set:
            return 1.0 / rank
    return 0.0


def calculate_ndcg_at_k(retrieved_ids: List[str], gold_ids: List[str], k: int) -> float:
    """
    Tính Normalized Discounted Cumulative Gain (nDCG@K) với Binary Relevance:
    DCG@K = sum_{i=1}^K (rel_i / log2(i + 1))
    IDCG@K = sum_{i=1}^{min(K, |Gold|)} (1 / log2(i + 1))
    nDCG@K = DCG@K / IDCG@K
    """
    if not gold_ids or k <= 0:
        return 0.0

    gold_set = set(gold_ids)
    top_k_retrieved = retrieved_ids[:k]

    dcg = 0.0
    for idx, cid in enumerate(top_k_retrieved, 1):
        rel = 1.0 if cid in gold_set else 0.0
        dcg += rel / math.log2(idx + 1)

    ideal_count = min(k, len(gold_set))
    idcg = 0.0
    for idx in range(1, ideal_count + 1):
        idcg += 1.0 / math.log2(idx + 1)

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


# ---------------------------------------------------------------------------
# 2. EVALUATION PIPELINE
# ---------------------------------------------------------------------------

def run_evaluation(
    questions_file: Optional[Path] = None,
    strategy: str = "hierarchical",
    k: int = 5,
    modes: Optional[List[str]] = None,
    custom_bm25_retriever: Optional[Any] = None,
    custom_semantic_retriever: Optional[Any] = None,
    custom_reranker: Optional[Any] = None
) -> dict:
    """
    Thực thi đánh giá benchmark retrieval trên tập bộ câu hỏi test.
    Tuyệt đối không gọi LLM generation.
    """
    config = load_advanced_config()
    if modes is None:
        modes = ["bm25", "semantic", "hybrid", "hybrid_rerank"]

    target_q_file = questions_file if questions_file else BASE_DIR / "eval" / "questions.json"
    if not target_q_file.exists():
        raise FileNotFoundError(f"Tập câu hỏi đánh giá '{target_q_file}' không tồn tại.")

    with open(target_q_file, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    if isinstance(eval_data, list):
        questions_list = eval_data
    elif isinstance(eval_data, dict):
        questions_list = eval_data.get("questions", [])
    else:
        questions_list = []
    if not questions_list:
        raise ValueError("Tập câu hỏi đánh giá 'questions' trong file JSON bị rỗng.")

    has_needs_review = any(q.get("needs_human_review", False) for q in questions_list)

    results_by_mode = {}

    for mode in modes:
        recalls = []
        mrrs = []
        ndcgs = []
        latencies = []
        query_details = []

        for idx, q_item in enumerate(questions_list, 1):
            qid = q_item.get("id", f"q_{idx}")
            question_text = q_item["question"]
            gold_chunk_ids = q_item.get("relevant_chunk_ids", [])

            t0 = time.perf_counter()
            retrieved_chunks = []
            error_msg = None

            try:
                if mode == "bm25":
                    if custom_bm25_retriever:
                        retrieved_chunks = custom_bm25_retriever(question_text, config["bm25_candidates"])
                    else:
                        retrieved_chunks = search_bm25(question_text, top_k=config["bm25_candidates"], strategy=strategy)
                elif mode == "semantic":
                    if custom_semantic_retriever:
                        retrieved_chunks = custom_semantic_retriever(question_text, config["semantic_candidates"])
                    else:
                        retrieved_chunks = search_semantic(question_text, strategy=strategy, candidate_k=config["semantic_candidates"])
                elif mode == "hybrid":
                    hyb = search_hybrid(question_text, strategy=strategy, custom_bm25_retriever=custom_bm25_retriever, custom_semantic_retriever=custom_semantic_retriever)
                    retrieved_chunks = hyb["results"]
                elif mode == "hybrid_rerank":
                    rr = search_hybrid_rerank(question_text, strategy=strategy, custom_bm25_retriever=custom_bm25_retriever, custom_semantic_retriever=custom_semantic_retriever, custom_reranker=custom_reranker)
                    retrieved_chunks = rr["results"]
            except Exception as err:
                error_msg = str(err)
                retrieved_chunks = []

            t1 = time.perf_counter()
            lat_ms = round((t1 - t0) * 1000, 2)
            latencies.append(lat_ms)

            retrieved_ids = [c["chunk_id"] for c in retrieved_chunks]

            rec = calculate_recall_at_k(retrieved_ids, gold_chunk_ids, k)
            mrr = calculate_mrr_at_k(retrieved_ids, gold_chunk_ids, k)
            ndcg = calculate_ndcg_at_k(retrieved_ids, gold_chunk_ids, k)

            recalls.append(rec)
            mrrs.append(mrr)
            ndcgs.append(ndcg)

            query_details.append({
                "question_id": qid,
                "question": question_text,
                "gold_ids": gold_chunk_ids,
                "retrieved_ids_top_k": retrieved_ids[:k],
                "recall_at_k": round(rec, 4),
                "mrr_at_k": round(mrr, 4),
                "ndcg_at_k": round(ndcg, 4),
                "latency_ms": lat_ms,
                "status": "error" if error_msg else "success",
                "error": error_msg
            })

        mean_recall = float(statistics.mean(recalls)) if recalls else 0.0
        mean_mrr = float(statistics.mean(mrrs)) if mrrs else 0.0
        mean_ndcg = float(statistics.mean(ndcgs)) if ndcgs else 0.0
        mean_lat = float(statistics.mean(latencies)) if latencies else 0.0
        p50_lat = float(statistics.median(latencies)) if latencies else 0.0

        results_by_mode[mode] = {
            "recall_at_k": round(mean_recall, 4),
            "mrr_at_k": round(mean_mrr, 4),
            "ndcg_at_k": round(mean_ndcg, 4),
            "latency_mean_ms": round(mean_lat, 2),
            "latency_p50_ms": round(p50_lat, 2),
            "evaluated_queries_count": len(questions_list),
            "queries": query_details
        }

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"eval_report_{strategy}_k{k}_{timestamp_str}.json"
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename

    warning_info = {
        "has_review_flag": has_needs_review,
        "message": (
            "CẢNH BÁO: Tập câu hỏi đánh giá gold labels có câu hỏi gắn nhãn 'needs_human_review': true. "
            "Báo cáo này KHÔNG tuyên bố mode thắng cuộc chính thức cho tới khi tập dữ liệu được kiểm duyệt 100%."
            if has_needs_review else "Tập dữ liệu câu hỏi đã hoàn tất kiểm duyệt."
        )
    }

    report_payload = {
        "timestamp": timestamp_str,
        "strategy": strategy,
        "k": k,
        "model_identity": {
            "embedding_model": config["embedding_model"],
            "embedding_dim": config["embedding_dim"],
            "reranker_model": config["reranker_model"]
        },
        "needs_human_review_warning": warning_info,
        "results_by_mode": results_by_mode
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, ensure_ascii=False, indent=2)

    return {
        "report_path": str(report_path),
        "report": report_payload
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Advanced RAG Evaluator - Buổi 08")
    parser.add_argument("--strategy", default="hierarchical", choices=["fixed-size", "semantic", "hierarchical"])
    parser.add_argument("--k", type=int, default=5, help="Giá trị K cho Recall@K, MRR@K, nDCG@K")

    args = parser.parse_args()

    print(f"🚀 [EVALUATOR] Đang chạy đánh giá Benchmark Retrieval (Strategy: '{args.strategy}', K={args.k})...")
    res = run_evaluation(strategy=args.strategy, k=args.k)
    report = res["report"]

    print(f"\n✅ ĐÃ HOÀN THÀNH: Báo cáo đã lưu tại '{res['report_path']}'")
    print("=" * 80)
    if report["needs_human_review_warning"]["has_review_flag"]:
        print(f"⚠️ {report['needs_human_review_warning']['message']}\n")

    print(f"{'Mode':<16} | {'Recall@K':<10} | {'MRR@K':<10} | {'nDCG@K':<10} | {'Mean Latency':<14} | {'P50 Latency'}")
    print("-" * 80)
    for m_name, m_data in report["results_by_mode"].items():
        print(f"{m_name:<16} | {m_data['recall_at_k']:<10.4f} | {m_data['mrr_at_k']:<10.4f} | {m_data['ndcg_at_k']:<10.4f} | {m_data['latency_mean_ms']:<14.2f}ms | {m_data['latency_p50_ms']:.2f}ms")
    print("=" * 80 + "\n")
