"""
Module Hierarchical RAG - Buổi 09
Triển khai config, Hierarchy Resolution, Parent-Child Registry, Parent Store, CLI và Unit Tests.
"""

import os
import sys
import json
import re
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Import baseline loaders from Buổi 08 snapshot
from rag import load_chunks

# ---------------------------------------------------------------------------
# 1. HIERARCHICAL CONFIGURATION LOADER & VALIDATOR
# ---------------------------------------------------------------------------

def load_hierarchical_config(env_file_path: Optional[Path] = None) -> dict:
    """
    Nạp và xác thực nghiêm ngặt toàn bộ tham số cấu hình cho Hierarchical RAG.
    Sử dụng Path(__file__).resolve() để độc lập hoàn toàn với CWD.
    """
    target_env = env_file_path if env_file_path else BASE_DIR / ".env"
    if target_env.exists():
        load_dotenv(dotenv_path=target_env, override=True)
    else:
        load_dotenv(override=True)

    # 1. Multi-Query Count & Temperature Validation
    try:
        mq_count = int(os.getenv("MULTI_QUERY_COUNT", "3"))
        if not (1 <= mq_count <= 5):
            raise ValueError()
    except Exception:
        raise ValueError(f"MULTI_QUERY_COUNT ({os.getenv('MULTI_QUERY_COUNT')}) phải là số nguyên từ 1 đến 5.")

    try:
        mq_max_chars = int(os.getenv("MULTI_QUERY_MAX_CHARS", "300"))
        if not (50 <= mq_max_chars <= 1000):
            raise ValueError()
    except Exception:
        raise ValueError(f"MULTI_QUERY_MAX_CHARS ({os.getenv('MULTI_QUERY_MAX_CHARS')}) phải là số nguyên từ 50 đến 1000.")

    try:
        temp = float(os.getenv("MULTI_QUERY_TEMPERATURE", "0.2"))
        if not (0.0 <= temp <= 1.0):
            raise ValueError()
    except Exception:
        raise ValueError(f"MULTI_QUERY_TEMPERATURE ({os.getenv('MULTI_QUERY_TEMPERATURE')}) phải là số thực từ 0.0 đến 1.0.")

    # RRF Weights Validation
    try:
        w_orig = float(os.getenv("MULTI_QUERY_ORIGINAL_WEIGHT", "1.5"))
        w_var = float(os.getenv("MULTI_QUERY_VARIANT_WEIGHT", "1.0"))
        if w_orig < 0.0 or w_var < 0.0:
            raise ValueError()
        if w_orig == 0.0 and w_var == 0.0:
            raise ValueError()
    except Exception:
        raise ValueError("Trọng số MULTI_QUERY_ORIGINAL_WEIGHT và MULTI_QUERY_VARIANT_WEIGHT phải là số thực không âm và không đồng thời bằng 0.")

    # RRF K Validation
    try:
        mq_rrf_k = int(os.getenv("MULTI_QUERY_RRF_K", "60"))
        parent_rrf_k = int(os.getenv("PARENT_RRF_K", "60"))
        if mq_rrf_k <= 0 or parent_rrf_k <= 0:
            raise ValueError()
    except Exception:
        raise ValueError("MULTI_QUERY_RRF_K và PARENT_RRF_K phải là số nguyên dương > 0.")

    # Candidate limits
    try:
        bm25_cand = int(os.getenv("BM25_CANDIDATES", "20"))
        sem_cand = int(os.getenv("SEMANTIC_CANDIDATES", "20"))
        rr_cand = int(os.getenv("RERANK_CANDIDATES", "20"))
        per_q_cand = int(os.getenv("PER_QUERY_CANDIDATES", "12"))
        parent_cand = int(os.getenv("PARENT_CANDIDATES", "10"))
        final_parent_k = int(os.getenv("FINAL_PARENT_TOP_K", "3"))
    except Exception:
        raise ValueError("Các giá trị candidate count phải là số nguyên.")

    for name, val in [
        ("BM25_CANDIDATES", bm25_cand),
        ("SEMANTIC_CANDIDATES", sem_cand),
        ("RERANK_CANDIDATES", rr_cand),
        ("PER_QUERY_CANDIDATES", per_q_cand),
        ("PARENT_CANDIDATES", parent_cand),
        ("FINAL_PARENT_TOP_K", final_parent_k)
    ]:
        if val <= 0 or val > 100:
            raise ValueError(f"Cấu hình '{name}' ({val}) phải là số nguyên dương trong khoảng (0, 100].")

    if final_parent_k > parent_cand:
        raise ValueError(f"FINAL_PARENT_TOP_K ({final_parent_k}) không được vượt quá PARENT_CANDIDATES ({parent_cand}).")

    # Parent configuration validation
    try:
        parent_max_chars = int(os.getenv("PARENT_MAX_CHARS", "6000"))
        if not (1000 <= parent_max_chars <= 20000):
            raise ValueError()
    except Exception:
        raise ValueError(f"PARENT_MAX_CHARS ({os.getenv('PARENT_MAX_CHARS')}) phải là số nguyên từ 1000 đến 20000.")

    try:
        parent_score_limit = int(os.getenv("PARENT_SCORE_CHILD_LIMIT", "3"))
        if not (1 <= parent_score_limit <= 20):
            raise ValueError()
    except Exception:
        raise ValueError(f"PARENT_SCORE_CHILD_LIMIT ({os.getenv('PARENT_SCORE_CHILD_LIMIT')}) phải là số nguyên từ 1 đến 20.")

    try:
        total_context_max = int(os.getenv("TOTAL_CONTEXT_MAX_CHARS", "16000"))
    except Exception:
        raise ValueError("TOTAL_CONTEXT_MAX_CHARS phải là số nguyên.")

    if total_context_max < parent_max_chars:
        raise ValueError(f"TOTAL_CONTEXT_MAX_CHARS ({total_context_max}) không được nhỏ hơn PARENT_MAX_CHARS ({parent_max_chars}).")

    try:
        rerank_min_score = float(os.getenv("RERANK_MIN_SCORE", "0.5"))
    except Exception:
        raise ValueError("RERANK_MIN_SCORE phải là số thực.")

    try:
        final_top_k = int(os.getenv("FINAL_TOP_K", "3"))
    except Exception:
        raise ValueError("FINAL_TOP_K phải là số nguyên.")

    # Model identity check
    emb_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2").strip()
    gen_model = os.getenv("GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite").strip()
    reranker_model = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3").strip()

    if not emb_model or not gen_model or not reranker_model:
        raise ValueError("Tên mô hình embedding, generation hoặc reranker không được phép để rỗng.")

    return {
        "multi_query_count": mq_count,
        "multi_query_max_chars": mq_max_chars,
        "temperature": temp,
        "multi_query_original_weight": w_orig,
        "multi_query_variant_weight": w_var,
        "multi_query_rrf_k": mq_rrf_k,
        "parent_rrf_k": parent_rrf_k,
        "bm25_candidates": bm25_cand,
        "semantic_candidates": sem_cand,
        "rerank_candidates": rr_cand,
        "per_query_candidates": per_q_cand,
        "parent_candidates": parent_cand,
        "final_parent_top_k": final_parent_k,
        "parent_max_chars": parent_max_chars,
        "parent_score_child_limit": parent_score_limit,
        "total_context_max_chars": total_context_max,
        "embedding_model": emb_model,
        "generation_model": gen_model,
        "reranker_model": reranker_model,
        "rerank_min_score": rerank_min_score,
        "final_top_k": final_top_k,
        "strategy": os.getenv("STRATEGY", "hierarchical").strip()
    }

# ---------------------------------------------------------------------------
# 1.5 MULTI-QUERY GENERATOR
# ---------------------------------------------------------------------------

_QUERY_SET_CACHE = {}

