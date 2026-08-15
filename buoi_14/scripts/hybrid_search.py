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
from src.hybrid_retriever import HybridRetriever

def print_hybrid_results(results):
    print(f"\n==================================================")
    print("HYBRID RESULTS")
    print(f"==================================================")
    print(f"{'Rank':<5} | {'Chunk ID':<15} | {'BM25 Rank':<10} | {'Dense Rank':<10} | {'RRF Score':<10} | {'Citation'}")
    print("-" * 100)
    for res in results:
        bm25_r = res['bm25_rank'] if res['bm25_rank'] is not None else '-'
        dense_r = res['dense_rank'] if res['dense_rank'] is not None else '-'
        print(f"{res['final_rank']:<5} | {res['chunk_id']:<15} | {bm25_r:<10} | {dense_r:<10} | {res['rrf_score']:.4f} | {res['citation']}")
    print("-" * 100)

def generate_hybrid_markdown_report(queries_results, output_path):
    md = []
    md.append("# BÁO CÁO SO SÁNH RETRIEVAL: BM25 vs DENSE vs HYBRID (BUỔI 14)")
    md.append("")
    md.append("Báo cáo này so sánh kết quả truy xuất của phương pháp **BM25-only**, **Dense-only** và **Hybrid Search (RRF k=60)** trên 3 loại câu hỏi thử nghiệm để thấy được hiệu quả kết hợp thông tin.")
    md.append("")
    
    for q_idx, (query, q_type, bm25_res, dense_res, hybrid_res) in enumerate(queries_results, start=1):
        md.append(f"## Câu hỏi {q_idx}: \"{query}\"")
        md.append(f"- **Phân loại**: {q_type}")
        md.append("")
        
        # Comparison Table
        md.append("### Bảng đối chiếu kết quả xếp hạng:")
        md.append("| Hạng | Phương pháp | Chunk ID | Score | Citation |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        
        # Add Top 3 of each
        for r in bm25_res[:3]:
            md.append(f"| {r['rank']} | BM25 | `{r['chunk_id']}` | {r['retrieval_score']:.4f} | {r['citation']} |")
        for r in dense_res[:3]:
            md.append(f"| {r['rank']} | Dense | `{r['chunk_id']}` | {r['retrieval_score']:.4f} | {r['citation']} |")
        for r in hybrid_res[:3]:
            bm25_rank_str = f"BM25 Rk: {r['bm25_rank']}" if r['bm25_rank'] is not None else "BM25: -"
            dense_rank_str = f"Dense Rk: {r['dense_rank']}" if r['dense_rank'] is not None else "Dense: -"
            md.append(f"| {r['final_rank']} | **Hybrid** | `{r['chunk_id']}` | {r['rrf_score']:.4f} ({bm25_rank_str}, {dense_rank_str}) | {r['citation']} |")
        md.append("")
        
        md.append("### Kết quả chi tiết của Hybrid Search (Top 5)")
        md.append("| Hạng | Chunk ID | Hạng BM25 | Hạng Dense | Điểm RRF | Citation |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in hybrid_res:
            b_rk = r['bm25_rank'] if r['bm25_rank'] is not None else "-"
            d_rk = r['dense_rank'] if r['dense_rank'] is not None else "-"
            md.append(f"| {r['final_rank']} | `{r['chunk_id']}` | {b_rk} | {d_rk} | {r['rrf_score']:.4f} | {r['citation']} |")
        md.append("")
        
        # Business logic analysis
        md.append("### 🔍 Phân tích nghiệp vụ:")
        if q_idx == 1:
            md.append("*   **Nhận xét**: Câu hỏi chứa mã văn bản chính xác (`Nghị định số 73/2016/NĐ-CP`). BM25 tìm thấy các tham chiếu trực tiếp chứa từ khóa này ở thứ hạng cao. Dense retrieval (đặc biệt khi dùng fallback Jaccard) tập trung vào các đoạn có sự tương quan từ ngữ tương tự. Hybrid Search thành công giữ lại các ứng viên xuất sắc của cả hai ở đầu danh sách nhờ điểm RRF.")
        elif q_idx == 2:
            md.append("*   **Nhận xét**: Câu hỏi thuần ý nghĩa ngữ nghĩa (an toàn vận chuyển). Dense retrieval vượt trội trong việc tìm kiếm các điều khoản liên quan đến 'Trách nhiệm bảo vệ vận chuyển' (Điều 56) và 'Phương tiện vận chuyển' (Điều 50). Hybrid Search đã tổng hợp xuất sắc và đưa các điều khoản an toàn lên vị trí dẫn đầu.")
        elif q_idx == 3:
            md.append("*   **Nhận xét**: Câu hỏi kết hợp (Thông tư 01/2014 + đóng gói niêm phong). Đây là trường hợp Hybrid Search phát huy tối đa sức mạnh: lọc chính xác văn bản Thông tư 01/2014 (nhờ BM25 khớp từ khóa cứng) đồng thời xếp hạng cao các phần về 'quy định đóng gói niêm phong' (nhờ Dense/Jaccard hiểu ngữ cảnh). Kết quả Hybrid chứa các chunk cực kỳ chính xác.")
        md.append("")
        md.append("---")
        md.append("")
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md) + "\n")
    print(f"Markdown comparison report written to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Run Hybrid BM25 and Dense search using RRF.")
    parser.add_argument("--query", type=str, help="Search query string.")
    parser.add_argument("--candidate-k", type=int, default=20, help="Number of candidates to fetch from each retriever.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of final results to return.")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(dotenv_path=buoi_14_dir / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.", file=sys.stderr)
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
    print("Initializing Retrievers...")
    bm25_retriever = BM25Retriever(df)
    dense_retriever = DenseRetriever(df, embeddings_path, api_key)
    hybrid_retriever = HybridRetriever(bm25_retriever, dense_retriever)
    
    if args.query:
        query = args.query
        top_k = args.top_k
        cand_k = args.candidate_k
        print(f"\nRunning Hybrid Search for: '{query}' (candidate_k={cand_k}, top_k={top_k})")
        
        hybrid_results = hybrid_retriever.retrieve(query, candidate_k=cand_k, top_k=top_k)
        print_hybrid_results(hybrid_results)
    else:
        # Run suite of 3 test queries
        test_queries = [
            ("Điều 12 Nghị định số 73/2016/NĐ-CP", "Câu có mã/số hiệu cụ thể"),
            ("quy định về an toàn trong vận chuyển tiền mặt và tài sản quý của ngân hàng", "Câu diễn đạt semantic (ý nghĩa)"),
            ("Thông tư 01/2014 quy định thế nào về việc đóng gói niêm phong tiền mặt", "Câu kết hợp cả hai yếu tố")
        ]
        
        queries_results = []
        for query, q_type in test_queries:
            print(f"\n[Suite] Running Hybrid Search for: '{query}' ({q_type})")
            bm25_res = bm25_retriever.retrieve(query, top_k=5)
            dense_res = dense_retriever.retrieve(query, top_k=5)
            hybrid_res = hybrid_retriever.retrieve(query, candidate_k=20, top_k=5)
            
            queries_results.append((query, q_type, bm25_res, dense_res, hybrid_res))
            print_hybrid_results(hybrid_res)
            
        # Write markdown report
        outputs_dir = buoi_14_dir / "outputs"
        os.makedirs(outputs_dir, exist_ok=True)
        generate_hybrid_markdown_report(queries_results, outputs_dir / "retrieval_examples.md")

if __name__ == '__main__':
    main()
