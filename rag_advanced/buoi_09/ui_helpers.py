"""
UI Helper functions - Buổi 09
Cung cấp các hàm thuần Python giúp định dạng kết quả truy xuất, tạo ma trận đối sánh, xây dựng cây cha-con và ánh xạ lỗi/cảnh báo.
"""

import re
import unicodedata
from typing import List, Dict, Any, Tuple

def citation_formatting(citation: dict) -> str:
    """
    Định dạng cấu trúc citation dict thành chuỗi hiển thị thân thiện trên UI.
    Hỗ trợ cả chế độ Flat (Child-only) và Parent-Child.
    """
    evidence_id = citation.get("evidence_id", "N/A")
    source = citation.get("source", "N/A")
    page_start = citation.get("page_start", "?")
    page_end = citation.get("page_end", "?")
    
    if page_start == page_end:
        page_str = f"Trang {page_start}"
    else:
        page_str = f"Trang {page_start}-{page_end}"
        
    warnings = citation.get("warnings", [])
    warn_str = f" | ⚠️ {', '.join(warnings)}" if warnings else ""
    
    if "parent_id" in citation:
        struct = citation.get("structural_path", {})
        chapter = struct.get("chapter") or "N/A"
        article = struct.get("article") or "N/A"
        score = citation.get("parent_rerank_score")
        score_str = f" | Score: {score:.4f}" if score is not None else ""
        
        supporting = citation.get("supporting_child_ids", [])
        child_str = f" | Chunks: {', '.join(supporting)}" if supporting else ""
        
        return f"[{evidence_id}] {source} ({page_str}) — Chương: {chapter}, Điều: {article}{score_str}{child_str}{warn_str}"
    else:
        child_id = citation.get("child_id") or citation.get("chunk_id", "N/A")
        score = citation.get("rerank_score")
        score_str = f" | Score: {score:.4f}" if score is not None else ""
        return f"[{evidence_id}] {source} ({page_str}) — Chunk: {child_id}{score_str}{warn_str}"


def query_child_matrix(child_hits: List[dict], query_list: List[dict]) -> List[dict]:
    """
    Tạo cấu trúc dòng-cột cho ma trận Query-Child Rank.
    Mỗi dòng đại diện cho một child chunk, các cột là các câu hỏi biến thể Q0..Qn kèm thông tin gộp RRF.
    """
    matrix_rows = []
    for hit in child_hits:
        cid = hit.get("child_id") or hit.get("chunk_id", "N/A")
        row = {
            "Child ID": cid,
            "MQ-RRF Score": hit.get("multi_query_rrf_score", 0.0),
            "Support Count": hit.get("support_query_count", 0)
        }
        # Điền thứ hạng của child chunk trong từng query
        for q in query_list:
            qid = q.get("query_id")
            if not qid:
                continue
            ranks = hit.get("per_query_ranks", {})
            if qid in ranks:
                row[qid] = f"#{ranks[qid]}"
            else:
                row[qid] = "—"
        matrix_rows.append(row)
    return matrix_rows


def parent_tree_data(accepted_parents: List[dict], child_hits: List[dict]) -> List[dict]:
    """
    Liên kết các parent candidates và child hits thành cấu trúc cây phân cấp (tree-like).
    """
    child_map = {}
    for c in child_hits:
        cid = c.get("child_id") or c.get("chunk_id")
        if cid:
            child_map[cid] = c
            
    tree = []
    for p in accepted_parents:
        pid = p.get("parent_id")
        supporting_child_ids = p.get("supporting_child_ids", [])
        
        children_nodes = []
        for cid in supporting_child_ids:
            c_hit = child_map.get(cid, {})
            ranks = c_hit.get("per_query_ranks", {})
            pq_ranks = ", ".join(f"{qid}:#{rk}" for qid, rk in ranks.items()) if ranks else "N/A"
            text_val = c_hit.get("text", "")
            anchor = text_val[:150] + ("..." if len(text_val) > 150 else "")
            
            children_nodes.append({
                "child_id": cid,
                "query_ranks": pq_ranks,
                "anchor_snippet": anchor,
                "full_text": text_val,
                "warnings": c_hit.get("warnings", []),
                "ambiguous": c_hit.get("ambiguous", False)
            })
            
        rank_str = f"Rank: {p.get('parent_rank', '?')} ➔ {p.get('parent_rerank_rank', '?')}" if p.get('parent_rerank_rank') is not None else f"Rank: {p.get('parent_rank', '?')}"
        score_str = f"Score: {p.get('parent_rrf_score', '?')} ➔ {p.get('parent_rerank_score', '?')}" if p.get('parent_rerank_score') is not None else f"Score: {p.get('parent_rrf_score', '?')}"
        
        tree.append({
            "parent_id": pid,
            "structural_path": p.get("structural_path", {}),
            "source": p.get("source", "N/A"),
            "page_start": p.get("page_start", "?"),
            "page_end": p.get("page_end", "?"),
            "rank_change": rank_str,
            "score_change": score_str,
            "text": p.get("text", ""),
            "warnings": p.get("warnings", []),
            "ambiguous": p.get("ambiguous", False),
            "children": children_nodes
        })
    return tree


