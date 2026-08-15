import os
import sys
import io
import argparse
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path to allow importing from src
script_dir = Path(__file__).resolve().parent
buoi_14_dir = script_dir.parent
sys.path.insert(0, str(buoi_14_dir))

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever

def print_results(title, results):
    print(f"\n==================================================")
    print(title)
    print(f"==================================================")
    for res in results:
        print(f"Rank {res['rank']} [Score: {res['retrieval_score']:.4f}]")
        print(f"Citation: {res['citation']}")
        print(f"Text: {res['text'][:180].replace(chr(10), ' ')}...")
        print("-" * 50)

def generate_markdown_report(queries_results, output_path):
    md = []
    md.append("# BÁO CÁO THỬ NGHIỆM BASELINE RETRIEVAL (BUỔI 14)")
    md.append("")
    md.append("Báo cáo này so sánh kết quả truy xuất của phương pháp **BM25-only (Lexical Search)** và **Dense-only (Semantic Search)** trên 3 loại câu hỏi thử nghiệm.")
    md.append("")
    
    for q_idx, (query, q_type, bm25_res, dense_res) in enumerate(queries_results, start=1):
        md.append(f"## Câu hỏi {q_idx}: \"{query}\"")
        md.append(f"- **Phân loại**: {q_type}")
        md.append("")
        
        md.append("### 1. Kết quả BM25 (Lexical Search)")
        md.append("| Hạng | Score | Chunk ID | Citation |")
        md.append("| :--- | :--- | :--- | :--- |")
        for r in bm25_res:
            md.append(f"| {r['rank']} | {r['retrieval_score']:.4f} | `{r['chunk_id']}` | {r['citation']} |")
        md.append("")
        
        md.append("### 2. Kết quả Dense (Semantic Search)")
        md.append("| Hạng | Score | Chunk ID | Citation |")
        md.append("| :--- | :--- | :--- | :--- |")
        for r in dense_res:
            md.append(f"| {r['rank']} | {r['retrieval_score']:.4f} | `{r['chunk_id']}` | {r['citation']} |")
        md.append("")
        
        md.append("### 3. Đối chiếu nội dung hàng đầu (Top-1 Comparison)")
        md.append("#### Top-1 BM25:")
        md.append(f"> **Citation**: {bm25_res[0]['citation']}\n>\n> {bm25_res[0]['text']}")
        md.append("")
        md.append("#### Top-1 Dense:")
        md.append(f"> **Citation**: {dense_res[0]['citation']}\n>\n> {dense_res[0]['text']}")
        md.append("")
        md.append("---")
        md.append("")
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md) + "\n")
    print(f"Markdown report written to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Run baseline BM25 and Dense retrievers.")
    parser.add_argument("--query", type=str, help="Search query string.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve.")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(dotenv_path=buoi_14_dir / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variable/file.", file=sys.stderr)
        sys.exit(1)
        
    # Paths
    corpus_path = buoi_14_dir / "data" / "processed" / "chunks_normalized.csv"
    embeddings_path = buoi_14_dir.parent / "kb+hops" / "chunks_embedded.json"
    
    if not corpus_path.exists():
        print(f"Error: Normalized corpus not found at {corpus_path}. Run prepare_corpus.py first.", file=sys.stderr)
        sys.exit(1)
        
    # Read corpus
    df = pd.read_csv(corpus_path)
    
    # Initialize retrievers
    print("Initializing BM25 Retriever...")
    bm25_retriever = BM25Retriever(df)
    
    print("Initializing Dense Retriever...")
    dense_retriever = DenseRetriever(df, embeddings_path, api_key)
    
    if args.query:
        # Run specific query
        query = args.query
        top_k = args.top_k
        print(f"\nRunning search for: '{query}' (top_k={top_k})")
        
        bm25_results = bm25_retriever.retrieve(query, top_k=top_k)
        dense_results = dense_retriever.retrieve(query, top_k=top_k)
        
        print_results("BM25 RESULTS", bm25_results)
        print_results("DENSE RESULTS", dense_results)
    else:
        # Run suite of 3 test queries
        test_queries = [
            ("Điều 12 Nghị định số 73/2016/NĐ-CP", "Câu có mã/số hiệu cụ thể"),
            ("quy định về an toàn trong vận chuyển tiền mặt và tài sản quý của ngân hàng", "Câu diễn đạt semantic (ý nghĩa)"),
            ("Thông tư 01/2014 quy định thế nào về việc đóng gói niêm phong tiền mặt", "Câu kết hợp cả hai yếu tố")
        ]
        
        queries_results = []
        for query, q_type in test_queries:
            print(f"\n[Suite] Running search for: '{query}' ({q_type})")
            bm25_res = bm25_retriever.retrieve(query, top_k=5)
            dense_res = dense_retriever.retrieve(query, top_k=5)
            queries_results.append((query, q_type, bm25_res, dense_res))
            
            print_results(f"BM25 - {q_type}", bm25_res[:3])
            print_results(f"DENSE - {q_type}", dense_res[:3])
            
        # Write markdown report
        outputs_dir = buoi_14_dir / "outputs"
        os.makedirs(outputs_dir, exist_ok=True)
        generate_markdown_report(queries_results, outputs_dir / "retrieval_examples.md")

if __name__ == '__main__':
    main()
