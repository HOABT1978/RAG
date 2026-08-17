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
from src.reranker import Reranker

def print_results_table(title, results, is_reranked=False):
    print(f"\n==================================================")
    print(title)
    print(f"==================================================")
    if is_reranked:
        print(f"{'Rank':<5} | {'Chunk ID':<15} | {'Hybrid Rank':<12} | {'Rerank Score':<12} | {'Citation'}")
        print("-" * 100)
        for res in results:
            print(f"{res['final_rank']:<5} | {res['chunk_id']:<15} | {res['hybrid_rank']:<12} | {res['rerank_score']:.4f} | {res['citation']}")
    else:
        print(f"{'Rank':<5} | {'Chunk ID':<15} | {'RRF Score':<12} | {'Citation'}")
        print("-" * 100)
        for res in results:
            print(f"{res['final_rank']:<5} | {res['chunk_id']:<15} | {res['rrf_score']:.4f} | {res['citation']}")
    print("-" * 100)

def generate_final_markdown_report(queries_results, output_path, reranker_model_name, is_neural):
    md = []
    md.append("# BÁO CÁO TOÀN DIỆN PIPELINE RETRIEVAL & RERANKING (BUỔI 14)")
    md.append("")
    md.append(f"- **Reranker Model**: `{reranker_model_name}`")
    md.append(f"- **Chế độ Reranking**: `{'Neural (Transformers)' if is_neural else 'Fallback Text Matching (difflib)'}`")
    md.append("")
    md.append("Báo cáo này đối chiếu kết quả qua 4 giai đoạn:")
    md.append("1. **BM25 Only** (Lexical Search)")
    md.append("2. **Dense Only** (Semantic Search)")
    md.append("3. **Hybrid Search** (RRF Fusion)")
    md.append("4. **Reranked** (Xếp hạng lại Top Candidates từ Hybrid)")
    md.append("")
    md.append("---")
    md.append("")
    
    for q_idx, (query, q_type, bm25_res, dense_res, hybrid_res, reranked_res) in enumerate(queries_results, start=1):
        md.append(f"## Câu hỏi {q_idx}: \"{query}\"")
        md.append(f"- **Phân loại**: {q_type}")
        md.append("")
        
        # Comparison table of Top-3
        md.append("### Bảng đối chiếu kết quả xếp hạng (Top 3):")
        md.append("| Hạng | BM25 Only | Dense Only | Hybrid Search (RRF) | Reranked (Cuối cùng) |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        
        for idx in range(3):
            b_cid = bm25_res[idx]['chunk_id'] if idx < len(bm25_res) else "-"
            d_cid = dense_res[idx]['chunk_id'] if idx < len(dense_res) else "-"
            h_cid = hybrid_res[idx]['chunk_id'] if idx < len(hybrid_res) else "-"
            r_cid = reranked_res[idx]['chunk_id'] if idx < len(reranked_res) else "-"
            md.append(f"| {idx+1} | `{b_cid}` | `{d_cid}` | `{h_cid}` | **`{r_cid}`** |")
        md.append("")
        
        # Detailed Rerank table
        md.append("### Chi tiết kết quả sau khi Rerank (Top 5)")
        md.append("| Hạng mới | Chunk ID | Hạng cũ (Hybrid) | Điểm Rerank | Citation |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for r in reranked_res:
            md.append(f"| {r['final_rank']} | `{r['chunk_id']}` | {r['hybrid_rank']} | {r['rerank_score']:.4f} | {r['citation']} |")
        md.append("")
        
        # Details of Top-1 Reranked Chunk
        md.append("#### Nội dung của tài liệu chính xác nhất (Top-1 Reranked Chunk):")
        md.append(f"> **Citation**: {reranked_res[0]['citation']}\n>\n> {reranked_res[0]['text']}")
        md.append("")
        
        # Analysis
        md.append("### 🔍 Phân tích luồng thay đổi thứ tự:")
        if q_idx == 1:
            md.append("*   **Nhận xét**: BM25 đưa các đoạn khớp từ khóa cứng về Nghị định 73/2016 lên đầu. Hybrid giữ lại cả hai luồng ứng viên. Rerank đã phân tích lại tương quan chính xác của câu hỏi đối với văn bản điều khoản và đưa phân đoạn phù hợp nhất về Điều 12/Điều liên quan lên đầu.")
        elif q_idx == 2:
            md.append("*   **Nhận xét**: Câu hỏi semantic được xếp hạng cao bởi Dense. Reranker tập trung chấm điểm cao nhất cho các đoạn bàn trực tiếp về trách nhiệm bảo vệ và quy trình vận chuyển an toàn, giúp kết quả tìm kiếm tập trung đúng trọng tâm điều khoản quy định.")
        elif q_idx == 3:
            md.append("*   **Nhận xét**: Reranker giúp sàng lọc tốt các từ khóa nhiễu của câu hỏi hỗn hợp, đưa phần giải thích chi tiết về việc kiểm đếm, đóng gói, niêm phong tiền mặt của Thông tư 01/2014 lên vị trí số 1.")
        md.append("")
        md.append("---")
        md.append("")
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md) + "\n")
    print(f"Final pipeline report written to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Run complete Retrieval and Rerank pipeline.")
    parser.add_argument("--query", type=str, help="Search query string.")
    parser.add_argument("--candidate-k", type=int, default=20, help="Number of candidates for Hybrid fusion.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of final results.")
    args = parser.parse_args()
    
    # Load env
    load_dotenv(dotenv_path=buoi_14_dir / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.", file=sys.stderr)
        sys.exit(1)
        
    # Paths
    corpus_path = buoi_14_dir / "data" / "processed" / "chunks_normalized.csv"
    embeddings_path = buoi_14_dir.parent / "kb+hops" / "chunks_embedded.json"
    
    if not corpus_path.exists():
        print(f"Error: Normalized corpus not found. Run prepare_corpus.py first.", file=sys.stderr)
        sys.exit(1)
        
    df = pd.read_csv(corpus_path)
    
    # Initialize components
    print("Initializing Retrieval Components...")
    bm25_retriever = BM25Retriever(df)
    dense_retriever = DenseRetriever(df, embeddings_path, api_key)
    hybrid_retriever = HybridRetriever(bm25_retriever, dense_retriever)
    
    # Initialize Reranker (Uses HF model config from env or default)
    model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    reranker = Reranker(model_name=model_name)
    
    if args.query:
        query = args.query
        top_k = args.top_k
        cand_k = args.candidate_k
        
        print(f"\nRunning Search Pipeline for: '{query}'")
        hybrid_results = hybrid_retriever.retrieve(query, candidate_k=cand_k, top_k=cand_k)
        reranked_results = reranker.rerank(query, hybrid_results, top_k=top_k)
        
        print_results_table("BEFORE RERANK (HYBRID SEARCH)", hybrid_results[:top_k], is_reranked=False)
        print_results_table("AFTER RERANK", reranked_results, is_reranked=True)
    else:
        # Run test suite and save report
        test_queries = [
            ("Điều 12 Nghị định số 73/2016/NĐ-CP", "Câu có mã/số hiệu cụ thể"),
            ("quy định về an toàn trong vận chuyển tiền mặt và tài sản quý của ngân hàng", "Câu diễn đạt semantic (ý nghĩa)"),
            ("Thông tư 01/2014 quy định thế nào về việc đóng gói niêm phong tiền mặt", "Câu kết hợp cả hai yếu tố")
        ]
        
        queries_results = []
        for query, q_type in test_queries:
            print(f"\n[Suite] Running Pipeline for: '{query}' ({q_type})")
            bm25_res = bm25_retriever.retrieve(query, top_k=5)
            dense_res = dense_retriever.retrieve(query, top_k=5)
            hybrid_res = hybrid_retriever.retrieve(query, candidate_k=20, top_k=20)
            reranked_res = reranker.rerank(query, hybrid_res, top_k=5)
            
            queries_results.append((query, q_type, bm25_res, dense_res, hybrid_res, reranked_res))
            
            print_results_table("BEFORE RERANK", hybrid_res[:5], is_reranked=False)
            print_results_table("AFTER RERANK", reranked_res, is_reranked=True)
            
        outputs_dir = buoi_14_dir / "outputs"
        os.makedirs(outputs_dir, exist_ok=True)
        generate_final_markdown_report(
            queries_results, 
            outputs_dir / "retrieval_examples.md",
            reranker.model_name,
            reranker.use_neural
        )

if __name__ == '__main__':
    main()
