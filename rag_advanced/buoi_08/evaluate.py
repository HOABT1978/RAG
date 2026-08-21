"""
Module Đánh giá Offline (Evaluation Framework) - Buổi 08
Tính toán các chỉ số chất lượng truy xuất (Retrieval Quality Metrics):
- Recall@K
- MRR@K (Mean Reciprocal Rank)
- nDCG@K (Normalized Discounted Cumulative Gain với binary relevance)
- Latency Mean & P50 (median)

LƯU Ý: Tuyệt đối KHÔNG gọi LLM Generation trong quá trình đánh giá (0 cuộc gọi API generation).
"""

import os
import sys
import json
import math
import time
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from advanced_rag import (
    load_advanced_config,
    search_bm25,
    search_semantic,
    search_hybrid,
    search_hybrid_rerank,
    CrossEncoderReranker,
    load_chunks
)


# ---------------------------------------------------------------------------
# 1. METRIC FORMULA IMPLEMENTATIONS (PURE FUNCTIONS)
# ---------------------------------------------------------------------------

def calculate_recall_at_k(retrieved_ids: List[str], gold_ids: List[str], k: int = 5) -> float:
    """
    Tính chỉ số Recall@K: Tỷ lệ relevant chunks được truy xuất trong top-k so với tổng số relevant chunks.
    Formula: Recall@K = |Retrieved@K ∩ Gold| / |Gold|
    """
    if not gold_ids or k <= 0:
        return 0.0

    top_k_retrieved = list(dict.fromkeys(retrieved_ids[:k]))
    gold_set = set(gold_ids)
    hits = sum(1 for cid in top_k_retrieved if cid in gold_set)

    return round(hits / len(gold_set), 6)


def calculate_mrr_at_k(retrieved_ids: List[str], gold_ids: List[str], k: int = 5) -> float:
    """
    Tính chỉ số Mean Reciprocal Rank (MRR@K): Nghịch đảo vị trí của chunk phù hợp đầu tiên trong top-k.
    Formula: MRR@K = 1 / rank (với rank <= k của item phù hợp đầu tiên), ngược lại = 0.0.
    """
    if not gold_ids or k <= 0:
        return 0.0

    gold_set = set(gold_ids)
    top_k_retrieved = retrieved_ids[:k]

    for rank, cid in enumerate(top_k_retrieved, 1):
        if cid in gold_set:
            return round(1.0 / rank, 6)

    return 0.0


