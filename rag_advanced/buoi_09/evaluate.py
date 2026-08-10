"""
Evaluator - Buổi 09
Đánh giá chất lượng RAG phân cấp (Recall@K, Parent Recall@K, MRR@K, nDCG@K) cho các chế độ.
Lưu báo cáo vào reports/latest_report.json và reports/eval_report_<timestamp>.json.
"""
import os
import sys
import json
import time
import math
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from hierarchical_rag import query_hierarchical_rag, load_hierarchical_config

def check_gemini_api_available() -> bool:
    """Kiểm tra xem Gemini API và kết nối mạng có sẵn sàng không."""
    from rag import load_config, _get_genai_client, generate_single_query_embedding
    try:
        config = load_config()
        if not config.get("has_api_key"):
            return False
        client = _get_genai_client(config["api_key"])
        generate_single_query_embedding(
            client=client,
            question="test connection",
            model_name=config["embedding_model"],
            dimension=config["embedding_dim"]
        )
        return True
    except Exception:
        return False

def evaluate_hierarchical_rag(strategy: str = "hierarchical", k: int = 3) -> dict:
    """
    Chạy benchmark offline cho các chế độ: single_flat, multi_flat, single_parent, multi_parent.
    Được cấu trúc để chạy retrieval-only (không sinh LLM answer) giúp tối ưu hóa token.
    Nếu dịch vụ Gemini/mạng không khả dụng hoặc lỗi giữa chừng, ghi nhận trạng thái NOT RUN.
    """
    # 1. Load questions
    q_path = BASE_DIR / "eval" / "questions.json"
    if not q_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file câu hỏi: {q_path}")
        
    with open(q_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    has_human_review = any(q.get("needs_human_review", False) for q in questions)
    
    # Load children registry to resolve parent IDs for evaluation
    children_file = BASE_DIR / "storage" / "hierarchy" / "children.json"
    children_registry = {}
    if children_file.exists():
        with open(children_file, "r", encoding="utf-8") as f:
            children_list = json.load(f)
        children_registry = {c["child_id"]: c for c in children_list}
        
    config = load_hierarchical_config()
    
    # Calculate corpus size and build details
    manifest_file = BASE_DIR / "storage" / "hierarchy" / "manifest.json"
    manifest_data = {}
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    file_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_report_path = reports_dir / f"eval_report_{file_ts}.json"
    latest_report_path = reports_dir / "latest_report.json"
    
    # Atomic helper
    def write_atomic(filepath, data):
        tmp_file = filepath.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if filepath.exists():
            os.remove(filepath)
        os.rename(tmp_file, filepath)
        
    # Helper to write NOT RUN report
    def write_not_run_report(error_msg: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_payload = {
            "timestamp": timestamp,
            "status": "NOT RUN",
            "error": error_msg,
            "config_identity": {
                "strategy": strategy,
                "k": k,
                "embedding_model": config["embedding_model"],
                "generation_model": config["generation_model"],
                "reranker_model": config["reranker_model"]
            },
            "corpus_identity": {
                "child_count": manifest_data.get("counts", {}).get("child_chunks", 318),
                "parent_count": manifest_data.get("counts", {}).get("parent_documents", 21)
            },
            "per_question_results": [],
            "aggregate_metrics": {},
            "human_review_warning": has_human_review
        }
        write_atomic(ts_report_path, report_payload)
        write_atomic(latest_report_path, report_payload)
        return report_payload

    # 2. Check API/Service Availability
    if not check_gemini_api_available():
        print("⚠️ API/Model service is not available. Skipping real evaluation (NOT RUN).")
        return write_not_run_report("Lỗi kết nối API hoặc thiếu API Key (getaddrinfo failed / unauthenticated)")

    modes = ["single_flat", "multi_flat", "single_parent", "multi_parent"]
    
    # Fake generator for retrieval-only evaluation
    import re
    fake_generator = lambda prompt: " ".join(f"[{t}]" for t in re.findall(r"\[(P\d+|E\d+)\]", prompt))
    
    results = {}
    per_question_results = []
    
    try:
        for m in modes:
            recalls = []
            parent_recalls = []
            mrrs = []
            ndcgs = []
            latencies = []
            chars = []
            exp_factors = []
            unique_parents_retrieved = set()
            unique_sources_retrieved = set()
            total_queries_run = 0
            total_child_union_count = 0
            
            mode_calls_generation = 0
            mode_calls_embedding = 0
            
            for q in questions:
                qid = q.get("question_id") or q.get("query_id")
                qtext = q["question"]
                gold_child_ids = q.get("relevant_child_ids") or q.get("relevant_chunk_ids") or []
                gold_parent_ids = q.get("relevant_parent_ids") or []
                
                # If gold_parent_ids is empty, try to resolve from children registry
                if not gold_parent_ids and children_registry:
                    for cid in gold_child_ids:
                        if cid in children_registry:
                            pid = children_registry[cid].get("parent_id")
                            if pid:
                                gold_parent_ids.append(pid)
                    gold_parent_ids = sorted(list(set(gold_parent_ids)))
                    
                t0 = time.perf_counter()
                res = query_hierarchical_rag(
                    qtext,
                    mode=m,
                    custom_generator=fake_generator
                )
                latency = (time.perf_counter() - t0) * 1000
                latencies.append(latency)
                
                trace = res.get("trace", {})
                api_calls = trace.get("api_calls", {})
                
                mode_calls_generation += api_calls.get("gemini_generation", 0)
                mode_calls_embedding += api_calls.get("gemini_embedding", 0)
                
                accepted_evidence = res.get("accepted_evidence", [])
                for e in accepted_evidence:
                    if e.get("source"):
                        unique_sources_retrieved.add(e.get("source"))
                    if "parent" in m and e.get("parent_id"):
                        unique_parents_retrieved.add(e.get("parent_id"))
                    elif "flat" in m:
                        cid = e.get("child_id") or e.get("chunk_id")
                        if cid in children_registry:
                            pid = children_registry[cid].get("parent_id")
                            if pid:
                                unique_parents_retrieved.add(pid)
                                
                if "parent" in m:
                    child_trace = trace.get("child_retrieval_trace", {}) or trace
                    queries_count = child_trace.get("query_count", {}).get("executed", 1)
                    union_count = child_trace.get("union_child_count", len(res.get("child_hits", [])))
                else:
                    queries_count = trace.get("query_count", {}).get("executed", 1) if "multi" in m else 1
                    union_count = len(res.get("child_hits", [])) or len(accepted_evidence)
                    
                total_queries_run += queries_count
                total_child_union_count += union_count
                
                retrieved_child_ids = []
                ret_parents = []
                
                is_parent = "parent" in m
                if is_parent:
                    parents_list = res.get("parent_candidates", [])
                    top_parents = parents_list[:k]
                    ret_parents = [p["parent_id"] for p in top_parents]
                    
                    cids = []
                    for p in top_parents:
                        cids.extend(p.get("supporting_child_ids", []))
                    seen = set()
                    for c in cids:
                        if c not in seen:
                            seen.add(c)
                            retrieved_child_ids.append(c)
                else:
                    child_list = res.get("child_hits", [])
                    top_children = child_list[:k]
                    retrieved_child_ids = [c.get("child_id") or c.get("chunk_id") for c in top_children]
                    
                # A. Child Recall
                gold_child_set = set(gold_child_ids)
                ret_child_set = set(retrieved_child_ids)
                child_intersection = gold_child_set.intersection(ret_child_set)
                child_recall = len(child_intersection) / len(gold_child_set) if gold_child_set else 0.0
                recalls.append(child_recall)
                
                # B. Parent Recall
                gold_parent_set = set(gold_parent_ids)
                ret_parent_set = set(ret_parents) if is_parent else set(unique_parents_retrieved)
                parent_intersection = gold_parent_set.intersection(ret_parent_set)
                parent_recall = len(parent_intersection) / len(gold_parent_set) if gold_parent_set else 0.0
                parent_recalls.append(parent_recall)
                
                # C. MRR@K
                mrr = 0.0
                for rank_idx, cid in enumerate(retrieved_child_ids, 1):
                    if cid in gold_child_set:
                        mrr = 1.0 / rank_idx
                        break
                mrrs.append(mrr)
                
                # D. nDCG@K
                dcg = 0.0
                for rank_idx, cid in enumerate(retrieved_child_ids[:k], 1):
                    if cid in gold_child_set:
                        dcg += 1.0 / math.log2(rank_idx + 1)
                idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(k, len(gold_child_set)) + 1))
                ndcg = dcg / idcg if idcg > 0 else 0.0
                ndcgs.append(ndcg)
                
                # Chars size
                total_char = sum(len(e.get("text", "")) for e in accepted_evidence)
                chars.append(total_char)
                
                # Expansion factor calculation
                if is_parent:
                    child_chars_sum = sum(len(ch.get("text", "")) for ch in res.get("child_hits", []))
                    exp_factor = round(total_char / child_chars_sum, 2) if child_chars_sum > 0 else 1.0
                else:
                    exp_factor = 1.0
                exp_factors.append(exp_factor)
                
                per_question_results.append({
                    "question_id": qid,
                    "question": qtext,
                    "mode": m,
                    "child_recall": round(child_recall, 4),
                    "parent_recall": round(parent_recall, 4),
                    "mrr": round(mrr, 4),
                    "ndcg": round(ndcg, 4),
                    "latency_ms": round(latency, 2),
                    "context_chars": total_char,
                    "expansion_factor": exp_factor
                })
                
            results[m] = {
                "Child Recall@K": round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
                "Parent Recall@K": round(sum(parent_recalls) / len(parent_recalls), 4) if parent_recalls else 0.0,
                "MRR@K": round(sum(mrrs) / len(mrrs), 4) if mrrs else 0.0,
                "nDCG@K": round(sum(ndcgs) / len(ndcgs), 4) if ndcgs else 0.0,
                "Unique Relevant Parents Retrieved": len(unique_parents_retrieved),
                "Unique Relevant Sources Retrieved": len(unique_sources_retrieved),
                "Total Queries Run": total_queries_run,
                "Total Child Union Count": total_child_union_count,
                "Mean Latency (ms)": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
                "P50 Latency (ms)": round(sorted(latencies)[len(latencies)//2], 2) if latencies else 0.0,
                "Mean Context Chars": int(sum(chars) / len(chars)) if chars else 0,
                "Mean Expansion Factor": round(sum(exp_factors) / len(exp_factors), 2) if exp_factors else 1.0,
                "Embedding Call Count": mode_calls_embedding,
                "Generation Call Count": mode_calls_generation
            }
            
    except Exception as e:
        err_msg = f"Lỗi xảy ra trong quá trình đánh giá: {str(e)}"
        print(f"⚠️ {err_msg}")
        return write_not_run_report(err_msg)
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_payload = {
        "timestamp": timestamp,
        "status": "SUCCESS",
        "config_identity": {
            "strategy": strategy,
            "k": k,
            "embedding_model": config["embedding_model"],
            "generation_model": config["generation_model"],
            "reranker_model": config["reranker_model"]
        },
        "corpus_identity": {
            "child_count": manifest_data.get("counts", {}).get("child_chunks", 318),
            "parent_count": manifest_data.get("counts", {}).get("parent_documents", 21)
        },
        "per_question_results": per_question_results,
        "aggregate_metrics": results,
        "human_review_warning": has_human_review
    }
    
    write_atomic(ts_report_path, report_payload)
    write_atomic(latest_report_path, report_payload)
    
    return report_payload

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluator CLI - Buổi 09")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    
    print(f"🚀 Starting offline evaluation with K={args.k}...")
    try:
        rep = evaluate_hierarchical_rag(k=args.k)
        if rep.get("status") == "NOT RUN":
            print(f"⚠️ Evaluation NOT RUN: {rep['error']}")
        else:
            print("✅ Evaluation complete!")
            print(f"Timestamp: {rep['timestamp']}")
            print(f"Report saved to reports/latest_report.json")
    except Exception as e:
        print(f"❌ Error during evaluation: {str(e)}")
        sys.exit(1)
