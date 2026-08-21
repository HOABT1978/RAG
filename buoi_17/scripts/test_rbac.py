import sys
import os
import json
import io
from pathlib import Path

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Add buoi_15 to sys.path to enable imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'buoi_15')))
from src.secure_retriever import SecureRetriever

# Load environment
import dotenv
dotenv.load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))
api_key = os.getenv('GEMINI_API_KEY')

secure_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'buoi_15', 'data', 'processed', 'chunks_secure.csv'))
embeddings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'kb+hops', 'chunks_embedded.json'))

print("Initializing SecureRetriever...")
retriever = SecureRetriever(secure_csv, embeddings_path, api_key)

roles_to_test = [
    ['Admin'],
    ['HR'],
    ['Risk_Manager'],
    ['Staff'],
    ['Guest'],
    ['Unknown']
]

query = 'quy định nhân sự tuyển dụng và hạn mức tín dụng'

print(f"Running test queries for roles on query: '{query}'")

for roles in roles_to_test:
    res = retriever.retrieve(query, user_roles=roles, method='hybrid_rerank', top_k=5)
    print(f"\n=== Roles: {roles} (Returned {len(res)} chunks) ===")
    for item in res:
        print(f" - Chunk: {item['chunk_id']} | Allowed: {item['allowed_roles']} | Cit: {item['citation']}")
