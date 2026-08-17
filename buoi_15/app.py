import os
import sys
import re
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Add parent directory to path to allow importing from src
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

from src.unified_retriever import UnifiedRetriever

# Set Page Config
st.set_page_config(
    page_title="RAG Hybrid Search — Buổi 14",
    page_icon="🔍",
    layout="wide"
)

# Load env variables
load_dotenv(dotenv_path=script_dir / ".env")
api_key = os.getenv("GEMINI_API_KEY")

# Resource Caching for retrievers (prevents reloading model on every rerun)
@st.cache_resource
def init_retriever():
    corpus_path = script_dir / "data" / "processed" / "chunks_normalized.csv"
    embeddings_path = script_dir.parent / "kb+hops" / "chunks_embedded.json"
    
    if not corpus_path.exists():
        st.error(f"Error: Normalized corpus not found at {corpus_path}. Please run prepare_corpus.py first.")
        st.stop()
        
    df = pd.read_csv(corpus_path)
    return UnifiedRetriever(df, embeddings_path, api_key)

# Helper function to fetch Graph Hints
def get_graph_hints(doc_ids, chunk_ids):
    uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "BUOI_14")
    password = os.getenv("NEO4J_PASSWORD", "12345678")
    db_name = os.getenv("NEO4J_DATABASE", "neo4j")
    
    hints = {
        'doc_relations': [],
        'contains_relations': [],
        'next_relations': []
    }
    
    driver = None
    try:
        # Check connection using neo4j:// or bolt://
        target_uri = uri
        try:
            driver = GraphDatabase.driver(target_uri, auth=(user, password))
            driver.verify_connectivity()
        except Exception:
            if uri.startswith("neo4j://"):
                target_uri = uri.replace("neo4j://", "bolt://")
                driver = GraphDatabase.driver(target_uri, auth=(user, password))
                driver.verify_connectivity()
            else:
                raise
                
        with driver.session(database=db_name) as session:
            # 1. Document relations
            doc_rel_query = """
            MATCH (v1:VanBan {lab_session: 'buoi_14'})-[r]->(v2:VanBan {lab_session: 'buoi_14'})
            WHERE v1.id IN $doc_ids AND type(r) <> 'CONTAINS'
            RETURN v1.id AS source, type(r) AS rel_type, v2.id AS target, v1.so_ky_hieu AS skh1, v2.so_ky_hieu AS skh2
            """
            res_doc = session.run(doc_rel_query, doc_ids=doc_ids)
            for record in res_doc:
                hints['doc_relations'].append(
                    f"📄 {record['source']} ({record['skh1']}) -[:{record['rel_type']}]-> {record['target']} ({record['skh2']})"
                )
                
            # 2. Contains relations
            contains_query = """
            MATCH (v:VanBan {lab_session: 'buoi_14'})-[r:CONTAINS]->(d:DieuKhoan {lab_session: 'buoi_14'})
            WHERE d.id IN $chunk_ids
            RETURN v.id AS doc_id, d.id AS chunk_id, v.so_ky_hieu AS skh
            """
            res_contains = session.run(contains_query, chunk_ids=chunk_ids)
            for record in res_contains:
                hints['contains_relations'].append(
                    f"📄 Văn bản {record['doc_id']} ({record['skh']}) -[:CONTAINS]-> 🧩 Phân đoạn {record['chunk_id']}"
                )
                
            # 3. Next relations
            next_query = """
            MATCH (d1:DieuKhoan {lab_session: 'buoi_14'})-[r:NEXT]->(d2:DieuKhoan {lab_session: 'buoi_14'})
            WHERE d1.id IN $chunk_ids OR d2.id IN $chunk_ids
            RETURN d1.id AS source, d2.id AS target
            """
            res_next = session.run(next_query, chunk_ids=chunk_ids)
            for record in res_next:
                hints['next_relations'].append(
                    f"🧩 Phân đoạn {record['source']} -[:NEXT]-> 🧩 Phân đoạn {record['to'] if 'to' in record else record['target']}"
                )
    except Exception as e:
        return None
    finally:
        if driver:
            driver.close()
            
    return hints

# UI Layout
st.title("🔍 RAG Hybrid Search & Reranking — Buổi 14")
st.markdown("---")