def calculate_ndcg_at_k(retrieved_ids: List[str], gold_ids: List[str], k: int = 5) -> float:
    """
    Tính chỉ số nDCG@K (Normalized Discounted Cumulative Gain với binary relevance):
    DCG@K = ∑_{i=1}^K (rel_i / log2(i + 1))
    IDCG@K = ∑_{i=1}^{min(K, |Gold|)} (1 / log2(i + 1))
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

    idcg_count = min(k, len(gold_set))
    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, idcg_count + 1))

    if idcg == 0.0:
        return 0.0

    return round(dcg / idcg, 6)


def calculate_p50(values: List[float]) -> float:
    """Tính vị trí P50 (median) từ danh sách số liệu."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return round(sorted_vals[mid], 2)
    else:
        return round((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0, 2)


# ---------------------------------------------------------------------------
# 2. EVALUATION DATASET RUNNER
# ---------------------------------------------------------------------------

def evaluate_dataset(
    questions_path: Path,
    modes: Optional[List[str]] = None,
    strategy: str = "hierarchical",
    top_k: int = 5,
    custom_reranker: Optional[Any] = None,
    custom_retrievers: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Thực thi đánh giá benchmark trên toàn bộ tập câu hỏi từ questions.json.
    Tuyệt đối KHÔNG gọi LLM Generation (0 cuộc gọi API generation).
    """
    config = load_advanced_config()

    if modes is None:
        modes = ["bm25", "semantic", "hybrid", "hybrid_rerank"]

    if not questions_path.exists():
        raise FileNotFoundError(f"File questions benchmark '{questions_path}' không tồn tại.")

    with open(questions_path, "r", encoding="utf-8") as f:
        questions_data = json.load(f)

    if not isinstance(questions_data, list) or len(questions_data) == 0:
        raise ValueError(f"Tập câu hỏi benchmark trong '{questions_path}' không được rỗng.")

    has_review_flag = any(q.get("needs_human_review", False) for q in questions_data)

    load_res = load_chunks(strategy=strategy)
    chunks = load_res["chunks"]

    report_by_mode = {}
    query_details = []

    for m in modes:
        recalls = []
        mrrs = []
        ndcgs = []
        latencies = []
        failed_count = 0

        for q_item in questions_data:
            qid = q_item.get("query_id", "Q_UNK")
            question = q_item.get("question", "").strip()
            gold_ids = q_item.get("relevant_chunk_ids", [])

            t0 = time.perf_counter()
            retrieved_ids = []
            err_msg = None

            try:
                if custom_retrievers and m in custom_retrievers:
                    retrieved_ids = custom_retrievers[m](question, top_k)
                else:
                    if m == "bm25":
                        res = search_bm25(question, chunks, top_k=config["bm25_candidates"])
                        retrieved_ids = [c["chunk_id"] for c in res]
                    elif m == "semantic":
                        res = search_semantic(question, strategy, candidate_k=config["semantic_candidates"])
                        retrieved_ids = [c["chunk_id"] for c in res]
                    elif m == "hybrid":
                        hyb_res = search_hybrid(question, strategy, chunks)
                        retrieved_ids = [c["chunk_id"] for c in hyb_res["results"]]
                    elif m == "hybrid_rerank":
                        hyb_rr_res = search_hybrid_rerank(question, strategy, chunks, custom_reranker=custom_reranker)
                        retrieved_ids = [c["chunk_id"] for c in hyb_rr_res["results"]]
            except Exception as e:
                err_msg = str(e)
                failed_count += 1

            t1 = time.perf_counter()
            latency_ms = round((t1 - t0) * 1000, 2)

            r_k = calculate_recall_at_k(retrieved_ids, gold_ids, top_k)
            mrr_k = calculate_mrr_at_k(retrieved_ids, gold_ids, top_k)
            ndcg_k = calculate_ndcg_at_k(retrieved_ids, gold_ids, top_k)

            recalls.append(r_k)
            mrrs.append(mrr_k)
            ndcgs.append(ndcg_k)
            latencies.append(latency_ms)

            query_details.append({
                "query_id": qid,
                "mode": m,
                "question": question,
                "gold_chunk_ids": gold_ids,
                "retrieved_chunk_ids": retrieved_ids[:top_k],
                "recall_at_k": r_k,
                "mrr_at_k": mrr_k,
                "ndcg_at_k": ndcg_k,
                "latency_ms": latency_ms,
                "error": err_msg
            })

        mean_recall = round(sum(recalls) / len(recalls), 4) if recalls else 0.0
        mean_mrr = round(sum(mrrs) / len(mrrs), 4) if mrrs else 0.0
        mean_ndcg = round(sum(ndcgs) / len(ndcgs), 4) if ndcgs else 0.0
        mean_lat = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        p50_lat = calculate_p50(latencies)

        report_by_mode[m] = {
            "recall_at_k": mean_recall,
            "mrr_at_k": mean_mrr,
            "ndcg_at_k": mean_ndcg,
            "latency_mean_ms": mean_lat,
            "latency_p50_ms": p50_lat,
            "evaluated_queries_count": len(questions_data),
            "failed_queries_count": failed_count
        }

    warning_msg = (
        "CẢNH BÁO: Tập dữ liệu gold labels có chứa câu hỏi mang nhãn 'needs_human_review=true'. "
        "Kết quả đánh giá mang tính chất tham khảo kỹ thuật; CHƯA TUYÊN BỐ MODE CHIẾN THẮNG CHÍNH THỨC."
        if has_review_flag else "Dữ liệu gold đã được kiểm duyệt hoàn toàn."
    )

    report_json = {
        "timestamp": datetime.datetime.now().isoformat(),
        "strategy": strategy,
        "k": top_k,
        "needs_human_review_warning": {
            "has_review_flag": has_review_flag,
            "message": warning_msg
        },
        "official_winner_declared": not has_review_flag,
        "model_identity": {
            "embedding_model": config["embedding_model"],
            "embedding_dim": config["embedding_dim"],
            "reranker_model": config["reranker_model"]
        },
        "results_by_mode": report_by_mode,
        "query_details": query_details
    }

    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = reports_dir / f"evaluation_report_{timestamp_str}.json"
    latest_file = reports_dir / "evaluation_report_latest.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_json, f, ensure_ascii=False, indent=2)

    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(report_json, f, ensure_ascii=False, indent=2)

    return report_json


# ---------------------------------------------------------------------------
# CLI EVALUATOR
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Advanced RAG Evaluator - Buổi 08")
    parser.add_argument("--strategy", type=str, default="hierarchical", choices=["fixed-size", "semantic", "hierarchical"], help="Chiến lược phân đoạn")
    parser.add_argument("--k", type=int, default=5, help="Giá trị K cho Recall@K, MRR@K, nDCG@K")
    parser.add_argument("--questions", type=str, default=str(BASE_DIR / "eval" / "questions.json"), help="Đường dẫn file JSON chứa câu hỏi benchmark")

    args = parser.parse_args()

    q_path = Path(args.questions)
    print(f"📊 [EVALUATOR] Khởi chạy đánh giá benchmark cho strategy '{args.strategy}' với K={args.k}...")
    print(f"📌 File câu hỏi: '{q_path}'")

    res_report = evaluate_dataset(questions_path=q_path, strategy=args.strategy, top_k=args.k)

    print("\n=================== BÁO CÁO ĐÁNH GIÁ ADVANCED RAG ===================")
    print(f"Timestamp: {res_report['timestamp']}")
    print(f"Strategy: {res_report['strategy']} | K = {res_report['k']}")
    print(f"Embedding Model: {res_report['model_identity']['embedding_model']}")
    print(f"Reranker Model: {res_report['model_identity']['reranker_model']}")
    print("-------------------------------------------------------------------")
    print(f"⚠️ Warning: {res_report['needs_human_review_warning']['message']}")
    print(f"🏆 Tuyên bố chiến thắng chính thức: {res_report['official_winner_declared']}")
    print("===================================================================")

    print(f"\n{'Mode':<15} | {'Recall@K':<10} | {'MRR@K':<10} | {'nDCG@K':<10} | {'Mean Latency':<12} | {'P50 Latency':<12}")
    print("-" * 80)
    for m, m_data in res_report["results_by_mode"].items():
        print(
            f"{m:<15} | {m_data['recall_at_k']:<10.4f} | {m_data['mrr_at_k']:<10.4f} | {m_data['ndcg_at_k']:<10.4f} | "
            f"{m_data['latency_mean_ms']:<10.2f}ms | {m_data['latency_p50_ms']:<10.2f}ms"
        )
