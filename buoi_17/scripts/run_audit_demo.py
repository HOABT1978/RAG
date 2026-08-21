import sys
import os
import json
import io

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Ensure we can import the adapter and logger
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from secure_retrieval_adapter import SecureRetrievalAdapter
from audit_logger import AuditLogger

print("Initializing SecureRetrievalAdapter and AuditLogger...")
adapter = SecureRetrievalAdapter()
logger = AuditLogger()

# Clear existing log file if it exists, to start fresh for the demo
log_file_path = logger.log_path
if os.path.exists(log_file_path):
    os.remove(log_file_path)
    print("Cleaned up old audit log file.")

master_df_len = len(adapter.retriever.df)

print("\n--- RUNNING DEMO REQUEST 1: ALLOWED ---")
# User: hr_user_01 (HR role), querying HR information
user_id_1 = "hr_user_01"
role_1 = ["HR"]
query_1 = "hồ sơ và nhân sự dự kiến bầu Chủ tịch Hội đồng quản trị"
action_1 = "retrieve_hr_policy"
method_1 = "hybrid_rerank"

# Check authorized df len for RBAC count
auth_df_len_1 = len(adapter.retriever.filter_authorized_df(role_1))
rbac_excluded_1 = master_df_len - auth_df_len_1

results_1 = adapter.retrieve(query_1, user_roles=role_1, method=method_1, top_k=3)
doc_ids_1 = list(set(item['document_id'] for item in results_1))
chunk_ids_1 = [item['chunk_id'] for item in results_1]
citations_1 = [item['citation'] for item in results_1]

# Log event
req_id_1 = logger.log_event(
    user_id_demo=user_id_1,
    user_role=role_1,
    action=action_1,
    query=query_1,
    retrieval_method=method_1,
    retrieved_document_ids=doc_ids_1,
    retrieved_chunk_ids=chunk_ids_1,
    citation_ids=citations_1,
    rbac_excluded_count=rbac_excluded_1,
    status="SUCCESS"
)
print(f"Logged Request 1 (ALLOWED) - ID: {req_id_1}, Status: SUCCESS")


print("\n--- RUNNING DEMO REQUEST 2: DENIED ---")
# User: guest_user_01 (Guest role), trying to query protected HR information
# Since they are a Guest, they do not have HR privileges. We return no HR chunks, and log DENIED.
user_id_2 = "guest_user_01"
role_2 = ["Guest"]
query_2 = "hồ sơ nhân sự bổ nhiệm chủ tịch quỹ tín dụng"
action_2 = "retrieve_hr_policy"
method_2 = "hybrid_rerank"

auth_df_len_2 = len(adapter.retriever.filter_authorized_df(role_2))
rbac_excluded_2 = master_df_len - auth_df_len_2

# Retrieve (should not contain HR-only chunks)
results_2 = adapter.retrieve(query_2, user_roles=role_2, method=method_2, top_k=3)
doc_ids_2 = list(set(item['document_id'] for item in results_2))
chunk_ids_2 = [item['chunk_id'] for item in results_2]
citations_2 = [item['citation'] for item in results_2]

# Log event as DENIED because Guest tried to execute an HR action and HR chunks were blocked
req_id_2 = logger.log_event(
    user_id_demo=user_id_2,
    user_role=role_2,
    action=action_2,
    query=query_2,
    retrieval_method=method_2,
    retrieved_document_ids=doc_ids_2,
    retrieved_chunk_ids=chunk_ids_2,
    citation_ids=citations_2,
    rbac_excluded_count=rbac_excluded_2,
    status="DENIED"
)
print(f"Logged Request 2 (DENIED) - ID: {req_id_2}, Status: DENIED")


print("\n--- RUNNING DEMO REQUEST 3: NORMAL ---")
# User: guest_user_02 (Guest role), querying general information (allowed for everyone)
user_id_3 = "guest_user_02"
role_3 = ["Guest"]
query_3 = "tiêu chuẩn doanh nghiệp xếp hạng tín nhiệm độc lập"
action_3 = "retrieve_general_info"
method_3 = "hybrid_rerank"

auth_df_len_3 = len(adapter.retriever.filter_authorized_df(role_3))
rbac_excluded_3 = master_df_len - auth_df_len_3

results_3 = adapter.retrieve(query_3, user_roles=role_3, method=method_3, top_k=3)
doc_ids_3 = list(set(item['document_id'] for item in results_3))
chunk_ids_3 = [item['chunk_id'] for item in results_3]
citations_3 = [item['citation'] for item in results_3]

req_id_3 = logger.log_event(
    user_id_demo=user_id_3,
    user_role=role_3,
    action=action_3,
    query=query_3,
    retrieval_method=method_3,
    retrieved_document_ids=doc_ids_3,
    retrieved_chunk_ids=chunk_ids_3,
    citation_ids=citations_3,
    rbac_excluded_count=rbac_excluded_3,
    status="SUCCESS"
)
print(f"Logged Request 3 (NORMAL) - ID: {req_id_3}, Status: SUCCESS")

print("\nVerify the log file contents:")
with open(log_file_path, 'r', encoding='utf-8') as f:
    for line in f:
        print(line.strip())
