import os
import json
import glob
import sqlite3
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import chromadb
from google import genai
from google.genai import types

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHUNKS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "buoi_05", "output", "chunks"))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
CHROMA_DIR = os.path.join(STORAGE_DIR, "chroma")
SQLITE_DB_PATH = os.path.join(STORAGE_DIR, "rag.db")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)


def _validate_chunk(chunk: dict) -> bool:
    """Kiểm tra cấu trúc và tính hợp lệ của 1 chunk JSON."""
    if not isinstance(chunk, dict):
        return False
    required_keys = ["chunk_id", "text", "source"]
    for key in required_keys:
        if not chunk.get(key) or not str(chunk.get(key)).strip():
            return False
    return True


def _get_gemini_client() -> Optional[genai.Client]:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key.strip():
        try:
            return genai.Client(api_key=api_key.strip())
        except Exception:
            return None
    return None


def _embed_text(client: Optional[genai.Client], text: str) -> Optional[List[float]]:
    if not client or not text:
        return None
    try:
        res = client.models.embed_content(
            model="text-embedding-004",
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=384)
        )
        return res.embedding.values
    except Exception:
        try:
            res = client.models.embed_content(
                model="gemini-embedding-2",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=384)
            )
            return res.embedding.values
        except Exception:
            return None


def _get_chroma_collection():
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return chroma_client.get_or_create_collection(name="rag_chunks")


def _get_db_connection():
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db = os.getenv("POSTGRES_DB", "rag_db")
    pg_user = os.getenv("POSTGRES_USER", "postgres")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "")

    try:
        import psycopg
        conn = psycopg.connect(
            host=pg_host,
            port=pg_port,
            dbname=pg_db,
            user=pg_user,
            password=pg_pass,
            connect_timeout=2
        )
        return conn, "postgres"
    except Exception:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        return conn, "sqlite"


def _init_db_table(conn, db_type: str):
    cursor = conn.cursor()
    sql = """
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id TEXT PRIMARY KEY,
        source TEXT,
        strategy TEXT,
        page_start INTEGER,
        page_end INTEGER,
        text TEXT
    );
    """
    cursor.execute(sql)
    conn.commit()


