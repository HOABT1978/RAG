import os
import sys

# Ensure import paths are correct
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from secure_retrieval_adapter import SecureRetrievalAdapter

class SecureRetrievalSystem(SecureRetrievalAdapter):
    """
    Standardized wrapper representing the secure retrieval system for Session 17 submission.
    Inherits from the SecureRetrievalAdapter which wraps Session 15's SecureRetriever.
    """
    pass

if __name__ == "__main__":
    combined_csv = os.path.abspath(os.path.join(script_dir, "..", "data", "chunks_combined_secure.csv"))
    mock_embeddings = os.path.abspath(os.path.join(script_dir, "..", "outputs", "mock_embeddings.json"))
    
    retriever = SecureRetrievalSystem(secure_csv_path=combined_csv, embeddings_json_path=mock_embeddings)
    print("Initializing SecureRetrievalSystem...")
    results = retriever.retrieve("tỷ lệ an toàn vốn tối thiểu", user_roles=["Risk_Manager"], top_k=2)
    print(f"Retrieved {len(results)} chunks:")
    for idx, r in enumerate(results, 1):
        print(f"  [{idx}] {r['chunk_id']} | access: {r['access_decision']}")