def normalize_query_text(text: str) -> str:
    import unicodedata
    normalized = unicodedata.normalize("NFC", text).casefold().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[.,\/#!$%\^&\*;:{}=\-_`~()?\"]", "", normalized)
    return normalized

def generate_query_variants(
    question: str,
    query_generator_fn: Optional[Any] = None
) -> dict:
    import unicodedata
    # 1. Load config
    config = load_hierarchical_config()
    num_variants = config["multi_query_count"]
    max_chars = config["multi_query_max_chars"]
    temperature = config["temperature"]
    model_name = config["generation_model"]
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # 2. NFC normalize and trim Q0
    q0_text = unicodedata.normalize("NFC", question).strip()
    if not q0_text:
        raise ValueError("Câu hỏi không được phép rỗng.")
    if len(q0_text) > 1000:
        raise ValueError("Câu hỏi vượt quá độ dài hợp lệ.")

    # 3. Check Cache
    cache_key_seed = f"{q0_text}::count={num_variants}::max={max_chars}::temp={temperature}::model={model_name}"
    cache_key = hashlib.md5(cache_key_seed.encode("utf-8")).hexdigest()

    if cache_key in _QUERY_SET_CACHE:
        cached_payload = dict(_QUERY_SET_CACHE[cache_key])
        # Ensure deep copy of queries list to avoid mutation
        cached_payload["queries"] = [dict(q) for q in cached_payload["queries"]]
        cached_payload["cache_hit"] = True
        return cached_payload

    # 4. Generate
    generated_list = []
    latency = 0.0
    status = "ready"
    error_msg = None

    if query_generator_fn is not None:
        try:
            start_time = time.time()
            gen_res = query_generator_fn(q0_text)
            latency = (time.time() - start_time) * 1000
            if isinstance(gen_res, list):
                generated_list = gen_res
            elif isinstance(gen_res, dict):
                generated_list = gen_res.get("queries", [])
                status = gen_res.get("status", "ready")
                error_msg = gen_res.get("error_detail")
        except Exception as e:
            status = "query_generation_unavailable"
            error_msg = str(e)
    else:
        from google import genai
        from google.genai import types
        from pydantic import BaseModel, Field
        from typing import List

        class QueryVariantItem(BaseModel):
            text: str = Field(description="Nội dung câu hỏi biến thể dùng để tìm kiếm")
            focus: str = Field(description="Mục tiêu tập trung: exact_legal_terms, paraphrase, hoặc missing_aspect")

        class QueryVariantsResponse(BaseModel):
            queries: List[QueryVariantItem]

        try:
            client = genai.Client(api_key=api_key)
            prompt = (
                f"Bạn là một trợ lý AI chuyên về mở rộng câu hỏi (Query Expansion) cho hệ thống tìm kiếm văn bản pháp luật ngân hàng.\n"
                f"Nhiệm vụ: Hãy tạo ra tối đa {num_variants} câu hỏi biến thể (phần câu hỏi mở rộng) bằng tiếng Việt cho câu hỏi gốc bên dưới.\n"
                f"Yêu cầu:\n"
                f"1. KHÔNG TRẢ LỜI câu hỏi.\n"
                f"2. Đa dạng hóa các biến thể theo các khía cạnh:\n"
                f"   - exact_legal_terms: Sử dụng thuật ngữ pháp lý chính xác liên quan.\n"
                f"   - paraphrase: Cách diễn đạt khác tương đương ngữ nghĩa câu hỏi gốc.\n"
                f"   - missing_aspect: Khía cạnh nhỏ hoặc ý phụ có thể bị bỏ sót của câu hỏi.\n"
                f"3. Nếu câu hỏi gốc có số Điều, Khoản, Điểm hoặc số hiệu năm văn bản, bắt buộc ít nhất một biến thể phải giữ nguyên tham chiếu đó.\n"
                f"4. TUYỆT ĐỐI KHÔNG tự bịa ra số hiệu Điều/Khoản mới không xuất hiện trong câu hỏi gốc.\n"
                f"5. Mỗi biến thể không được vượt quá {max_chars} ký tự.\n\n"
                f"Câu hỏi gốc: \"{q0_text}\"\n"
            )
            
            start_time = time.time()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QueryVariantsResponse,
                    temperature=temperature
                )
            )
            latency = (time.time() - start_time) * 1000
            
            resp_json = json.loads(response.text)
            generated_list = resp_json.get("queries", [])
        except Exception as e:
            status = "query_generation_unavailable"
            error_msg = str(e)

    # If generation failed, return fallback status with Q0 only
    if status == "query_generation_unavailable":
        return {
            "original_question": q0_text,
            "queries": [
                {
                    "query_id": "Q0",
                    "text": q0_text,
                    "origin": "original",
                    "focus": "original_intent"
                }
            ],
            "model": model_name,
            "generation_latency_ms": 0.0,
            "status": "query_generation_unavailable",
            "error_detail": error_msg,
            "cache_hit": False
        }

    # 5. Validation and filtering
    seen_norms = set()
    q0_norm = normalize_query_text(q0_text)
    seen_norms.add(q0_norm)

    valid_queries = [
        {
            "query_id": "Q0",
            "text": q0_text,
            "origin": "original",
            "focus": "original_intent"
        }
    ]

    dropped_duplicate_count = 0
    orig_dieu = set(re.findall(r"điều\s+(\d+)", q0_text, re.IGNORECASE))
    orig_khoan = set(re.findall(r"khoản\s+(\d+)", q0_text, re.IGNORECASE))

    for item in generated_list:
        text_val = item.get("text", "").strip()
        text_val = unicodedata.normalize("NFC", text_val)
        focus_val = item.get("focus", "").strip()

        if not text_val:
            continue
        if len(text_val) > max_chars:
            continue

        # Rule-based validation: no invented Điều/Khoản
        var_dieu = set(re.findall(r"điều\s+(\d+)", text_val, re.IGNORECASE))
        var_khoan = set(re.findall(r"khoản\s+(\d+)", text_val, re.IGNORECASE))
        if not var_dieu.issubset(orig_dieu) or not var_khoan.issubset(orig_khoan):
            # Drop if invented
            continue

        # Deduplication check
        norm_val = normalize_query_text(text_val)
        if norm_val in seen_norms:
            dropped_duplicate_count += 1
            continue
        seen_norms.add(norm_val)

        valid_queries.append({
            "query_id": None,
            "text": text_val,
            "origin": "generated",
            "focus": focus_val
        })

    # Slice to maximum allowed count (Q0 + num_variants)
    valid_queries = valid_queries[:num_variants + 1]

    # Assign deterministic IDs
    for idx, q in enumerate(valid_queries):
        q["query_id"] = f"Q{idx}"

    payload = {
        "original_question": q0_text,
        "queries": valid_queries,
        "model": model_name,
        "generation_latency_ms": latency,
        "status": "ready",
        "cache_hit": False
    }
    if dropped_duplicate_count > 0:
        payload["dropped_duplicate_count"] = dropped_duplicate_count

    # Cache it
    _QUERY_SET_CACHE[cache_key] = payload
    return payload

