"""
Module RAG Baseline - Buổi 08 (Advanced RAG)
Sao chép từ Semantic Baseline Buổi 07 (rag_foundation/buoi_07/rag.py).
Cung cấp các hàm load, validate, embedding, ChromaDB indexing, retrieval, confidence gate và citation mapping.
Tự nạp cấu hình và lưu trữ từ thư mục rag_advanced/buoi_08/.
"""

import os
import sys
import json
import math
import time
import re
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv
import chromadb
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
CHROMA_DIR = STORAGE_DIR / "chroma"
CHUNKS_DIR = BASE_DIR.parent.parent / "rag_foundation" / "buoi_05" / "output" / "chunks"
ENV_PATH = BASE_DIR / ".env"

ALLOWED_STRATEGIES = {"fixed-size", "semantic", "hierarchical"}


# ---------------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """
    Nạp và xác thực cấu hình từ file .env bằng đường dẫn tuyệt đối.
    Không in ra giá trị API key.
    """
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
    else:
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    model_name = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2").strip()
    if not model_name:
        raise ValueError("GEMINI_EMBEDDING_MODEL không được để rỗng.")

    gen_model = os.getenv("GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite").strip()
    if not gen_model:
        raise ValueError("GEMINI_GENERATION_MODEL không được để rỗng.")

    try:
        dim = int(os.getenv("GEMINI_EMBEDDING_DIM", "768"))
        if not (128 <= dim <= 3072):
            raise ValueError()
    except Exception:
        raise ValueError("GEMINI_EMBEDDING_DIM phải là số nguyên trong khoảng [128, 3072].")

    try:
        max_dist = float(os.getenv("RAG_MAX_DISTANCE", "0.45"))
        if max_dist < 0.0:
            raise ValueError()
    except Exception:
        raise ValueError("RAG_MAX_DISTANCE phải là số thực (float) không âm.")

    return {
        "api_key": api_key,
        "has_api_key": bool(api_key),
        "embedding_model": model_name,
        "embedding_dim": dim,
        "generation_model": gen_model,
        "max_distance": max_dist
    }


# ---------------------------------------------------------------------------
# 2. CHUNKS LOADER & VALIDATOR
# ---------------------------------------------------------------------------

def validate_chunk(item: dict, file_name: str, index: int) -> dict:
    """Validate từng chunk record."""
    required_keys = ["chunk_id", "strategy", "source", "page_start", "page_end", "text"]
    for key in required_keys:
        if key not in item:
            raise ValueError(
                f"Lỗi cấu trúc tại file '{file_name}', record #{index}: Thiếu trường bắt buộc '{key}'."
            )

    cid = str(item["chunk_id"]).strip()
    if not cid:
        raise ValueError(f"Lỗi tại file '{file_name}', record #{index}: 'chunk_id' bị rỗng.")

    strat = str(item["strategy"]).strip()
    if strat not in ALLOWED_STRATEGIES:
        raise ValueError(
            f"Lỗi tại file '{file_name}', record #{index}: 'strategy' ('{strat}') không thuộc {ALLOWED_STRATEGIES}."
        )

    src = str(item["source"]).strip()
    if not src:
        raise ValueError(f"Lỗi tại file '{file_name}', record #{index}: 'source' bị rỗng.")

    try:
        p_start = int(item["page_start"])
        p_end = int(item["page_end"])
    except (ValueError, TypeError):
        raise TypeError(
            f"Lỗi tại file '{file_name}', record #{index}: 'page_start' và 'page_end' phải là số nguyên."
        )

    if p_start <= 0 or p_end <= 0:
        raise ValueError(
            f"Lỗi tại file '{file_name}', record #{index}: 'page_start' ({p_start}) và 'page_end' ({p_end}) phải > 0."
        )

    if p_start > p_end:
        raise ValueError(
            f"Lỗi tại file '{file_name}', record #{index}: 'page_start' ({p_start}) > 'page_end' ({p_end})."
        )

    txt = str(item["text"]).strip()

    return {
        "chunk_id": cid,
        "strategy": strat,
        "source": src,
        "page_start": p_start,
        "page_end": p_end,
        "text": txt
    }


def load_chunks(input_dir: Optional[Path] = None, strategy: str = "hierarchical") -> dict:
    """Nạp danh sách chunks từ thư mục chứa file JSON."""
    target_dir = input_dir if input_dir else CHUNKS_DIR

    if not target_dir.exists():
        raise FileNotFoundError(f"Thư mục chứa chunks '{target_dir}' không tồn tại.")

    json_files = sorted(list(target_dir.glob("*.json")))
    if not json_files:
        raise FileNotFoundError(f"Không tìm thấy file JSON nào trong thư mục '{target_dir}'.")

    valid_chunks = []
    seen_ids = {}
    total_records = 0
    selected_records = 0
    empty_text_skipped = 0
    files_read = 0

    for file_path in json_files:
        file_name = file_path.name
        files_read += 1
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                raise ValueError(f"Lỗi định dạng JSON tại file '{file_name}': {str(e)}")

        if isinstance(data, list):
            records = data
        elif isinstance(data, dict) and "chunks" in data and isinstance(data["chunks"], list):
            records = data["chunks"]
        else:
            raise ValueError(
                f"Cấu trúc JSON tại file '{file_name}' không hợp lệ."
            )

        for idx, item in enumerate(records, 1):
            total_records += 1
            if not isinstance(item, dict):
                raise TypeError(f"Record #{idx} trong file '{file_name}' không phải JSON object.")

            item_strat = item.get("strategy")
            if item_strat != strategy:
                continue

            selected_records += 1
            validated_item = validate_chunk(item, file_name, idx)

            if not validated_item["text"]:
                empty_text_skipped += 1
                continue

            cid = validated_item["chunk_id"]
            if cid in seen_ids:
                first_file, first_idx = seen_ids[cid]
                raise ValueError(f"Trùng lặp chunk_id '{cid}' giữa file '{first_file}' và '{file_name}'.")

            seen_ids[cid] = (file_name, idx)
            valid_chunks.append(validated_item)

    return {
        "chunks": valid_chunks,
        "stats": {
            "files_read": files_read,
            "total_records": total_records,
            "selected_records": selected_records,
            "empty_text_skipped": empty_text_skipped,
            "valid_chunks": len(valid_chunks)
        }
    }


# ---------------------------------------------------------------------------
# 3. EMBEDDINGS & CHROMADB HELPERS
# ---------------------------------------------------------------------------

def _get_genai_client(api_key: str) -> genai.Client:
    if not api_key:
        raise ValueError("Thiếu GEMINI_API_KEY trong cấu hình. Không thể gọi Gemini API.")
    return genai.Client(api_key=api_key)


def _extract_embedding_values(res: Any) -> List[float]:
    if hasattr(res, "embedding") and res.embedding and hasattr(res.embedding, "values"):
        return res.embedding.values
    if hasattr(res, "embeddings") and res.embeddings and len(res.embeddings) > 0 and hasattr(res.embeddings[0], "values"):
        return res.embeddings[0].values
    raise ValueError("Không tìm thấy thuộc tính vector trong kết quả trả về từ Gemini API.")


def generate_single_embedding(client: Any, text: str, source: str, model_name: str, dimension: int) -> List[float]:
    formatted_input = f"title: {source} | text: {text}"
    max_retries = 15
    last_err = None

    for attempt in range(max_retries):
        try:
            res = client.models.embed_content(
                model=model_name,
                contents=formatted_input,
                config=types.EmbedContentConfig(output_dimensionality=dimension)
            )
            return _extract_embedding_values(res)
        except Exception as e:
            last_err = e
            err_msg = str(e)
            if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower()) and attempt < max_retries - 1:
                delay_match = re.search(r"retry(?:Delay)?['\":\s]+(\d+(?:\.\d+)?)s?", err_msg, re.IGNORECASE)
                wait_seconds = float(delay_match.group(1)) + 2.0 if delay_match else min(60.0, 2.0 ** (attempt + 2))
                print(f"⚠️ [GEMINI API 429] Bắt gặp Rate Limit. Đang tạm dừng {wait_seconds:.1f}s (lần {attempt + 1}/{max_retries})...")
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(f"Lỗi khi gọi API Gemini embedding cho document '{source}': {err_msg}")

    raise RuntimeError(f"Lỗi khi gọi API Gemini embedding cho document '{source}': {str(last_err)}")


def generate_single_query_embedding(client: Any, question: str, model_name: str, dimension: int) -> List[float]:
    formatted_input = f"task: question answering | query: {question}"
    max_retries = 15
    last_err = None

    for attempt in range(max_retries):
        try:
            res = client.models.embed_content(
                model=model_name,
                contents=formatted_input,
                config=types.EmbedContentConfig(output_dimensionality=dimension)
            )
            return _extract_embedding_values(res)
        except Exception as e:
            last_err = e
            err_msg = str(e)
            if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower()) and attempt < max_retries - 1:
                delay_match = re.search(r"retry(?:Delay)?['\":\s]+(\d+(?:\.\d+)?)s?", err_msg, re.IGNORECASE)
                wait_seconds = float(delay_match.group(1)) + 2.0 if delay_match else min(60.0, 2.0 ** (attempt + 2))
                print(f"⚠️ [GEMINI API 429] Bắt gặp Rate Limit cho Query. Đang tạm dừng {wait_seconds:.1f}s (lần {attempt + 1}/{max_retries})...")
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(f"Lỗi khi gọi API Gemini query embedding: {err_msg}")

    raise RuntimeError(f"Lỗi khi gọi API Gemini query embedding: {str(last_err)}")


def validate_embeddings(embeddings: List[List[float]], expected_count: int, expected_dim: int):
    if len(embeddings) != expected_count:
        raise ValueError(f"Số lượng vector ({len(embeddings)}) không khớp với số lượng mong đợi ({expected_count}).")

    for idx, vec in enumerate(embeddings):
        if not isinstance(vec, list) or len(vec) == 0:
            raise ValueError(f"Vector tại vị trí #{idx} không hợp lệ hoặc rỗng.")
        if len(vec) != expected_dim:
            raise ValueError(f"Kích thước vector tại vị trí #{idx} ({len(vec)}) không khớp với chiều quy định ({expected_dim}).")
        has_non_zero = False
        for v_idx, val in enumerate(vec):
            if type(val) is not float and type(val) is not int:
                raise TypeError(f"Giá trị tại vector #{idx}[{v_idx}] không phải float.")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Vector tại vị trí #{idx}[{v_idx}] bị NaN hoặc Infinity!")
            if val != 0.0:
                has_non_zero = True
        if not has_non_zero:
            raise ValueError(f"Vector tại vị trí #{idx} là Zero Vector!")


def generate_embeddings(chunks: List[dict], config: dict, client: Optional[Any] = None) -> List[List[float]]:
    if not config["has_api_key"] and client is None:
        raise ValueError("Thiếu GEMINI_API_KEY trong file .env!")
    if client is None:
        client = _get_genai_client(config["api_key"])

    embeddings = []
    for chunk in chunks:
        vec = generate_single_embedding(
            client=client,
            text=chunk["text"],
            source=chunk["source"],
            model_name=config["embedding_model"],
            dimension=config["embedding_dim"]
        )
        embeddings.append(vec)
        time.sleep(0.1)

    validate_embeddings(embeddings, len(chunks), config["embedding_dim"])
    return embeddings


def get_collection_name(strategy: str, dimension: int, model_name: str) -> str:
    model_hash = hashlib.md5(model_name.encode("utf-8")).hexdigest()[:8]
    clean_strat = strategy.lower().replace(" ", "_")
    return f"nhnn-{clean_strat}-{dimension}-{model_hash}"


def get_chroma_client(chroma_dir: Optional[Path] = None) -> chromadb.PersistentClient:
    target_dir = chroma_dir if chroma_dir else CHROMA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(target_dir))


def verify_collection_metadata(col, strategy: str, config: dict):
    meta = col.metadata or {}
    m_strat = meta.get("strategy")
    m_model = meta.get("embedding_model")
    m_dim = meta.get("embedding_dim")

    if m_strat and m_strat != strategy:
        raise ValueError(f"Mismatch collection strategy! Cũ: '{m_strat}', Mới: '{strategy}'.")
    if m_model and m_model != config["embedding_model"]:
        raise ValueError(f"Mismatch collection embedding model! Cũ: '{m_model}', Mới: '{config['embedding_model']}'.")
    if m_dim and int(m_dim) != config["embedding_dim"]:
        raise ValueError(f"Mismatch collection embedding dimension! Cũ: {m_dim}, Mới: {config['embedding_dim']}.")


def index_chunks(chunks: List[dict], embeddings: List[List[float]], strategy: str, config: dict, reset: bool = False, chroma_dir: Optional[Path] = None) -> dict:
    if len(chunks) != len(embeddings):
        raise ValueError("Số lượng chunks và embeddings không bằng nhau.")

    client = get_chroma_client(chroma_dir)
    col_name = get_collection_name(strategy, config["embedding_dim"], config["embedding_model"])

    col_meta = {
        "strategy": strategy,
        "embedding_model": config["embedding_model"],
        "embedding_dim": int(config["embedding_dim"]),
        "distance_metric": "cosine",
        "schema_version": "1.0"
    }

    if reset and any(c.name == col_name for c in client.list_collections()):
        client.delete_collection(name=col_name)

    existing_cols = [c.name for c in client.list_collections()]
    if col_name not in existing_cols:
        collection = client.create_collection(name=col_name, metadata=col_meta, embedding_function=None, configuration={"hnsw": {"space": "cosine"}})
    else:
        collection = client.get_collection(name=col_name, embedding_function=None)

    verify_collection_metadata(collection, strategy, config)

    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "chunk_id": c["chunk_id"],
            "strategy": c["strategy"],
            "source": c["source"],
            "page_start": int(c["page_start"]),
            "page_end": int(c["page_end"]),
            "embedding_model": config["embedding_model"],
            "embedding_dim": int(config["embedding_dim"])
        }
        for c in chunks
    ]

    collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    return {
        "status": "success",
        "collection_name": col_name,
        "count": collection.count(),
        "indexed_chunks": len(chunks)
    }


def run_index(strategy: str = "hierarchical", reset: bool = False, input_dir: Optional[Path] = None, chroma_dir: Optional[Path] = None) -> dict:
    config = load_config()
    if not config["has_api_key"]:
        raise ValueError("Thiếu GEMINI_API_KEY trong file .env!")

    load_res = load_chunks(input_dir=input_dir, strategy=strategy)
    chunks = load_res["chunks"]

    client = get_chroma_client(chroma_dir)
    col_name = get_collection_name(strategy, config["embedding_dim"], config["embedding_model"])

    col_meta = {
        "strategy": strategy,
        "embedding_model": config["embedding_model"],
        "embedding_dim": int(config["embedding_dim"]),
        "distance_metric": "cosine",
        "schema_version": "1.0"
    }

    if reset and any(c.name == col_name for c in client.list_collections()):
        client.delete_collection(name=col_name)

    existing_cols = [c.name for c in client.list_collections()]
    if col_name not in existing_cols:
        collection = client.create_collection(name=col_name, metadata=col_meta, embedding_function=None, configuration={"hnsw": {"space": "cosine"}})
    else:
        collection = client.get_collection(name=col_name, embedding_function=None)

    verify_collection_metadata(collection, strategy, config)

    genai_cli = _get_genai_client(config["api_key"])
    indexed_count = 0

    for idx, c in enumerate(chunks, 1):
        vec = generate_single_embedding(
            client=genai_cli,
            text=c["text"],
            source=c["source"],
            model_name=config["embedding_model"],
            dimension=config["embedding_dim"]
        )
        meta = {
            "chunk_id": c["chunk_id"],
            "strategy": c["strategy"],
            "source": c["source"],
            "page_start": int(c["page_start"]),
            "page_end": int(c["page_end"]),
            "embedding_model": config["embedding_model"],
            "embedding_dim": int(config["embedding_dim"])
        }
        collection.upsert(
            ids=[c["chunk_id"]],
            documents=[c["text"]],
            embeddings=[vec],
            metadatas=[meta]
        )
        indexed_count += 1
        time.sleep(0.1)

    return {
        "status": "success",
        "strategy": strategy,
        "collection_name": col_name,
        "count": collection.count(),
        "indexed_chunks": indexed_count,
        "empty_text_skipped": load_res["stats"]["empty_text_skipped"]
    }


def get_status(strategy: str = "hierarchical", chroma_dir: Optional[Path] = None) -> dict:
    config = load_config()
    client = get_chroma_client(chroma_dir)
    col_name = get_collection_name(strategy, config["embedding_dim"], config["embedding_model"])

    existing_collections = [c.name for c in client.list_collections()]
    col_exists = col_name in existing_collections

    count = 0
    if col_exists:
        col = client.get_collection(name=col_name, embedding_function=None)
        count = col.count()

    return {
        "has_api_key": config["has_api_key"],
        "api_key_status": "Co" if config["has_api_key"] else "Thieu",
        "embedding_model": config["embedding_model"],
        "embedding_dim": config["embedding_dim"],
        "generation_model": config["generation_model"],
        "max_distance": config["max_distance"],
        "strategy": strategy,
        "collection_name": col_name,
        "collection_exists": col_exists,
        "record_count": count
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baseline Semantic RAG CLI - Buổi 08")
    parser.add_argument("command", choices=["status", "index"], help="Lệnh thực thi")
    parser.add_argument("--strategy", default="hierarchical", choices=["fixed-size", "semantic", "hierarchical"])
    parser.add_argument("--reset", action="store_true")

    args = parser.parse_args()

    if args.command == "status":
        st = get_status(args.strategy)
        print(f"📊 STATUS [{args.strategy}]: {st}")
    elif args.command == "index":
        res = run_index(args.strategy, reset=args.reset)
        print(f"✅ INDEX [{args.strategy}]: {res}")
