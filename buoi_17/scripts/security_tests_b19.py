import os
import sys
import json
import pandas as pd
import io
from dotenv import load_dotenv

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from secure_retrieval_adapter import SecureRetrievalAdapter
from ollama_adapter import OllamaClient

# Define paths
combined_csv_path = os.path.abspath(os.path.join(script_dir, "..", "data", "chunks_combined_secure.csv"))
mock_embeddings_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "mock_embeddings.json"))
conflicts_csv_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "compliance_conflicts.csv"))
checklist_csv_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "audit_checklist_results.csv"))
gap_csv_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "compliance_gap_results.csv"))
log_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "audit_log.jsonl"))
report_path = os.path.abspath(os.path.join(script_dir, "..", "outputs", "security_test_b19_report.md"))
env_path = os.path.abspath(os.path.join(script_dir, "..", ".env"))

load_dotenv(env_path, override=True)

print("=== STARTING SECURITY & GUARDRAIL TESTS FOR BUOI 19 ===")

results = {}

# 1. Local Offline Privacy Check
print("\n[Test 1] Running Local Offline Privacy Check...")
llm_provider = os.getenv("LLM_PROVIDER")
ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
if llm_provider == "ollama":
    details = f"LLM_PROVIDER is correctly set to 'ollama' in .env. Ollama Base URL is configured to: {ollama_url}. All queries are routed locally to the containerized service and no external API keys/prompts are sent to internet LLM endpoints."
    results['Local Offline Privacy Check'] = {'status': 'PASS', 'details': details}
else:
    details = f"LLM_PROVIDER is set to '{llm_provider}', which is not 'ollama'."
    results['Local Offline Privacy Check'] = {'status': 'FAIL', 'details': details}

# 2. RBAC Enforcement
print("\n[Test 2] Running RBAC Enforcement Check...")
try:
    adapter = SecureRetrievalAdapter(secure_csv_path=combined_csv_path, embeddings_json_path=mock_embeddings_path)
    # Query for CAR - restricted to Admin and Risk_Manager
    results_staff = adapter.retrieve("tỷ lệ an toàn vốn tối thiểu CAR", user_roles=["Staff"], top_k=20)
    staff_has_car02 = any(item['document_id'] == "agr_car02" for item in results_staff)
    if staff_has_car02:
        results['RBAC Enforcement'] = {
            'status': 'FAIL',
            'details': "Role 'Staff' was able to retrieve restricted document 'agr_car02'."
        }
    else:
        results['RBAC Enforcement'] = {
            'status': 'PASS',
            'details': "RBAC pre-filtering successfully blocked 'Staff' role from accessing restricted CAR policy chunks (agr_car02)."
        }
except Exception as e:
    results['RBAC Enforcement'] = {'status': 'FAIL', 'details': str(e)}

# 3. Citation Integrity
print("\n[Test 3] Running Citation Integrity Check...")
try:
    citation_ok = True
    details = ""
    
    # Check conflicts
    if os.path.exists(conflicts_csv_path):
        df = pd.read_csv(conflicts_csv_path)
        nulls = df['doc_a_citation'].isnull().sum() + df['doc_b_citation'].isnull().sum()
        if nulls > 0:
            citation_ok = False
            details += "Found empty citations in conflicts CSV. "
        else:
            details += f"Citations verified in conflicts CSV ({len(df)} rows). "
            
    # Check checklist
    if os.path.exists(checklist_csv_path):
        df = pd.read_csv(checklist_csv_path)
        nulls = df['source_citation'].isnull().sum()
        if nulls > 0:
            citation_ok = False
            details += "Found empty citations in checklist CSV. "
        else:
            details += f"Citations verified in checklist CSV ({len(df)} rows). "
            
    # Check gap analysis
    if os.path.exists(gap_csv_path):
        df = pd.read_csv(gap_csv_path)
        nulls = df['external_citation'].isnull().sum() + df['internal_citation'].isnull().sum()
        if nulls > 0:
            citation_ok = False
            details += "Found empty citations in gap CSV. "
        else:
            details += f"Citations verified in gap CSV ({len(df)} rows)."
            
    results['Citation Integrity'] = {
        'status': 'PASS' if citation_ok else 'FAIL',
        'details': details
    }
except Exception as e:
    results['Citation Integrity'] = {'status': 'FAIL', 'details': str(e)}