def retrieve_multi_query_hybrid(
    question: str,
    custom_query_generator: Optional[Any] = None,
    custom_bm25_retriever: Optional[Any] = None,
    custom_semantic_retriever: Optional[Any] = None,
    chunks: Optional[List[dict]] = None,
    chroma_dir: Optional[Path] = None
) -> dict:
    import time
    from advanced_rag import search_hybrid

    # 1. Load config
    config = load_hierarchical_config()
    mq_rrf_k = config["multi_query_rrf_k"]
    w_orig = config["multi_query_original_weight"]
    w_var = config["multi_query_variant_weight"]
    per_query_candidates = config["per_query_candidates"]

    t_start = time.perf_counter()

    # 2. Query expansion
    expansion_call_count = 0
    t0_exp = time.perf_counter()
    
    if custom_query_generator is not None:
        expansion_res = generate_query_variants(question, query_generator_fn=custom_query_generator)
    else:
        expansion_res = generate_query_variants(question)
        if not expansion_res.get("cache_hit", False) and expansion_res.get("status") == "ready":
            expansion_call_count = 1
            
    t1_exp = time.perf_counter()
    exp_latency = (t1_exp - t0_exp) * 1000

    q_list = expansion_res["queries"]
    status = "ready"
    
    if expansion_res.get("status") == "query_generation_unavailable":
        status = "multi_query_partial"

    # 3. Retrieve per query
    query_results = {}
    query_latencies = {}
    
    query_count_req = len(q_list)
    query_count_val = len(q_list)
    query_count_exec = 0
    query_count_failed = 0
    failed_queries_errors = {}
    
    embedding_call_count = 0

    for q in q_list:
        qid = q["query_id"]
        qtext = q["text"]
        
        try:
            res = search_hybrid(
                question=qtext,
                strategy="hierarchical",
                chunks=chunks,
                chroma_dir=chroma_dir,
                custom_bm25_retriever=custom_bm25_retriever,
                custom_semantic_retriever=custom_semantic_retriever
            )
            query_count_exec += 1
            query_results[qid] = res["results"][:per_query_candidates]
            
            if custom_semantic_retriever is None:
                embedding_call_count += 1
                
            query_latencies[qid] = res["trace"]["latency_ms"]["total_ms"]
        except Exception as e:
            query_count_failed += 1
            if qid == "Q0":
                raise ValueError(f"Lỗi nghiêm trọng khi truy xuất Q0: {str(e)}")
            else:
                failed_queries_errors[qid] = str(e)
                status = "partial"
                
    if query_count_failed > 0 and query_count_failed == len(q_list) - 1:
        status = "multi_query_partial"

    # 4. Cross-Query RRF Merge
    t0_fus = time.perf_counter()
    
    child_hits = {}
    
    for qid, results in query_results.items():
        weight = w_orig if qid == "Q0" else w_var
        
        for rank_0, hit in enumerate(results):
            cid = hit["chunk_id"]
            rank_val = rank_0 + 1
            
            if cid not in child_hits:
                child_hits[cid] = {
                    "child_id": cid,
                    "text": hit["text"],
                    "source": hit["source"],
                    "page_start": hit["page_start"],
                    "page_end": hit["page_end"],
                    "support_query_count": 0,
                    "support_query_ids": [],
                    "per_query_ranks": {},
                    "per_query_trace": {},
                    "multi_query_rrf_score": 0.0
                }
            else:
                for field in ["text", "source", "page_start", "page_end"]:
                    if child_hits[cid][field] != hit[field]:
                        raise ValueError(
                            f"Metadata mismatch cho child_id '{cid}' giữa các query! Field '{field}': '{child_hits[cid][field]}' vs '{hit[field]}'."
                        )
            
            rrf_contrib = weight / (mq_rrf_k + rank_val)
            child_hits[cid]["multi_query_rrf_score"] += rrf_contrib
            child_hits[cid]["support_query_count"] += 1
            child_hits[cid]["support_query_ids"].append(qid)
            child_hits[cid]["per_query_ranks"][qid] = rank_val
            child_hits[cid]["per_query_trace"][qid] = {
                "bm25_rank": hit.get("bm25_rank"),
                "bm25_score": hit.get("bm25_score"),
                "semantic_rank": hit.get("semantic_rank"),
                "semantic_distance": hit.get("semantic_distance"),
                "rrf_score": hit.get("rrf_score")
            }

    for cid, hit in child_hits.items():
        hit["support_query_ids"].sort(key=lambda x: int(x[1:]))
        hit["best_query_rank"] = min(hit["per_query_ranks"].values())
        hit["multi_query_rrf_score"] = round(hit["multi_query_rrf_score"], 6)

    sorted_hits = sorted(
        child_hits.values(),
        key=lambda x: (
            -x["multi_query_rrf_score"],
            -x["support_query_count"],
            x["best_query_rank"],
            x["child_id"]
        )
    )

    for rank_1, hit in enumerate(sorted_hits, 1):
        hit["multi_query_rank"] = rank_1

    t1_fus = time.perf_counter()
    fus_latency = (t1_fus - t0_fus) * 1000
    t_end = time.perf_counter()
    total_latency = (t_end - t_start) * 1000

    overlap_dist = {}
    for hit in sorted_hits:
        cnt = hit["support_query_count"]
        overlap_dist[cnt] = overlap_dist.get(cnt, 0) + 1

    trace = {
        "query_count": {
            "requested": query_count_req,
            "valid": query_count_val,
            "executed": query_count_exec,
            "failed": query_count_failed
        },
        "failed_queries": failed_queries_errors,
        "generated_query_latency_ms": round(exp_latency, 2),
        "retrieval_latency_ms": {qid: round(lat, 2) for qid, lat in query_latencies.items()},
        "result_count": {qid: len(res) for qid, res in query_results.items()},
        "union_child_count": len(sorted_hits),
        "overlap_distribution": overlap_dist,
        "fusion_latency_ms": round(fus_latency, 2),
        "total_latency_ms": round(total_latency, 2),
        "expansion_call_count": expansion_call_count,
        "semantic_embedding_call_count": embedding_call_count
    }

    return {
        "status": status,
        "results": sorted_hits,
        "trace": trace
    }

def validate_hierarchy_registry() -> Tuple[bool, str, Optional[dict]]:
    """
    Xác thực Registry trên đĩa.
    Kiểm tra sự tồn tại của 3 file và dấu vân tay input_file_fingerprints.
    """
    config = load_hierarchical_config()
    target_storage = BASE_DIR / "storage" / "hierarchy"
    manifest_file = target_storage / "manifest.json"
    children_file = target_storage / "children.json"
    parents_file = target_storage / "parents.json"

    if not manifest_file.exists() or not children_file.exists() or not parents_file.exists():
        return False, "Thiếu file registry trên đĩa.", None

    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        return False, "Không thể đọc manifest.json.", None

    if manifest.get("strategy") != "hierarchical":
        return False, f"Strategy mismatch: Manifest='{manifest.get('strategy')}' vs Cần='hierarchical'.", None

    conf_ident = manifest.get("config_identity", {})
    if conf_ident.get("parent_max_chars") != config["parent_max_chars"]:
        return False, f"Config parent_max_chars mismatch: Manifest={conf_ident.get('parent_max_chars')} vs Config={config['parent_max_chars']}.", None

    json_dir = BASE_DIR.parent.parent / "rag_foundation" / "buoi_05" / "output" / "chunks"
    if json_dir.exists():
        for j_file in sorted(list(json_dir.glob("*.json"))):
            real_md5 = compute_file_md5(j_file)
            manifest_md5 = manifest.get("input_file_fingerprints", {}).get(j_file.name)
            if real_md5 != manifest_md5:
                return False, f"Fingerprint mismatch cho file '{j_file.name}': Cũ='{manifest_md5}' vs Mới='{real_md5}'.", None

    return True, "Registry hợp lệ.", manifest