if not api_key:
    st.warning("⚠️ Cảnh báo: `GEMINI_API_KEY` chưa được định nghĩa trong tệp `.env`. Bộ tìm kiếm ngữ nghĩa sẽ hoạt động ở chế độ fallback Jaccard.")

# Form controls
col_query, col_method, col_k = st.columns([5, 3, 2])

with col_query:
    query = st.text_input("Câu hỏi", placeholder="Nhập nội dung câu hỏi cần tìm kiếm pháp lý...")
    
with col_method:
    method_label = st.selectbox(
        "Phương pháp tìm kiếm",
        ["Hybrid + Rerank", "Hybrid (RRF)", "BM25 (Từ khóa)", "Dense (Ngữ nghĩa)"]
    )
    # Map method labels to parameters
    method_map = {
        "BM25 (Từ khóa)": "bm25",
        "Dense (Ngữ nghĩa)": "dense",
        "Hybrid (RRF)": "hybrid",
        "Hybrid + Rerank": "hybrid_rerank"
    }
    method = method_map[method_label]
    
with col_k:
    top_k = st.number_input("Top-k kết quả", min_value=1, max_value=20, value=5)

search_clicked = st.button("Tìm kiếm", type="primary")

if search_clicked and query:
    with st.spinner("Đang chạy truy xuất dữ liệu..."):
        retriever = init_retriever()
        results = retriever.retrieve(query, method=method, top_k=top_k)
        
        if not results:
            st.warning("Không tìm thấy kết quả nào phù hợp.")
        else:
            # Layout splits into results list and sidebar comparison
            main_col, side_col = st.columns([7, 3])
            
            with main_col:
                st.subheader(f"Kết quả Tìm kiếm ({method_label})")
                for item in results:
                    with st.expander(f"Hạng {item['rank']} | Chunk: {item['chunk_id']} | Document: {item['document_id']} (Score: {item['score']:.4f})", expanded=True):
                        st.markdown(f"**Citation**: `{item['citation']}`")
                        st.write(item['text'])
                        
            with side_col:
                # Rank comparison for hybrid_rerank
                if method == 'hybrid_rerank':
                    st.subheader("📊 Thay đổi thứ tự (Rerank)")
                    st.markdown("**BEFORE vs AFTER Rerank:**")
                    
                    comparison_data = []
                    for item in results:
                        comparison_data.append({
                            "Chunk ID": item['chunk_id'],
                            "Hạng cũ (Hybrid)": item['hybrid_rank'],
                            "Hạng mới": item['rank'],
                            "Điểm Rerank": round(item['score'], 4)
                        })
                    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
                    
                # Details on hybrid weights
                elif method == 'hybrid':
                    st.subheader("📊 Chi tiết xếp hạng")
                    comparison_data = []
                    for item in results:
                        comparison_data.append({
                            "Chunk ID": item['chunk_id'],
                            "Hạng BM25": item.get('bm25_rank', '-'),
                            "Hạng Dense": item.get('dense_rank', '-'),
                            "Điểm RRF": round(item['score'], 4)
                        })
                    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
                    
                # Graph hints section
                st.subheader("🕸️ Graph Hints (Mối liên kết đồ thị)")
                doc_ids = list(set([item['document_id'] for item in results]))
                chunk_ids = list(set([item['chunk_id'] for item in results]))
                
                hints = get_graph_hints(doc_ids, chunk_ids)
                
                if hints is None:
                    st.info("ℹ️ Neo4j Database chưa sẵn sàng (Offline hoặc sai thông tin đăng nhập).")
                else:
                    st.markdown("**Mối quan hệ chứa đựng (CONTAINS):**")
                    if hints['contains_relations']:
                        for r in hints['contains_relations']:
                            st.caption(r)
                    else:
                        st.caption("*Không tìm thấy*")
                        
                    st.markdown("**Mối quan hệ liền kề (NEXT):**")
                    if hints['next_relations']:
                        for r in hints['next_relations']:
                            st.caption(r)
                    else:
                        st.caption("*Không tìm thấy*")
                        
                    st.markdown("**Mối quan hệ liên văn bản:**")
                    if hints['doc_relations']:
                        for r in hints['doc_relations']:
                            st.caption(r)
                    else:
                        st.caption("*Không tìm thấy*")