def mode_comparison_row(mode: str, run_result: dict) -> dict:
    """
    Xây dựng một dòng so sánh (dictionary) cho Mode Comparison Table.
    """
    status = run_result.get("status", "N/A")
    trace = run_result.get("trace", {})
    api_calls = trace.get("api_calls", {})
    stage_latencies = trace.get("stage_latencies", {})
    
    accepted_evidence = run_result.get("accepted_evidence", [])
    child_hits = run_result.get("child_hits", [])
    parent_candidates = run_result.get("parent_candidates", [])
    
    is_parent_mode = "parent" in mode
    
    # Gom danh sách Evidence IDs
    evidence_ids = []
    unique_sources = set()
    unique_articles = set()
    total_chars = 0
    
    for idx, e in enumerate(accepted_evidence, 1):
        label = f"P{idx}" if is_parent_mode else f"E{idx}"
        eid = e.get("parent_id") if is_parent_mode else (e.get("child_id") or e.get("chunk_id"))
        evidence_ids.append(f"{label}:{eid[:8] if eid else 'N/A'}")
        
        if e.get("source"):
            unique_sources.add(e.get("source"))
            
        if is_parent_mode:
            unique_articles.add(e.get("parent_id"))
        else:
            struct = e.get("structure") or {}
            art = struct.get("article") or "DOCUMENT_FALLBACK"
            unique_articles.add(f"{e.get('source')}::{art}")
            
        total_chars += len(e.get("text", ""))
        
    evidence_ids_str = ", ".join(evidence_ids) if evidence_ids else "None"
    
    # Định dạng Rank fields tương ứng với từng chế độ
    rank_details = []
    for idx, e in enumerate(accepted_evidence[:3], 1):
        label = f"P{idx}" if is_parent_mode else f"E{idx}"
        if is_parent_mode:
            pr = e.get("parent_rank", "?")
            prr = e.get("parent_rerank_rank", "?")
            br = e.get("best_child_rank", "?")
            rank_details.append(f"{label}(Raw:{pr}, Rerank:{prr}, BestChild:{br})")
        else:
            fr = e.get("fused_rank") or e.get("multi_query_rank") or e.get("bm25_rank") or "?"
            rr = e.get("rerank_rank", "?")
            rank_details.append(f"{label}(Raw:{fr}, Rerank:{rr})")
    rank_fields_str = ", ".join(rank_details) if rank_details else "None"
    
    # Source / Pages
    src_pages = []
    for e in accepted_evidence:
        src = e.get("source", "N/A")
        p_start = e.get("page_start", "?")
        p_end = e.get("page_end", "?")
        page_str = f"p.{p_start}" if p_start == p_end else f"p.{p_start}-{p_end}"
        src_pages.append(f"{src} ({page_str})")
    src_pages_str = ", ".join(sorted(list(set(src_pages)))) if src_pages else "None"
    
    # Expansion Factor
    if is_parent_mode:
        expansion_factor = trace.get("context_expansion_factor")
        if expansion_factor is None:
            child_chars = sum(len(c.get("text", "")) for c in child_hits)
            expansion_factor = round(total_chars / child_chars, 2) if child_chars > 0 else 1.0
    else:
        expansion_factor = 1.0
        
    # Warnings tổng hợp
    warnings_list = []
    for e in accepted_evidence:
        warnings_list.extend(e.get("warnings", []))
    unique_warnings = sorted(list(set(warnings_list)))
    warnings_str = ", ".join(unique_warnings) if unique_warnings else "None"
    
    # Thống kê latency
    latency_val = stage_latencies.get("total_ms") or trace.get("total_latency_ms") or 0.0
    
    return {
        "Mode": mode,
        "Status": status,
        "Unit Type": "Parent" if is_parent_mode else "Child",
        "Evidence IDs": evidence_ids_str,
        "Ranks": rank_fields_str,
        "Sources/Pages": src_pages_str,
        "Unique Sources": len(unique_sources),
        "Unique Articles": len(unique_articles),
        "Retrieved Children": len(child_hits),
        "Expanded Parents": len(parent_candidates) if is_parent_mode else 0,
        "Context Chars": total_chars,
        "Expansion Factor": expansion_factor,
        "Latency (ms)": round(latency_val, 2),
        "Embedding Calls": api_calls.get("gemini_embedding", 0),
        "Generation Calls": api_calls.get("gemini_generation", 0),
        "Warnings": warnings_str
    }


