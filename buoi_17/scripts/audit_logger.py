import os
import json
import uuid
from datetime import datetime, timezone

class AuditLogger:
    def __init__(self, log_path=None):
        if log_path is None:
            # relative to this script: ../outputs/audit_log.jsonl
            log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'audit_log.jsonl'))
        self.log_path = log_path
        
        # Ensure outputs directory exists
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
    def log_event(self, user_id_demo, user_role, action, query, retrieval_method, 
                  retrieved_document_ids, retrieved_chunk_ids, citation_ids, 
                  rbac_excluded_count, status, request_id=None):
        
        # Generate UUID request_id if not provided
        if request_id is None:
            request_id = str(uuid.uuid4())
            
        # Get UTC timestamp
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Build audit record supporting multiple naming conventions for safety
        record = {
            'timestamp': timestamp,
            'request_id': request_id,
            'user_id_demo': user_id_demo,
            'user_role': user_role,
            'action': action,
            'query': query,
            'retrieval_method': retrieval_method,
            'retrieval method': retrieval_method,
            'retrieved_document_ids': retrieved_document_ids,
            'retrieved document IDs': retrieved_document_ids,
            'retrieved_chunk_ids': retrieved_chunk_ids,
            'retrieved chunk IDs': retrieved_chunk_ids,
            'citation_ids': citation_ids,
            'citation IDs': citation_ids,
            'rbac_excluded_count': rbac_excluded_count,
            'số candidate bị RBAC loại': rbac_excluded_count,
            'status': status
        }
        
        # Double-check that no secrets are in the record
        # (Passphrases, keys, secrets shouldn't be logged)
        for key, val in record.items():
            if isinstance(val, str):
                # Simple check for apparent secrets in logging fields
                if 'api_key' in key.lower() or 'password' in key.lower() or 'secret' in key.lower():
                    record[key] = '[REDACTED]'
        
        # Append record as a line in the JSONL file
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
        return request_id
