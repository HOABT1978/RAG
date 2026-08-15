import os
import sys
import io
import argparse
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path to allow importing from src
script_dir = Path(__file__).resolve().parent
buoi_14_dir = script_dir.parent
sys.path.insert(0, str(buoi_14_dir))

from src.unified_retriever import UnifiedRetriever

def fetch_graph_hints(doc_ids, chunk_ids, uri, user, password, db_name):
    hints = {
        'doc_relations': [],
        'contains_relations': [],
        'next_relations': []
    }
    
    # Attempt connecting to Neo4j
    driver = None
    try:
        # Fallback handling from neo4j:// to bolt://
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
            # 1. Fetch document-level relationships
            doc_rel_query = """
            MATCH (v1:VanBan {lab_session: 'buoi_14'})-[r]->(v2:VanBan {lab_session: 'buoi_14'})
            WHERE v1.id IN $doc_ids AND type(r) <> 'CONTAINS'
            RETURN v1.id AS source, type(r) AS rel_type, v2.id AS target, v1.so_ky_hieu AS skh1, v2.so_ky_hieu AS skh2
            """
            res_doc = session.run(doc_rel_query, doc_ids=doc_ids)
            for record in res_doc:
                hints['doc_relations'].append({
                    'from': f"{record['source']} ({record['skh1']})",
                    'rel': record['rel_type'],
                    'to': f"{record['target']} ({record['skh2']})"
                })
                
            # 2. Fetch CONTAINS relationships
            contains_query = """
            MATCH (v:VanBan {lab_session: 'buoi_14'})-[r:CONTAINS]->(d:DieuKhoan {lab_session: 'buoi_14'})
            WHERE d.id IN $chunk_ids
            RETURN v.id AS doc_id, d.id AS chunk_id, v.so_ky_hieu AS skh
            """
            res_contains = session.run(contains_query, chunk_ids=chunk_ids)
            for record in res_contains:
                hints['contains_relations'].append({
                    'doc': f"{record['doc_id']} ({record['skh']})",
                    'chunk': record['chunk_id']
                })
                
            # 3. Fetch NEXT relationships (both directions)
            next_query = """
            MATCH (d1:DieuKhoan {lab_session: 'buoi_14'})-[r:NEXT]->(d2:DieuKhoan {lab_session: 'buoi_14'})
            WHERE d1.id IN $chunk_ids OR d2.id IN $chunk_ids
            RETURN d1.id AS source, d2.id AS target
            """
            res_next = session.run(next_query, chunk_ids=chunk_ids)
            for record in res_next:
                hints['next_relations'].append({
                    'from': record['source'],
                    'to': record['target']
                })
                
    except Exception as e:
        # Silently handle connection issues, print that graph is offline
        return None
    finally:
        if driver:
            driver.close()
            
    return hints

def main():
    parser = argparse.ArgumentParser(description="Query unified RAG system for Buổi 14.")
    parser.add_argument("--query", type=str, required=True, help="Question query string.")
    parser.add_argument("--method", type=str, default="hybrid_rerank", 
                        choices=["bm25", "dense", "hybrid", "hybrid_rerank"],
                        help="Retrieval method configuration.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(dotenv_path=buoi_14_dir / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in env.", file=sys.stderr)
        sys.exit(1)
        
    corpus_path = buoi_14_dir / "data" / "processed" / "chunks_normalized.csv"
    embeddings_path = buoi_14_dir.parent / "kb+hops" / "chunks_embedded.json"
    
    if not corpus_path.exists():
        print(f"Error: Normalized corpus not found at {corpus_path}.", file=sys.stderr)
        sys.exit(1)
        
    df_corpus = pd.read_csv(corpus_path)
    
    # Initialize retriever
    retriever = UnifiedRetriever(df_corpus, embeddings_path, api_key)
    
    print(f"\n🚀 Running Retrieval...")
    print(f"   Query  : '{args.query}'")
    print(f"   Method : '{args.method}'")
    print(f"   Top-K  : {args.top_k}")
    
    results = retriever.retrieve(args.query, method=args.method, top_k=args.top_k)
    
    # Print Results
    print(f"\n==========================================================================================")
    print(f"RETRIEVED RESULTS ({args.method.upper()})")
    print(f"==========================================================================================")
    
    doc_ids = []
    chunk_ids = []
    
    for idx, res in enumerate(results, start=1):
        doc_ids.append(res['document_id'])
        chunk_ids.append(res['chunk_id'])
        
        score_str = f"Score: {res['score']:.4f}"
        if 'hybrid_score' in res:
            score_str += f" (RRF Score: {res['hybrid_score']:.4f})"
            
        print(f"Hạng {res['rank']} | Chunk ID: {res['chunk_id']} | Document ID: {res['document_id']} | {score_str}")
        print(f"Citation: {res['citation']}")
        print(f"Nội dung: {res['text'][:300]}...")
        print("-" * 90)
        
    # Unique IDs for Neo4j query
    doc_ids = list(set(doc_ids))
    chunk_ids = list(set(chunk_ids))
    
    # Fetch Graph Hints
    uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "BUOI_14")
    password = os.getenv("NEO4J_PASSWORD", "12345678")
    db_name = os.getenv("NEO4J_DATABASE", "neo4j")
    
    print(f"\n==========================================================================================")
    print(f"GRAPH HINTS (Direct Relations in Mini KG)")
    print(f"==========================================================================================")
    print(f"Retrieved Document IDs : {doc_ids}")
    print(f"Retrieved Chunk IDs    : {chunk_ids}\n")
    
    graph_hints = fetch_graph_hints(doc_ids, chunk_ids, uri, user, password, db_name)
    
    if graph_hints is None:
        print("ℹ️  Graph Database is offline or connection refused. Skipping related graph path traversal.")
    else:
        # Document Relationships
        print("[Mối quan hệ liên văn bản giữa các tài liệu liên quan]:")
        if graph_hints['doc_relations']:
            for rel in graph_hints['doc_relations']:
                print(f"  *  {rel['from']} -[:{rel['rel']}]-> {rel['to']}")
        else:
            print("  *  Không tìm thấy mối quan hệ liên văn bản nào trong đồ thị.")
            
        print("\n[Mối quan hệ chứa đựng (CONTAINS)]:")
        if graph_hints['contains_relations']:
            for rel in graph_hints['contains_relations']:
                print(f"  *  Văn bản {rel['doc']} -[:CONTAINS]-> Phân đoạn {rel['chunk']}")
                
        print("\n[Mối quan hệ cấu trúc liền kề (NEXT)]:")
        if graph_hints['next_relations']:
            for rel in graph_hints['next_relations']:
                print(f"  *  Phân đoạn {rel['from']} -[:NEXT]-> Phân đoạn {rel['to']}")
        else:
            print("  *  Không tìm thấy quan hệ liền kề NEXT nào cho các phân đoạn trong đồ thị.")
            
    print("==========================================================================================")

if __name__ == '__main__':
    main()