def retrieve_hierarchical_parent(
    question: str,
    mode: str = "multi_parent",
    custom_query_generator: Optional[Any] = None,
    custom_bm25_retriever: Optional[Any] = None,
    custom_semantic_retriever: Optional[Any] = None,
    chunks: Optional[List[dict]] = None,
    chroma_dir: Optional[Path] = None,
    skip_budget: bool = False
) -> dict:
    import time
    
    t_start = time.perf_counter()

    # 1. Validate hierarchy registry precondition
    valid_reg, msg_reg, manifest = validate_hierarchy_registry()
    if not valid_reg:
        return {
            "status": "hierarchy_not_ready",
            "message": msg_reg,
            "results": [],
            "trace": {}
        }

    config = load_hierarchical_config()
    parent_rrf_k = config["parent_rrf_k"]
    parent_score_child_limit = config["parent_score_child_limit"]
    parent_candidates_limit = config["parent_candidates"]
    total_context_max_chars = config["total_context_max_chars"]

    # Load registry database
    target_storage = BASE_DIR / "storage" / "hierarchy"
    with open(target_storage / "children.json", "r", encoding="utf-8") as f:
        children_list = json.load(f)
    with open(target_storage / "parents.json", "r", encoding="utf-8") as f:
        parents_list = json.load(f)

    children_registry = {c["child_id"]: c for c in children_list}
    parents_registry = {p["parent_id"]: p for p in parents_list}

    # 2. Retrieve child hits depending on mode
    if mode == "single_parent":
        def single_query_generator(q):
            return {
                "queries": [
                    {"query_id": "Q0", "text": q, "origin": "original", "focus": "original_intent"}
                ]
            }
        child_res = retrieve_multi_query_hybrid(
            question,
            custom_query_generator=single_query_generator,
            custom_bm25_retriever=custom_bm25_retriever,
            custom_semantic_retriever=custom_semantic_retriever,
            chunks=chunks,
            chroma_dir=chroma_dir
        )
    else:
        child_res = retrieve_multi_query_hybrid(
            question,
            custom_query_generator=custom_query_generator,
            custom_bm25_retriever=custom_bm25_retriever,
            custom_semantic_retriever=custom_semantic_retriever,
            chunks=chunks,
            chroma_dir=chroma_dir
        )

    if child_res.get("status") == "query_generation_unavailable":
        return {
            "status": "query_generation_unavailable",
            "results": [],
            "trace": child_res.get("trace", {})
        }

    child_hits = child_res["results"]
    t0_map = time.perf_counter()

    # 3. Child to Parent Mapping & Aggregation
    parent_groups = {}
    child_to_parent_map = {}
    child_count_per_parent = {}

    for hit in child_hits:
        cid = hit["child_id"]
        if cid not in children_registry:
            raise ValueError(f"Không tìm thấy child_id '{cid}' trong children registry!")
        pid = children_registry[cid]["parent_id"]
        if not pid:
            raise ValueError(f"Child_id '{cid}' không được liên kết với bất kỳ parent_id nào!")

        child_to_parent_map[cid] = pid
        child_count_per_parent[pid] = child_count_per_parent.get(pid, 0) + 1

        if pid not in parent_groups:
            parent_groups[pid] = []
        parent_groups[pid].append(hit)

    parent_candidates = []
    parent_score_components = {}

    for pid, children_group in parent_groups.items():
        if pid not in parents_registry:
            raise ValueError(f"Không tìm thấy parent_id '{pid}' trong parent store!")
        parent_doc = parents_registry[pid]

        # Sort children by multi_query_rank ascending (best rank first)
        children_group.sort(key=lambda x: x["multi_query_rank"])

        anchor_child_id = children_group[0]["child_id"]
        scoring_children = children_group[:parent_score_child_limit]
        scoring_child_ids = [c["child_id"] for c in scoring_children]
        supporting_child_ids = [c["child_id"] for c in children_group]

        # Parent score calculation
        parent_rrf_score = sum(1.0 / (parent_rrf_k + c["multi_query_rank"]) for c in scoring_children)
        parent_score_components[pid] = {
            "scoring_child_ranks": [c["multi_query_rank"] for c in scoring_children],
            "contribs": [round(1.0 / (parent_rrf_k + c["multi_query_rank"]), 6) for c in scoring_children]
        }

        # Unique queries supporting
        support_query_ids = set()
        for c in children_group:
            support_query_ids.update(c["support_query_ids"])
        support_query_ids = sorted(list(support_query_ids), key=lambda x: int(x[1:]))

        best_child_rank = children_group[0]["multi_query_rank"]
        ambiguous = any(children_registry[c["child_id"]]["ambiguous"] for c in children_group)

        # Collect warnings
        p_warnings = list(parent_doc.get("warnings", []))
        for c in children_group:
            p_warnings.extend(children_registry[c["child_id"]].get("warnings", []))
        p_warnings = sorted(list(set(p_warnings)))

        # Structural path from registry
        first_child_reg = children_registry[children_group[0]["child_id"]]
        structural_path = first_child_reg["structural_path"]

        parent_candidates.append({
            "parent_id": pid,
            "source": parent_doc["source"],
            "page_start": parent_doc["page_start"],
            "page_end": parent_doc["page_end"],
            "structural_path": structural_path,
            "text": parent_doc["text"],
            "parent_rrf_score": round(parent_rrf_score, 6),
            "anchor_child_id": anchor_child_id,
            "scoring_child_ids": scoring_child_ids,
            "supporting_child_ids": supporting_child_ids,
            "support_query_ids": support_query_ids,
            "best_child_rank": best_child_rank,
            "ambiguous": ambiguous,
            "warnings": p_warnings
        })

    # Sort parent candidates
    sorted_parents = sorted(
        parent_candidates,
        key=lambda x: (
            -x["parent_rrf_score"],
            -len(x["support_query_ids"]),
            x["best_child_rank"],
            x["parent_id"]
        )
    )

    for rank_1, p in enumerate(sorted_parents, 1):
        p["parent_rank"] = rank_1

    # 4. Candidate limit and Context budget
    candidates_pre_budget = sorted_parents[:parent_candidates_limit]
    dropped_by_candidate_limit = sorted_parents[parent_candidates_limit:]

    accepted_parents = []
    parents_dropped = []
    current_chars = 0

    for dp in dropped_by_candidate_limit:
        parents_dropped.append({
            "parent_id": dp["parent_id"],
            "reason": "candidate_limit"
        })

    if skip_budget:
        accepted_parents = candidates_pre_budget
    else:
        for idx, p in enumerate(candidates_pre_budget):
            p_len = len(p["text"])
            if current_chars + p_len > total_context_max_chars:
                if idx == 0:
                    p["warnings"].append("first_parent_oversized_context_limit")
                    accepted_parents.append(p)
                    current_chars += p_len
                else:
                    parents_dropped.append({
                        "parent_id": p["parent_id"],
                        "reason": "context_budget"
                    })
            else:
                accepted_parents.append(p)
                current_chars += p_len

    t1_map = time.perf_counter()
    map_latency = (t1_map - t0_map) * 1000
    t_end = time.perf_counter()
    total_latency = (t_end - t_start) * 1000

    # Chars counts & stats
    child_chars = sum(len(c["text"]) for c in child_hits)
    expanded_parent_chars = sum(len(p["text"]) for p in accepted_parents)
    expansion_factor = round(expanded_parent_chars / child_chars, 2) if child_chars > 0 else 0.0

    amb_count = sum(1 for p in accepted_parents if p["ambiguous"])
    warn_count = sum(len(p["warnings"]) for p in accepted_parents)

    trace = {
        "input_child_hit_count": len(child_hits),
        "unique_parent_count": len(sorted_parents),
        "child_count_per_parent": child_count_per_parent,
        "child_to_parent_mapping": child_to_parent_map,
        "parent_score_components": parent_score_components,
        "parents_dropped": parents_dropped,
        "child_chars": child_chars,
        "expanded_parent_chars": expanded_parent_chars,
        "context_expansion_factor": expansion_factor,
        "ambiguous_count": amb_count,
        "warning_count": warn_count,
        "latency_ms": {
            "mapping_and_aggregation_ms": round(map_latency, 2),
            "total_ms": round(total_latency, 2)
        },
        "child_retrieval_trace": child_res.get("trace", {})
    }

    status = child_res.get("status", "ready")
    
    return {
        "status": status,
        "results": accepted_parents,
        "trace": trace
    }

_RERANKER_SINGLETON = None

def get_reranker_instance() -> Any:
    global _RERANKER_SINGLETON
    if _RERANKER_SINGLETON is None:
        from advanced_rag import CrossEncoderReranker
        config = load_hierarchical_config()
        device_setting = os.getenv("RERANK_DEVICE", "auto")
        max_length = int(os.getenv("RERANKER_MAX_LENGTH", "512"))
        _RERANKER_SINGLETON = CrossEncoderReranker(
            model_name=config["reranker_model"],
            device_setting=device_setting,
            max_length=max_length,
            cache_dir=BASE_DIR / "storage" / "huggingface"
        )
    return _RERANKER_SINGLETON