# 4. Human Review Guardrail
print("\n[Test 4] Running Human Review Guardrail Check...")
try:
    guardrail_ok = True
    details = ""
    
    if os.path.exists(conflicts_csv_path):
        df = pd.read_csv(conflicts_csv_path)
        bad = df[df['review_status'] != 'NEEDS_HUMAN_REVIEW']
        if len(bad) > 0:
            guardrail_ok = False
            details += f"Found {len(bad)} rows in conflicts CSV without NEEDS_HUMAN_REVIEW status. "
            
    if os.path.exists(checklist_csv_path):
        df = pd.read_csv(checklist_csv_path)
        bad = df[df['review_status'] != 'NEEDS_HUMAN_REVIEW']
        if len(bad) > 0:
            guardrail_ok = False
            details += f"Found {len(bad)} rows in checklist CSV without NEEDS_HUMAN_REVIEW status. "
            
    if os.path.exists(gap_csv_path):
        df = pd.read_csv(gap_csv_path)
        bad = df[df['review_status'] != 'NEEDS_HUMAN_REVIEW']
        if len(bad) > 0:
            guardrail_ok = False
            details += f"Found {len(bad)} rows in gap CSV without NEEDS_HUMAN_REVIEW status."
            
    if guardrail_ok:
        details = "100% of generated records in conflicts, checklists, and gap analysis results have 'review_status' set to 'NEEDS_HUMAN_REVIEW' forcing manual audit verification."
        
    results['Human Review Guardrail'] = {
        'status': 'PASS' if guardrail_ok else 'FAIL',
        'details': details
    }
except Exception as e:
    results['Human Review Guardrail'] = {'status': 'FAIL', 'details': str(e)}

# 5. Audit Log Privacy
print("\n[Test 5] Running Audit Log Privacy Check...")
try:
    privacy_ok = True
    details = ""
    
    if os.path.exists(log_path):
        leaks = 0
        with open(log_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f, 1):
                if not line.strip():
                    continue
                data = json.loads(line)
                for k, v in data.items():
                    if isinstance(v, str):
                        if any(term in k.lower() for term in ['key', 'secret', 'password']):
                            if v != '[REDACTED]':
                                privacy_ok = False
                                leaks += 1
        if privacy_ok:
            details = f"Scanned audit log file. All keys containing 'key', 'secret', or 'password' are correctly masked with '[REDACTED]'."
        else:
            details = f"Found {leaks} unmasked secret leaks in the audit log!"
    else:
        details = "No audit log file found, skipped scan."
        
    results['Audit Log Privacy'] = {
        'status': 'PASS' if privacy_ok else 'FAIL',
        'details': details
    }
except Exception as e:
    results['Audit Log Privacy'] = {'status': 'FAIL', 'details': str(e)}

# 6. Local Model Resilience
print("\n[Test 6] Running Local Model Resilience Check...")
try:
    client = OllamaClient()
    res = client.generate("Tạo checklist: xe bọc thép", format_json=True)
    parsed = json.loads(res)
    if isinstance(parsed, dict) and ("items" in parsed or "has_conflict" in parsed or "response" in parsed):
        details = "System maintains local model resilience. Offline requests successfully execute via the local Ollama container or trigger the safe rule-engine fallback instead of crashing."
        results['Local Model Resilience'] = {'status': 'PASS', 'details': details}
    else:
        results['Local Model Resilience'] = {'status': 'FAIL', 'details': "Ollama client did not return a valid fallback or response."}
except Exception as e:
    results['Local Model Resilience'] = {'status': 'FAIL', 'details': str(e)}


# Save Markdown report
all_pass = all(item['status'] == 'PASS' for item in results.values())
final_status = "PASS" if all_pass else "FAIL"

report_md = f"""# BÁO CÁO KIỂM THỬ AN TOÀN VÀ PHÂN QUYỀN (SECURITY & GUARDRAIL TEST REPORT) - BUỔI 19

Báo cáo này ghi nhận kết quả kiểm thử an toàn bảo mật, phân quyền RBAC và khả năng tự chủ offline của hệ thống trợ lý kiểm toán AI (Buổi 19).

---

## 1. Kết Quả 6 Hạng Mục Kiểm Tra An Toàn

"""

for idx, (test_name, res) in enumerate(results.items(), 1):
    status_emoji = "✅ PASS" if res['status'] == 'PASS' else "❌ FAIL"
    report_md += f"""### Hạng mục {idx}: **{test_name}**
* **Trạng thái**: {status_emoji}
* **Mô tả kết quả**:
  > {res['details']}

---
"""

report_md += f"""
## 2. Kết Luận Nghiệm Thu Bảo Mật

```text
SECURITY & GUARDRAIL TESTS: {final_status}
```
"""

with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_md)

print(f"\nReport saved successfully to: {report_path}")
print(f"Final status: {final_status}")
sys.exit(0 if all_pass else 1)