def _save_chunk_text(conn, db_type: str, chunk: dict):
    cursor = conn.cursor()
    if db_type == "postgres":
        sql = """
        INSERT INTO chunks (chunk_id, source, strategy, page_start, page_end, text)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (chunk_id) DO UPDATE SET text = EXCLUDED.text;
        """
        cursor.execute(sql, (
            chunk["chunk_id"],
            chunk.get("source", ""),
            chunk.get("strategy", ""),
            int(chunk.get("page_start", 0)),
            int(chunk.get("page_end", 0)),
            chunk.get("text", "")
        ))
    else:
        sql = """
        INSERT OR REPLACE INTO chunks (chunk_id, source, strategy, page_start, page_end, text)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        cursor.execute(sql, (
            chunk["chunk_id"],
            chunk.get("source", ""),
            chunk.get("strategy", ""),
            int(chunk.get("page_start", 0)),
            int(chunk.get("page_end", 0)),
            chunk.get("text", "")
        ))
    conn.commit()


def _get_chunks_by_ids(conn, db_type: str, chunk_ids: List[str]) -> List[dict]:
    if not chunk_ids:
        return []
    cursor = conn.cursor()
    if db_type == "postgres":
        placeholders = ", ".join(["%s"] * len(chunk_ids))
        sql = f"SELECT chunk_id, source, strategy, page_start, page_end, text FROM chunks WHERE chunk_id IN ({placeholders});"
        cursor.execute(sql, chunk_ids)
        rows = cursor.fetchall()
    else:
        placeholders = ", ".join(["?"] * len(chunk_ids))
        sql = f"SELECT chunk_id, source, strategy, page_start, page_end, text FROM chunks WHERE chunk_id IN ({placeholders});"
        cursor.execute(sql, chunk_ids)
        rows = cursor.fetchall()

    results = []
    for r in rows:
        results.append({
            "chunk_id": r[0],
            "source": r[1],
            "strategy": r[2],
            "page_start": r[3],
            "page_end": r[4],
            "text": r[5]
        })
    return results


def index() -> dict:
    load_dotenv()
    client = _get_gemini_client()
    if not client:
        raise ValueError("Không tìm thấy GEMINI_API_KEY hoặc lỗi khởi tạo client. Không tạo vector giả khi embedding lỗi!")

    collection = _get_chroma_collection()
    conn, db_type = _get_db_connection()
    _init_db_table(conn, db_type)

    json_files = glob.glob(os.path.join(CHUNKS_DIR, "*.json"))
    if not json_files:
        conn.close()
        return {"status": "error", "message": f"Không tìm thấy file JSON nào tại {CHUNKS_DIR}", "num_documents": 0, "num_chunks": 0}

    total_chunks = 0
    sources = set()

    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                chunks = json.load(f)
            except Exception:
                continue

        for chunk in chunks:
            if not _validate_chunk(chunk):
                continue

            chunk_id = chunk["chunk_id"]
            text = chunk["text"]
            source = chunk["source"]
            sources.add(source)

            # Đảm bảo lưu thông tin chi tiết vào database
            _save_chunk_text(conn, db_type, chunk)

            # Tạo embedding qua Gemini
            emb = _embed_text(client, text)
            if emb is None:
                conn.close()
                raise RuntimeError(f"Lỗi tạo embedding cho chunk '{chunk_id}'. Không tạo vector giả!")

            metadata = {
                "source": source,
                "strategy": str(chunk.get("strategy", "")),
                "page_start": int(chunk.get("page_start", 0)),
                "page_end": int(chunk.get("page_end", 0))
            }

            collection.upsert(
                ids=[chunk_id],
                embeddings=[emb],
                documents=[text],
                metadatas=[metadata]
            )
            total_chunks += 1

    conn.commit()
    conn.close()

    return {
        "status": "indexed",
        "num_documents": len(sources),
        "num_chunks": total_chunks,
        "db_storage": db_type
    }


def ask(question: str, k: int = 3) -> dict:
    load_dotenv()
    client = _get_gemini_client()
    if not client:
        return {
            "question": question,
            "answer": "⚠️ Đã xảy ra lỗi hoặc thiếu GEMINI_API_KEY. Không tạo vector giả để truy vấn khi không có API key thật.",
            "chunks": [],
            "db_storage": "N/A"
        }

    collection = _get_chroma_collection()
    conn, db_type = _get_db_connection()

    query_emb = _embed_text(client, question)
    if query_emb is None:
        conn.close()
        return {
            "question": question,
            "answer": "⚠️ Tạo embedding cho câu hỏi thất bại. Không tạo vector giả khi embedding lỗi!",
            "chunks": [],
            "db_storage": db_type
        }

    query_res = collection.query(query_embeddings=[query_emb], n_results=k)
    retrieved_ids = query_res["ids"][0] if query_res and query_res.get("ids") else []
    retrieved_chunks = _get_chunks_by_ids(conn, db_type, retrieved_ids)
    conn.close()

    chunk_map = {c["chunk_id"]: c for c in retrieved_chunks}
    ordered_chunks = [chunk_map[cid] for cid in retrieved_ids if cid in chunk_map]

    if not ordered_chunks:
        return {
            "question": question,
            "answer": "Tài liệu không đủ thông tin để trả lời câu hỏi này.",
            "chunks": [],
            "db_storage": db_type
        }

    # Đóng gói context với metadata thật để LLM làm bằng chứng (evidence)
    formatted_context_list = []
    for c in ordered_chunks:
        fmt = (
            f"--- Chunk ID: {c['chunk_id']} | Nguồn: {c['source']} | Trang: {c['page_start']}-{c['page_end']} ---\n"
            f"{c['text']}"
        )
        formatted_context_list.append(fmt)

    context_str = "\n\n".join(formatted_context_list)

    prompt = (
        "Bạn là trợ lý AI phân tích tài liệu. Hãy dựa VÀO DUY NHẤT các trích đoạn văn bản (context) dưới đây để trả lời câu hỏi của người dùng.\n\n"
        "QUY TẮC BẮT BUỘC:\n"
        "1. Chỉ dùng thông tin có trong các trích đoạn dưới đây để trả lời câu hỏi.\n"
        "2. NẾU THÔNG TIN TRONG CÁC TRÍCH ĐOẠN KHÔNG ĐỦ ĐỂ TRẢ LỜI CÂU HỎI, bạn BẮT BUỘC phải trả lời chính xác câu: "
        "\"Tài liệu không đủ thông tin để trả lời câu hỏi này.\" và KHÔNG ĐƯỢC tự suy đoán hay bịa đặt.\n"
        "3. Với mỗi khẳng định/thông tin trong câu trả lời, bạn PHẢI trích dẫn nguồn bằng cú pháp: "
        "[Nguồn: <source>, Trang: <page_start>-<page_end>, Chunk: <chunk_id>].\n\n"
        f"--- BẮT ĐẦU CONTEXT ---\n{context_str}\n--- KẾT THÚC CONTEXT ---\n\n"
        f"Câu hỏi: {question}"
    )

    try:
        try:
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        answer = response.text.strip()
    except Exception as e:
        answer = f"[Lỗi khi gọi Gemini: {str(e)}]"

    return {
        "question": question,
        "answer": answer,
        "chunks": ordered_chunks,
        "db_storage": db_type
    }


def status() -> dict:
    load_dotenv()
    collection = _get_chroma_collection()
    num_chunks = collection.count()

    conn, db_type = _get_db_connection()
    num_docs = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT source) FROM chunks;")
        row = cursor.fetchone()
        if row and row[0] is not None:
            num_docs = row[0]
    except Exception:
        num_docs = 0
    finally:
        conn.close()

    return {
        "num_documents": num_docs,
        "num_chunks": num_chunks,
        "db_storage": db_type
    }