def query_hierarchical_rag(
    question: str,
    mode: str = "multi_parent",
    custom_query_generator: Optional[Any] = None,
    custom_bm25_retriever: Optional[Any] = None,
    custom_semantic_retriever: Optional[Any] = None,
    custom_reranker: Optional[Any] = None,
    custom_generator: Optional[Any] = None,
    chunks: Optional[List[dict]] = None,
    chroma_dir: Optional[Path] = None
) -> dict:
    import time
    import math
    import os
    import re
    from google import genai
    from advanced_rag import search_hybrid_rerank, search_hybrid
    
    t_start = time.perf_counter()
    allowed_modes = {"single_flat", "multi_flat", "single_parent", "multi_parent"}
    if mode not in allowed_modes:
        raise ValueError(f"Mode '{mode}' không hợp lệ. Phải thuộc {allowed_modes}")
        
    config = load_hierarchical_config()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    api_generation_calls = 0
    api_embedding_calls = 0
    
    latencies = {
        "expansion_ms": 0.0,
        "retrieval_ms": 0.0,
        "fusion_ms": 0.0,
        "mapping_ms": 0.0,
        "rerank_ms": 0.0,
        "generation_ms": 0.0,
        "total_ms": 0.0
    }
    
    query_set = None
    if mode in {"multi_flat", "multi_parent"}:
        t0_exp = time.perf_counter()
        try:
            if custom_query_generator is not None:
                query_set = custom_query_generator(question)
            else:
                query_set = generate_query_variants(question)
                
            latencies["expansion_ms"] = round((time.perf_counter() - t0_exp) * 1000, 2)
            
            if query_set.get("status") == "ready":
                if not query_set.get("cache_hit", False):
                    api_generation_calls += 1
            
            if query_set.get("status") == "query_generation_unavailable":
                t_end = time.perf_counter()
                latencies["total_ms"] = round((t_end - t_start) * 1000, 2)
                return {
                    "status": "query_generation_unavailable",
                    "mode": mode,
                    "original_question": question,
                    "query_set": query_set,
                    "child_hits": [],
                    "parent_candidates": [],
                    "accepted_evidence": [],
                    "answer": "",
                    "citations": [],
                    "trace": {
                        "stage_latencies": latencies,
                        "api_calls": {
                            "gemini_generation": api_generation_calls,
                            "gemini_embedding": api_embedding_calls
                        },
                        "identities": {
                            "embedding_model": config["embedding_model"],
                            "generation_model": config["generation_model"],
                            "reranker_model": config["reranker_model"]
                        }
                    }
                }
        except Exception as e:
            t_end = time.perf_counter()
            latencies["total_ms"] = round((t_end - t_start) * 1000, 2)
            return {
                "status": "query_generation_unavailable",
                "mode": mode,
                "original_question": question,
                "query_set": {"status": "query_generation_unavailable", "queries": []},
                "child_hits": [],
                "parent_candidates": [],
                "accepted_evidence": [],
                "answer": "",
                "citations": [],
                "trace": {
                    "stage_latencies": latencies,
                    "api_calls": {
                        "gemini_generation": api_generation_calls,
                        "gemini_embedding": api_embedding_calls
                    },
                    "identities": {
                        "embedding_model": config["embedding_model"],
                        "generation_model": config["generation_model"],
                        "reranker_model": config["reranker_model"]
                    }
                }
            }

    child_hits = []
    parent_candidates = []
    accepted_evidence = []
    
    reranker_failed = False
    
    if mode == "single_flat":
        t0_ret = time.perf_counter()
        hybrid_res = search_hybrid(
            question=question,
            strategy=config["strategy"],
            chunks=chunks,
            chroma_dir=chroma_dir,
            custom_bm25_retriever=custom_bm25_retriever,
            custom_semantic_retriever=custom_semantic_retriever
        )
        latencies["retrieval_ms"] = round((time.perf_counter() - t0_ret) * 1000, 2)
        api_embedding_calls += 1
        
        child_hits = hybrid_res["results"]
        limit_candidates_count = min(config["rerank_candidates"], len(child_hits))
        candidates_to_rerank = child_hits[:limit_candidates_count]
        
        t0_rr = time.perf_counter()
        try:
            if custom_reranker is not None:
                scored_children = custom_reranker(question, candidates_to_rerank)
            else:
                reranker = get_reranker_instance()
                scored_children = reranker.compute_scores(question, candidates_to_rerank)
                
            sorted_scored = sorted(
                scored_children,
                key=lambda x: (-x["rerank_score"], x["fused_rank"], str(x["chunk_id"]))
            )
            latencies["rerank_ms"] = round((time.perf_counter() - t0_rr) * 1000, 2)
        except Exception as e:
            reranker_failed = True
            
        if not reranker_failed:
            final_k = min(config["final_top_k"], len(sorted_scored))
            for rank_1, item in enumerate(sorted_scored[:final_k], 1):
                item_copy = dict(item)
                item_copy["rerank_rank"] = rank_1
                item_copy["rank_change"] = item_copy["fused_rank"] - rank_1
                
                accepted = (item_copy["rerank_score"] >= config["rerank_min_score"])
                item_copy["accepted"] = accepted
                if accepted:
                    accepted_evidence.append(item_copy)
                    
    elif mode == "multi_flat":
        t0_ret = time.perf_counter()
        mq_res = retrieve_multi_query_hybrid(
            question=question,
            custom_query_generator=custom_query_generator,
            custom_bm25_retriever=custom_bm25_retriever,
            custom_semantic_retriever=custom_semantic_retriever,
            chunks=chunks,
            chroma_dir=chroma_dir
        )
        latencies["retrieval_ms"] = mq_res["trace"]["retrieval_latency_ms"].get("Q0", 0.0)
        latencies["fusion_ms"] = mq_res["trace"]["fusion_latency_ms"]
        api_embedding_calls += mq_res["trace"]["semantic_embedding_call_count"]
        
        child_hits = mq_res["results"]
        limit_candidates_count = min(config["rerank_candidates"], len(child_hits))
        candidates_to_rerank = child_hits[:limit_candidates_count]
        
        t0_rr = time.perf_counter()
        try:
            if custom_reranker is not None:
                scored_children = custom_reranker(question, candidates_to_rerank)
            else:
                reranker = get_reranker_instance()
                scored_children = reranker.compute_scores(question, candidates_to_rerank)
                
            sorted_scored = sorted(
                scored_children,
                key=lambda x: (-x["rerank_score"], x["multi_query_rank"], str(x["child_id"]))
            )
            latencies["rerank_ms"] = round((time.perf_counter() - t0_rr) * 1000, 2)
        except Exception as e:
            reranker_failed = True
            
        if not reranker_failed:
            final_k = min(config["final_top_k"], len(sorted_scored))
            for rank_1, item in enumerate(sorted_scored[:final_k], 1):
                item_copy = dict(item)
                item_copy["rerank_rank"] = rank_1
                item_copy["rank_change"] = item_copy["multi_query_rank"] - rank_1
                
                accepted = (item_copy["rerank_score"] >= config["rerank_min_score"])
                item_copy["accepted"] = accepted
                if accepted:
                    accepted_evidence.append(item_copy)
                    
    elif mode in {"single_parent", "multi_parent"}:
        t0_ret = time.perf_counter()
        parent_res = retrieve_hierarchical_parent(
            question=question,
            mode="single_parent" if mode == "single_parent" else "multi_parent",
            custom_query_generator=custom_query_generator,
            custom_bm25_retriever=custom_bm25_retriever,
            custom_semantic_retriever=custom_semantic_retriever,
            chunks=chunks,
            chroma_dir=chroma_dir,
            skip_budget=True
        )
        
        if parent_res.get("status") == "hierarchy_not_ready":
            return parent_res
            
        latencies["retrieval_ms"] = parent_res["trace"]["child_retrieval_trace"]["retrieval_latency_ms"].get("Q0", 0.0)
        latencies["fusion_ms"] = parent_res["trace"]["child_retrieval_trace"]["fusion_latency_ms"]
        latencies["mapping_ms"] = parent_res["trace"]["latency_ms"]["mapping_and_aggregation_ms"]
        
        api_embedding_calls += parent_res["trace"]["child_retrieval_trace"]["semantic_embedding_call_count"]
        
        child_hits = parent_res["trace"].get("child_retrieval_trace", {}).get("results", [])
        parent_candidates = parent_res["results"]
        
        t0_rr = time.perf_counter()
        try:
            if custom_reranker is not None:
                scored_parents = custom_reranker(question, parent_candidates)
            else:
                reranker = get_reranker_instance()
                scored_parents = reranker.compute_scores(question, parent_candidates)
                
            sorted_scored = sorted(
                scored_parents,
                key=lambda x: (-x["rerank_score"], x["parent_rank"], x["parent_id"])
            )
            latencies["rerank_ms"] = round((time.perf_counter() - t0_rr) * 1000, 2)
        except Exception as e:
            reranker_failed = True
            
        if not reranker_failed:
            for rank_1, item in enumerate(sorted_scored, 1):
                item["parent_rerank_raw_score"] = item.get("rerank_raw_score")
                item["parent_rerank_score"] = item.get("rerank_score")
                item["parent_rerank_rank"] = rank_1
                item["parent_rank_change"] = item["parent_rank"] - rank_1
                
            current_chars = 0
            total_context_max_chars = config["total_context_max_chars"]
            final_parent_top_k = config["final_parent_top_k"]
            
            accepted_count = 0
            for idx, p in enumerate(sorted_scored):
                accepted = False
                if p["parent_rerank_score"] >= config["rerank_min_score"]:
                    p_len = len(p["text"])
                    if current_chars + p_len <= total_context_max_chars:
                        if accepted_count < final_parent_top_k:
                            accepted = True
                            current_chars += p_len
                            accepted_count += 1
                    else:
                        if idx == 0:
                            p["warnings"].append("first_parent_oversized_context_limit")
                            accepted = True
                            current_chars += p_len
                            accepted_count += 1
                            
                p["accepted"] = accepted
                if accepted:
                    accepted_evidence.append(p)

    if reranker_failed:
        t_end = time.perf_counter()
        latencies["total_ms"] = round((t_end - t_start) * 1000, 2)
        return {
            "status": "reranker_unavailable",
            "mode": mode,
            "original_question": question,
            "query_set": query_set,
            "child_hits": child_hits,
            "parent_candidates": parent_candidates,
            "accepted_evidence": [],
            "answer": "",
            "citations": [],
            "trace": {
                "stage_latencies": latencies,
                "api_calls": {
                    "gemini_generation": api_generation_calls,
                    "gemini_embedding": api_embedding_calls
                },
                "identities": {
                    "embedding_model": config["embedding_model"],
                    "generation_model": config["generation_model"],
                    "reranker_model": config["reranker_model"]
                }
            }
        }

    if not accepted_evidence:
        t_end = time.perf_counter()
        latencies["total_ms"] = round((t_end - t_start) * 1000, 2)
        return {
            "status": "insufficient_evidence",
            "mode": mode,
            "original_question": question,
            "query_set": query_set,
            "child_hits": child_hits,
            "parent_candidates": parent_candidates,
            "accepted_evidence": [],
            "answer": "Không đủ thông tin bằng chứng hợp lệ để trả lời câu hỏi.",
            "citations": [],
            "trace": {
                "stage_latencies": latencies,
                "api_calls": {
                    "gemini_generation": api_generation_calls,
                    "gemini_embedding": api_embedding_calls
                },
                "identities": {
                    "embedding_model": config["embedding_model"],
                    "generation_model": config["generation_model"],
                    "reranker_model": config["reranker_model"]
                }
            }
        }

    prompt = build_grounded_prompt(question, accepted_evidence, mode)
    
    t0_gen = time.perf_counter()
    answer = ""
    gen_failed = False
    
    try:
        if custom_generator is not None:
            answer = custom_generator(prompt)
        else:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=config["generation_model"],
                contents=prompt
            )
            answer = response.text
        api_generation_calls += 1
    except Exception as e:
        gen_failed = True
        
    latencies["generation_ms"] = round((time.perf_counter() - t0_gen) * 1000, 2)
    
    citations = []
    citation_valid = True
    
    if not gen_failed:
        pattern = r"\[(P\d+|E\d+)\]"
        found_tags = re.findall(pattern, answer)
        found_tags = sorted(list(set(found_tags)))
        
        for tag in found_tags:
            try:
                idx = int(tag[1:]) - 1
                if idx < 0 or idx >= len(accepted_evidence):
                    citation_valid = False
                    break
                
                e = accepted_evidence[idx]
                citation_obj = {
                    "evidence_id": tag,
                    "source": e["source"],
                    "page_start": e["page_start"],
                    "page_end": e["page_end"],
                    "warnings": e.get("warnings", []),
                    "ambiguous": e.get("ambiguous", False)
                }
                if "parent" in mode:
                    citation_obj["parent_id"] = e["parent_id"]
                    citation_obj["anchor_child_id"] = e.get("anchor_child_id")
                    citation_obj["supporting_child_ids"] = e.get("supporting_child_ids", [])
                    citation_obj["structural_path"] = e.get("structural_path", {})
                    citation_obj["parent_rerank_score"] = e.get("parent_rerank_score")
                else:
                    citation_obj["child_id"] = e.get("child_id") or e.get("chunk_id")
                    citation_obj["rerank_score"] = e.get("rerank_score")
                    
                citations.append(citation_obj)
            except Exception:
                citation_valid = False
                break

    t_end = time.perf_counter()
    latencies["total_ms"] = round((t_end - t_start) * 1000, 2)
    
    status = "answered"
    if gen_failed or not citation_valid:
        status = "insufficient_evidence"
        answer = "Không thể xác thực trích dẫn từ câu trả lời của mô hình ngôn ngữ lớn."
        citations = []
        
    return {
        "status": status,
        "mode": mode,
        "original_question": question,
        "query_set": query_set,
        "child_hits": child_hits,
        "parent_candidates": parent_candidates,
        "accepted_evidence": accepted_evidence,
        "answer": answer,
        "citations": citations,
        "trace": {
            "stage_latencies": latencies,
            "api_calls": {
                "gemini_generation": api_generation_calls,
                "gemini_embedding": api_embedding_calls
            },
            "identities": {
                "embedding_model": config["embedding_model"],
                "generation_model": config["generation_model"],
                "reranker_model": config["reranker_model"]
            }
        }
    }