def warning_status_mapping(status: str, warnings: List[str]) -> dict:
    """
    Ánh xạ mã trạng thái và danh sách cảnh báo thành thông báo tiếng Việt có hướng dẫn xử lý rõ ràng.
    """
    status_map = {
        "answered": {
            "title": "Thành công",
            "type": "success",
            "desc": "Tìm thấy thông tin đối khớp phù hợp và trả lời thành công.",
            "action": "Không cần xử lý thêm."
        },
        "insufficient_evidence": {
            "title": "Không đủ bằng chứng",
            "type": "warning",
            "desc": "Không có tài liệu nào vượt qua ngưỡng tin cậy tối thiểu (Rerank score < RERANK_MIN_SCORE) hoặc trích dẫn LLM không hợp lệ.",
            "action": "Hãy thử hạ chỉ số RERANK_MIN_SCORE ở Sidebar hoặc tinh chỉnh câu hỏi rõ ràng hơn."
        },
        "query_generation_unavailable": {
            "title": "Không thể mở rộng câu hỏi",
            "type": "error",
            "desc": "Mô hình Gemini LLM không phản hồi hoặc bị lỗi khi sinh câu hỏi biến thể (Multi-query).",
            "action": "Vui lòng kiểm tra lại GEMINI_API_KEY ở Sidebar hoặc kết nối mạng."
        },
        "reranker_unavailable": {
            "title": "Mô hình Rerank lỗi",
            "type": "error",
            "desc": "Không thể khởi tạo hoặc chạy mô hình Cross-Encoder Reranker.",
            "action": "Kiểm tra xem mô hình cục bộ đã được tải xuống đầy đủ chưa, hoặc kiểm tra bộ nhớ RAM/GPU."
        },
        "hierarchy_not_ready": {
            "title": "Registry Chưa Sẵn Sàng",
            "type": "error",
            "desc": "Hệ thống Registry phân cấp Cha-Con chưa được xây dựng hoặc bị lỗi khớp cấu hình.",
            "action": "Hãy nhấp nút 'Build Hierarchy Registry' để xây dựng cấu trúc trước khi sử dụng chế độ Parent RAG."
        },
        "collection_not_ready": {
            "title": "Chroma Collection Chưa Sẵn Sàng",
            "type": "error",
            "desc": "Cơ sở dữ liệu Vector chưa được thiết lập hoặc chưa index chunks.",
            "action": "Hãy nhấp nút 'Prepare Semantic Collection' để index các vector vào ChromaDB."
        },
        "multi_query_partial": {
            "title": "Mở rộng câu hỏi bị lỗi một phần",
            "type": "warning",
            "desc": "Không thể sinh tất cả các câu hỏi biến thể yêu cầu, chỉ chạy RAG với câu hỏi gốc hoặc một số biến thể.",
            "action": "Kết quả RAG vẫn được trả về nhưng có thể giảm độ phủ. Kiểm tra API Key."
        },
        "generation_error": {
            "title": "Lỗi sinh câu trả lời",
            "type": "error",
            "desc": "Gặp lỗi khi gửi prompt grounding sang mô hình Gemini generation.",
            "action": "Kiểm tra hạn ngạch (quota) API Gemini hoặc khóa API key có hợp lệ không."
        }
    }
    
    mapped = status_map.get(status, {
        "title": f"Trạng thái: {status}",
        "type": "info",
        "desc": "Trạng thái thực thi chưa được phân loại rõ.",
        "action": "Kiểm tra log hệ thống."
    })
    
    # Lọc cảnh báo thân thiện người dùng
    user_warnings = []
    for w in warnings:
        w_lower = w.lower()
        if "oversized_single_child" in w_lower:
            user_warnings.append("⚠️ Chunk con vượt quá kích thước tối đa của cửa sổ cha (oversized_single_child).")
        elif "first_parent_oversized_context_limit" in w_lower:
            user_warnings.append("⚠️ Cửa sổ cha đầu tiên vượt quá giới hạn ngữ cảnh tối đa nhưng vẫn được giữ lại để tránh mất thông tin (first_parent_oversized_context_limit).")
        elif "mâu thuẫn" in w_lower or "ambiguous" in w_lower:
            user_warnings.append(f"⚠️ Phát hiện mâu thuẫn/mơ hồ trong phân giải phân cấp: {w}")
        else:
            user_warnings.append(f"⚠️ Cảnh báo hệ thống: {w}")
            
    return {
        "title": mapped["title"],
        "type": mapped["type"],
        "desc": mapped["desc"],
        "action": mapped["action"],
        "warnings": user_warnings
    }