def build_grounded_prompt(question: str, accepted_evidence: List[dict], mode: str) -> str:
    evidence_blocks = []
    for idx, e in enumerate(accepted_evidence, 1):
        label = f"P{idx}" if "parent" in mode else f"E{idx}"
        text_val = e["text"]
        src = e["source"]
        struct = e.get("structural_path", {})
        header = struct.get("article") or struct.get("chapter") or "Tài liệu"
        evidence_blocks.append(f"[{label}] Nguồn: {src} | Tiêu đề: {header}\nNội dung: {text_val}")
    
    joined_evidence = "\n\n".join(evidence_blocks)
    prompt = (
        f"Bạn là trợ lý AI trả lời câu hỏi dựa trên các tài liệu pháp luật ngân hàng được cung cấp dưới đây.\n"
        f"Yêu cầu:\n"
        f"1. Chỉ trả lời câu hỏi DỰA TRÊN THÔNG TIN TRONG TÀI LIỆU CUNG CẤP. Không tự bịa thông tin ngoài.\n"
        f"2. Không suy diễn tư vấn pháp lý nằm ngoài văn bản.\n"
        f"3. Đối với mỗi nhận định hoặc câu trả lời, hãy đính kèm nhãn trích dẫn thích hợp dạng [P1], [P2]... (hoặc [E1], [E2]... tùy thuộc nhãn bằng chứng) tương ứng với tài liệu hỗ trợ.\n"
        f"4. Nếu tài liệu cung cấp có mâu thuẫn hoặc cảnh báo (warnings/ambiguous), hãy chỉ rõ giới hạn và điểm mâu thuẫn đó trong câu trả lời.\n\n"
        f"Tài liệu bằng chứng:\n"
        f"{joined_evidence}\n\n"
        f"Câu hỏi gốc: \"{question}\"\n"
        f"Trả lời:"
    )
    return prompt

# ---------------------------------------------------------------------------
# 2. HIERARCHY RESOLUTION ENGINE
# ---------------------------------------------------------------------------

def extract_numerical_suffix(chunk_id: str) -> int:
    """Trích xuất hậu tố số của chunk_id để sắp xếp tuyến tính chính xác."""
    match = re.search(r":(\d+)$", chunk_id)
    if match:
        return int(match.group(1))
    return 999999


def clean_text_for_heading_check(text: str) -> str:
    """Dọn dẹp các ký tự markdown, ngoặc kép ở đầu văn bản để đối sánh regex."""
    text_clean = text.strip()
    # Loại bỏ ký tự bold, italic, ngoặc kép, tiêu đề markdown ở đầu
    text_clean = re.sub(r"^[\*\_#\s\"“‟‟”]+", "", text_clean)
    return text_clean


def detect_heading_in_text(text: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Quét thô phần đầu văn bản (first 80 chars) để nhận diện heading Chương hoặc Điều.
    """
    cleaned = clean_text_for_heading_check(text)
    preview = cleaned[:100]

    chapter_val = None
    article_val = None
    warnings = []

    # Regex nhận diện Chương
    chapter_match = re.match(r"^(Chương\s+[IVXLCDM\d]+[^\n]*)", preview, re.IGNORECASE)
    if chapter_match:
        chapter_val = chapter_match.group(1).strip()
        chapter_val = re.sub(r"[\*\_#\s\"“‟‟”\:\.\,]+$", "", chapter_val)

    # Regex nhận diện Điều
    article_match = re.match(r"^(Điều\s+\d+[^\n]*)", preview, re.IGNORECASE)
    if article_match:
        article_val = article_match.group(1).strip()
        article_val = re.sub(r"[\*\_#\s\"“‟‟”\:\.\,]+$", "", article_val)

    return chapter_val, article_val, warnings


def resolve_chunk_hierarchy(
    chunk: dict,
    last_chapter: Optional[str],
    last_article: Optional[str]
) -> Tuple[dict, Optional[str], Optional[str]]:
    """
    Giải quyết cấp bậc Chương/Điều/Khoản/Điểm cho 1 child chunk theo độ ưu tiên:
    1. Metadata structure chính record
    2. Heading inferred tại đầu chunk
    3. Carry forward từ node trước đó cùng source
    4. Document Fallback
    """
    child_id = chunk["chunk_id"]
    source = chunk["source"]
    text = chunk["text"]

    warnings = []
    ambiguous = False

    chapter_label = None
    article_label = None
    clause_label = None
    point_label = None
    method = "document_fallback"

    # Bước 1: Trích xuất tiêu đề từ văn bản thô (heading check)
    text_chapter, text_article, heading_warnings = detect_heading_in_text(text)
    warnings.extend(heading_warnings)

    # Bước 2: Đọc từ metadata structure
    struct = chunk.get("structure")

    # Xác định chapter
    if struct and isinstance(struct, dict) and struct.get("chapter"):
        chapter_label = struct["chapter"]
        method = "metadata"
    elif text_chapter:
        chapter_label = text_chapter
        method = "heading_inferred"
    elif last_chapter:
        chapter_label = last_chapter
        method = "carried_forward"

    # Xác định article
    if struct and isinstance(struct, dict) and struct.get("article"):
        article_label = struct["article"]
        method = "metadata"
        # Kiểm tra mâu thuẫn metadata với văn bản
        if text_article and text_article.split(".")[0].strip().lower() != article_label.split(".")[0].strip().lower():
            ambiguous = True
            warnings.append(
                f"Mâu thuẫn: Metadata có article '{article_label}' nhưng văn bản chứa heading '{text_article}'."
            )
    elif text_article:
        article_label = text_article
        method = "heading_inferred"
    elif last_article:
        article_label = last_article
        method = "carried_forward"
    else:
        article_label = "DOCUMENT_FALLBACK"
        method = "document_fallback"

    # Trích xuất clause và point từ metadata nếu có
    if struct and isinstance(struct, dict):
        clause_label = struct.get("clause")
        point_label = struct.get("point")

    # Kiểm tra nhiều từ khóa 'Điều ...' xuất hiện trong văn bản (Citation vs Heading)
    # Loại trừ từ khóa xuất hiện ở dòng đầu tiên (đã được coi là Heading)
    cleaned_body = clean_text_for_heading_check(text)
    if text_article:
        # Bỏ đi tiêu đề ở đầu trước khi quét citations
        cleaned_body = cleaned_body[len(text_article):]

    all_dieu_mentions = re.findall(r"(?:Điều\s+\d+)", cleaned_body, re.IGNORECASE)
    if len(all_dieu_mentions) > 0:
        # Phát hiện citations trong text
        warnings.append(
            f"Phát hiện các tham chiếu điều khoản trong văn bản: {all_dieu_mentions}."
        )

    # Xây dựng structural path
    structural_path = {
        "chapter": chapter_label,
        "article": article_label,
        "clause": clause_label,
        "point": point_label
    }

    resolved_record = {
        "child_id": child_id,
        "parent_id": None, # Sẽ gán sau khi build parent windows
        "source": source,
        "page_start": chunk["page_start"],
        "page_end": chunk["page_end"],
        "text": text,
        "structural_path": structural_path,
        "resolution_method": method,
        "ambiguous": ambiguous,
        "warnings": warnings
    }

    # Cập nhật carry forward state
    new_chapter = chapter_label if method in {"metadata", "heading_inferred"} else last_chapter
    new_article = article_label if method in {"metadata", "heading_inferred"} and article_label != "DOCUMENT_FALLBACK" else last_article

    return resolved_record, new_chapter, new_article


# ---------------------------------------------------------------------------
# 3. PARENT DOCUMENT BUILDING
# ---------------------------------------------------------------------------

def build_parent_windows(
    article_key: str,
    source: str,
    children: List[dict],
    parent_max_chars: int
) -> List[dict]:
    """
    Gom nhóm children của cùng một Article thành các cửa sổ Parent Document liên tiếp.
    Đảm bảo tổng ký tự của cửa sổ không vượt quá parent_max_chars (trừ trường hợp 1 child vượt ngưỡng).
    """
    parent_docs = []
    window_idx = 1

    current_children = []
    current_length = 0

    def save_window(cids, text_agg, idx):
        # Tính trang bắt đầu và kết thúc của các con
        p_starts = [c["page_start"] for c in current_children]
        p_ends = [c["page_end"] for c in current_children]

        # Tính số lượng child bị ambiguous
        amb_count = sum(1 for c in current_children if c["ambiguous"])

        # Warnings thu thập từ children
        p_warnings = []
        for c in current_children:
            p_warnings.extend(c["warnings"])

        # Sinh mã MD5 ID ổn định
        seed = f"{source}::{article_key}::w{idx}"
        parent_id = hashlib.md5(seed.encode("utf-8")).hexdigest()

        # Cập nhật parent_id ngược lại cho child records
        for c in current_children:
            c["parent_id"] = parent_id

        parent_docs.append({
            "parent_id": parent_id,
            "source": source,
            "page_start": min(p_starts),
            "page_end": max(p_ends),
            "article_key": article_key,
            "window_index": idx,
            "child_ids": cids,
            "text": text_agg,
            "char_count": len(text_agg),
            "ambiguous_child_count": amb_count,
            "warnings": p_warnings
        })

    for child in children:
        child_text = child["text"]
        child_len = len(child_text)

        # Kiểm tra kích thước của bản thân child
        if child_len > parent_max_chars:
            child["warnings"].append("oversized_single_child")

        # Xác định độ dài nếu cộng thêm child hiện tại
        added_len = child_len + (2 if current_length > 0 else 0) # separator '\n\n'

        if current_length > 0 and current_length + added_len > parent_max_chars:
            # Lưu cửa sổ hiện tại
            agg_text = "\n\n".join(c["text"] for c in current_children)
            save_window([c["child_id"] for c in current_children], agg_text, window_idx)

            # Reset cửa sổ mới
            window_idx += 1
            current_children = [child]
            current_length = child_len
        else:
            current_children.append(child)
            current_length += added_len

    # Lưu cửa sổ cuối cùng nếu còn sót lại
    if current_children:
        agg_text = "\n\n".join(c["text"] for c in current_children)
        save_window([c["child_id"] for c in current_children], agg_text, window_idx)

    return parent_docs


# ---------------------------------------------------------------------------
# 4. HIERARCHY REGISTRY BUILDER & PERSISTENCE
# ---------------------------------------------------------------------------

def compute_file_md5(filepath: Path) -> str:
    """Tính mã băm MD5 của một file."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def build_and_save_hierarchy(
    strategy: str = "hierarchical",
    input_dir: Optional[Path] = None,
    storage_dir: Optional[Path] = None
) -> dict:
    """
    Xây dựng Registry và lưu trữ dạng cấu trúc cha-con deterministic.
    Lưu atomically và tạo manifest với dấu vân tay MD5.
    """
    config = load_hierarchical_config()
    target_storage = storage_dir if storage_dir else BASE_DIR / "storage" / "hierarchy"
    target_storage.mkdir(parents=True, exist_ok=True)

    # 1. Nạp và validate hierarchical chunks
    load_res = load_chunks(input_dir=input_dir, strategy=strategy)
    chunks = load_res["chunks"]

    # Tính dấu vân tay đầu vào
    json_dir = input_dir if input_dir else BASE_DIR.parent.parent / "rag_foundation" / "buoi_05" / "output" / "chunks"
    fingerprints = {}
    if json_dir.exists():
        for j_file in sorted(list(json_dir.glob("*.json"))):
            fingerprints[j_file.name] = compute_file_md5(j_file)

    # 2. Gom nhóm theo source
    chunks_by_source = {}
    for c in chunks:
        src = c["source"]
        if src not in chunks_by_source:
            chunks_by_source[src] = []
        chunks_by_source[src].append(c)

    # 3. Sắp xếp child chunks theo thứ tự số của chunk_id
    for src in chunks_by_source:
        chunks_by_source[src].sort(key=lambda x: extract_numerical_suffix(x["chunk_id"]))

    # Kiểm tra trùng lặp chunk_id
    seen_ids = set()
    for c in chunks:
        cid = c["chunk_id"]
        if cid in seen_ids:
            raise ValueError(f"Trùng lặp chunk_id '{cid}' phát hiện trong luồng xử lý!")
        seen_ids.add(cid)

    # 4. Phân giải cấp bậc (Hierarchy Resolution)
    children_records = []
    children_map = {}

    for src, src_chunks in chunks_by_source.items():
        last_chapter = None
        last_article = None

        for c in src_chunks:
            resolved_child, last_chapter, last_article = resolve_chunk_hierarchy(
                chunk=c,
                last_chapter=last_chapter,
                last_article=last_article
            )
            children_records.append(resolved_child)
            children_map[resolved_child["child_id"]] = resolved_child

    # 5. Gom nhóm theo Parent Article & Chia cửa sổ (Parent Document Building)
    # Để đảm bảo tính deterministic, gom nhóm theo (source, article_key)
    children_by_parent_key = {}
    for c in children_records:
        key = (c["source"], c["structural_path"]["article"])
        if key not in children_by_parent_key:
            children_by_parent_key[key] = []
        children_by_parent_key[key].append(c)

    parent_documents = []
    # Sắp xếp các key để deterministic
    sorted_keys = sorted(children_by_parent_key.keys(), key=lambda x: (x[0], x[1] or ""))

    for src, art_key in sorted_keys:
        group_children = children_by_parent_key[(src, art_key)]
        parents = build_parent_windows(
            article_key=art_key or "DOCUMENT_FALLBACK",
            source=src,
            children=group_children,
            parent_max_chars=config["parent_max_chars"]
        )
        parent_documents.extend(parents)

    # Đếm các chỉ số
    total_warnings = sum(len(c["warnings"]) for c in children_records) + sum(len(p["warnings"]) for p in parent_documents)
    total_ambiguous = sum(1 for c in children_records if c["ambiguous"])

    # 6. Ghi atomically qua file tạm
    children_file = target_storage / "children.json"
    parents_file = target_storage / "parents.json"
    manifest_file = target_storage / "manifest.json"

    manifest_payload = {
        "schema_version": "1.0",
        "input_file_fingerprints": fingerprints,
        "strategy": strategy,
        "config_identity": {
            "parent_max_chars": config["parent_max_chars"],
            "parent_score_child_limit": config["parent_score_child_limit"]
        },
        "counts": {
            "child_chunks": len(children_records),
            "parent_documents": len(parent_documents)
        },
        "warning_counts": {
            "total_warnings": total_warnings,
            "ambiguous_children": total_ambiguous
        },
        "build_timestamp": datetime_now_str()
    }

    # Hàm atomic ghi
    def atomic_write_json(file_path: Path, data: Any):
        temp_path = file_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if file_path.exists():
            os.remove(file_path)
        os.rename(temp_path, file_path)

    atomic_write_json(children_file, children_records)
    atomic_write_json(parents_file, parent_documents)
    atomic_write_json(manifest_file, manifest_payload)

    return {
        "manifest": manifest_payload,
        "children_path": str(children_file),
        "parents_path": str(parents_file)
    }


def datetime_now_str() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_hierarchy_status(storage_dir: Optional[Path] = None) -> dict:
    """Kiểm tra trạng thái Hierarchy Store mà không sửa đổi timestamp hay ghi file."""
    target_storage = storage_dir if storage_dir else BASE_DIR / "storage" / "hierarchy"
    manifest_file = target_storage / "manifest.json"

    if not manifest_file.exists():
        return {
            "hierarchy_built": False,
            "manifest": None
        }

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    return {
        "hierarchy_built": True,
        "manifest": manifest
    }


# ---------------------------------------------------------------------------
# 5. CLI SUBCOMMANDS
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Hierarchical RAG CLI - Buổi 09")
    parser.add_argument("command", choices=["hierarchy-audit", "build-hierarchy", "hierarchy-status", "expand-query", "multi-child", "parent-retrieve", "query", "compare"])
    parser.add_argument("--strategy", default="hierarchical", choices=["fixed-size", "semantic", "hierarchical"])
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--question", default="")
    parser.add_argument("--mode", default="multi_parent", choices=["single_flat", "multi_flat", "single_parent", "multi_parent"])

    args = parser.parse_args()

    if args.command == "hierarchy-audit":
        print(f"\n🔍 [HIERARCHY AUDIT] Đang kiểm tra cấu trúc chunks...")
        load_res = load_chunks(strategy=args.strategy)
        chunks = load_res["chunks"]

        # Phân tích thô thử nghiệm
        last_ch, last_art = None, None
        warnings_count = 0
        ambiguous_count = 0

        for c in chunks[:15]:
            res, last_ch, last_art = resolve_chunk_hierarchy(c, last_ch, last_art)
            if res["ambiguous"]:
                ambiguous_count += 1
            warnings_count += len(res["warnings"])
            print(f"  Child `{res['child_id']}` ➔ Resolved Article: '{res['structural_path']['article']}' (Method: {res['resolution_method']})")

        print(f"\n✅ HOÀN THÀNH AUDIT: Quét thử nghiệm 15 chunks. Tổng Chunks={len(chunks)}.\n")

    elif args.command == "build-hierarchy":
        print(f"\n🚀 [BUILD HIERARCHY] Đang xây dựng cấu trúc cha-con...")
        res = build_and_save_hierarchy(strategy=args.strategy)
        manifest = res["manifest"]
        print(f"✅ ĐÃ HOÀN THÀNH: Xây dựng Hierarchy Registry thành công!")
        print(f"  - Số lượng Chunks con: {manifest['counts']['child_chunks']}")
        print(f"  - Số lượng Tài liệu cha: {manifest['counts']['parent_documents']}")
        print(f"  - Số lượng Cảnh báo: {manifest['warning_counts']['total_warnings']}")
        print(f"  - Số lượng Ambiguous: {manifest['warning_counts']['ambiguous_children']}")
        print(f"  - Manifest lưu tại: '{res['parents_path']}'\n")

    elif args.command == "hierarchy-status":
        status = get_hierarchy_status()
        print(f"\n📊 [HIERARCHY STATUS] Trạng thái Registry:")
        print("=" * 60)
        for k, v in status.items():
            print(f"  {k:<20}: {v}")
        print("=" * 60 + "\n")

    elif args.command == "expand-query":
        if not args.question:
            print("❌ Lỗi: Hãy cung cấp câu hỏi bằng tham số --question.")
            sys.exit(1)
        print(f"\n🔮 [EXPAND QUERY] Đang sinh câu hỏi biến thể cho: '{args.question}'...")
        res = generate_query_variants(args.question)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        print()

    elif args.command == "multi-child":
        if not args.question:
            print("❌ Lỗi: Hãy cung cấp câu hỏi bằng tham số --question.")
            sys.exit(1)
        print(f"\n⚡ [MULTI-CHILD RETRIEVAL] Đang tìm kiếm đa câu hỏi cho: '{args.question}'...")
        res = retrieve_multi_query_hybrid(args.question)
        
        print("\n🔑 Danh sách câu hỏi được sử dụng:")
        q_exp = generate_query_variants(args.question)
        for q in q_exp["queries"]:
            print(f"  - {q['query_id']}: {q['text']} ({q['origin']})")
            
        print("\n📊 Bảng kết quả Child Hits hợp nhất (Top 10):")
        print(f"{'Rank':<5} | {'Child ID':<30} | {'MQ-RRF':<8} | {'Support':<8} | {'Per-Query Ranks'}")
        print("-" * 80)
        for item in res["results"][:10]:
            pq_ranks = ", ".join(f"{qid}:#{rk}" for qid, rk in item["per_query_ranks"].items())
            print(f"{item['multi_query_rank']:<5} | {item['child_id']:<30} | {item['multi_query_rrf_score']:<8} | {item['support_query_count']:<8} | {pq_ranks}")
        
        print("\n📈 Thống kê Trace:")
        print(json.dumps(res["trace"], ensure_ascii=False, indent=2))
        print()

    elif args.command == "parent-retrieve":
        if not args.question:
            print("❌ Lỗi: Hãy cung cấp câu hỏi bằng tham số --question.")
            sys.exit(1)
        print(f"\n🌲 [PARENT RETRIEVAL] Đang truy xuất phân cấp ({args.mode}) cho: '{args.question}'...")
        res = retrieve_hierarchical_parent(args.question, mode=args.mode)
        
        if res.get("status") == "hierarchy_not_ready":
            print(f"❌ Lỗi: Registry chưa sẵn sàng. Chi tiết: {res.get('message')}")
            sys.exit(1)
            
        print("\n🌳 Cây ánh xạ (Mapping Tree):")
        
        if args.mode == "single_parent":
            def single_query_generator(q):
                return {"queries": [{"query_id": "Q0", "text": q, "origin": "original", "focus": "original_intent"}]}
            child_res = retrieve_multi_query_hybrid(args.question, custom_query_generator=single_query_generator)
        else:
            child_res = retrieve_multi_query_hybrid(args.question)
            
        child_hits_map = {c["child_id"]: c for c in child_res["results"]}
        
        for idx, p in enumerate(res["results"]):
            print(f"Parent: {p['parent_id']} | Score: {p['parent_rrf_score']} | Path: {p['structural_path']['article']}")
            for cid in p["supporting_child_ids"]:
                c_hit = child_hits_map.get(cid, {})
                pq_ranks = ", ".join(f"{qid}:#{rk}" for qid, rk in c_hit.get("per_query_ranks", {}).items())
                print(f"└── Child: {cid}")
                print(f"    └── Queries/Ranks: {pq_ranks}")
                
        print("\n📈 Thống kê Trace:")
        print(json.dumps(res["trace"], ensure_ascii=False, indent=2))
        print()

    elif args.command == "query":
        if not args.question:
            print("❌ Lỗi: Hãy cung cấp câu hỏi bằng tham số --question.")
            sys.exit(1)
        print(f"\n🔍 [QUERY RAG] Mode '{args.mode}' | Câu hỏi: '{args.question}'...")
        res = query_hierarchical_rag(args.question, mode=args.mode)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        print()

    elif args.command == "compare":
        if not args.question:
            print("❌ Lỗi: Hãy cung cấp câu hỏi bằng tham số --question.")
            sys.exit(1)
        print(f"\n🔄 [COMPARE RETRIEVAL] Đang so sánh 4 chế độ truy xuất cho câu hỏi: '{args.question}'...")
        
        modes = ["single_flat", "multi_flat", "single_parent", "multi_parent"]
        results = {}
        for m in modes:
            res = query_hierarchical_rag(
                args.question,
                mode=m,
                custom_generator=lambda prompt: "[P1] [E1]"
            )
            results[m] = res
            
        print("\n📊 BẢNG SO SÁNH PHÂN CẤP & FLAT:")
        print(f"{'Mode':<15} | {'Status':<25} | {'Evidence Count':<15} | {'Rerank Ranks & Scores'}")
        print("-" * 90)
        for m in modes:
            res = results[m]
            ev_list = res.get("accepted_evidence", [])
            evidence_count = len(ev_list)
            details = []
            for item in ev_list[:3]:
                if "parent" in m:
                    details.append(f"{item['parent_id'][:8]}(Score: {item['parent_rerank_score']})")
                else:
                    cid = item.get("child_id") or item.get("chunk_id")
                    details.append(f"{cid.split(':')[-1]}(Score: {item['rerank_score']})")
            print(f"{m:<15} | {res['status']:<25} | {evidence_count:<15} | {', '.join(details)}")
        print()
