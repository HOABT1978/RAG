import os
import sys
import json
import io
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Configure stdout/stderr for Vietnamese character support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Resolve paths
script_dir = Path(__file__).resolve().parent
buoi_15_dir = script_dir.parent
secure_csv_path = buoi_15_dir / "data" / "processed" / "chunks_secure.csv"

# Load local environment configuration
load_dotenv(dotenv_path=buoi_15_dir / ".env", override=True)
uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "12345678")
db_name = os.getenv("NEO4J_DATABASE", "neo4j")

# Verify inputs
if not secure_csv_path.exists():
    print(f"Error: secure CSV not found at {secure_csv_path}. Please run assign_security_tags.py first.")
    sys.exit(1)

df = pd.read_csv(secure_csv_path)

# Compute document-level roles (union of roles of its chunks)
doc_roles = {}
for _, row in df.iterrows():
    doc_id = str(row['document_id'])
    roles = json.loads(row['allowed_roles'])
    if doc_id not in doc_roles:
        doc_roles[doc_id] = set()
    doc_roles[doc_id].update(roles)

# Convert sets back to list of strings
doc_roles_list = {k: list(v) for k, v in doc_roles.items()}

print(f"Connecting to Neo4j database '{db_name}' at {uri}...")
driver = None
try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("Connection established successfully!")
except Exception as e:
    # Try fallback to bolt protocol
    if uri.startswith("neo4j://"):
        fallback_uri = uri.replace("neo4j://", "bolt://")
        print(f"Retrying connection with fallback protocol: {fallback_uri}...")
        try:
            driver = GraphDatabase.driver(fallback_uri, auth=(user, password))
            driver.verify_connectivity()
            print("Connected successfully using direct Bolt protocol!")
        except Exception as fe:
            print(f"❌ Connection failed: {fe}")
            sys.exit(1)
    else:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

with driver.session(database=db_name) as session:
    # 1. Update DieuKhoan nodes in batches using UNWIND
    print("\nUpdating DieuKhoan nodes in batches...")
    dieukhoan_unwind_query = """
    UNWIND $batch as row
    MATCH (d:DieuKhoan {id: row.id})
    SET d.allowed_roles = row.allowed_roles,
        d.lab_session = "buoi_15"
    RETURN count(d) as updated
    """
    
    dk_data = [{'id': str(r['chunk_id']), 'allowed_roles': json.loads(r['allowed_roles'])} for _, r in df.iterrows()]
    
    batch_size = 1000
    dk_updated = 0
    for i in range(0, len(dk_data), batch_size):
        batch = dk_data[i:i+batch_size]
        res = session.run(dieukhoan_unwind_query, batch=batch)
        record = res.single()
        if record:
            dk_updated += record['updated']
            
    print(f"-> Successfully updated {dk_updated} DieuKhoan nodes.")

    # 2. Update VanBan nodes in batches using UNWIND
    print("\nUpdating VanBan nodes in batches...")
    vanban_unwind_query = """
    UNWIND $batch as row
    MATCH (v:VanBan {id: row.id})
    SET v.allowed_roles = row.allowed_roles,
        v.lab_session = "buoi_15"
    RETURN count(v) as updated
    """
    
    vb_data = [{'id': doc_id, 'allowed_roles': roles} for doc_id, roles in doc_roles_list.items()]
    res = session.run(vanban_unwind_query, batch=vb_data)
    record = res.single()
    vb_updated = record['updated'] if record else 0
    print(f"-> Successfully updated {vb_updated} VanBan nodes.")

    # 3. Update Connecting relationships to lab_session = "buoi_15"
    print("\nUpdating relationship labels to lab_session='buoi_15'...")
    
    # A. Contains relationship
    session.run("""
    MATCH (v:VanBan {lab_session: 'buoi_15'})-[r:CONTAINS]->(d:DieuKhoan {lab_session: 'buoi_15'})
    SET r.lab_session = 'buoi_15'
    """)
    
    # B. Next relationship
    session.run("""
    MATCH (d1:DieuKhoan {lab_session: 'buoi_15'})-[r:NEXT]->(d2:DieuKhoan {lab_session: 'buoi_15'})
    SET r.lab_session = 'buoi_15'
    """)
    
    # C. Other document relationships (like CAN_CU, SUA_DOI_BO_SUNG, etc.)
    session.run("""
    MATCH (v1:VanBan {lab_session: 'buoi_15'})-[r]->(v2:VanBan {lab_session: 'buoi_15'})
    WHERE type(r) <> 'CONTAINS'
    SET r.lab_session = 'buoi_15'
    """)
    print("-> Successfully updated all connecting relationships to lab_session='buoi_15'.")

    # 4. AUDIT & CHECKS
    print("\n=== KIỂM TRA THÔNG TIN NẠP ĐỒ THỊ BẢO MẬT ===")
    
    # A. Count nodes having allowed_roles
    total_sec_nodes = session.run("""
    MATCH (n)
    WHERE (n:VanBan OR n:DieuKhoan) AND n.allowed_roles IS NOT NULL AND n.lab_session = "buoi_15"
    RETURN count(n) as c
    """).single()['c']
    
    vb_sec = session.run("""
    MATCH (v:VanBan {lab_session: 'buoi_15'})
    WHERE v.allowed_roles IS NOT NULL
    RETURN count(v) as c
    """).single()['c']
    
    dk_sec = session.run("""
    MATCH (d:DieuKhoan {lab_session: 'buoi_15'})
    WHERE d.allowed_roles IS NOT NULL
    RETURN count(d) as c
    """).single()['c']
    
    print(f"Tổng số Node an toàn đã nạp (lab_session='buoi_15'): {total_sec_nodes}")
    print(f" - Số Node VanBan: {vb_sec}")
    print(f" - Số Node DieuKhoan: {dk_sec}")
    
    # B. Fetch one sample document and its chunks to verify relationship and roles
    sample_query = """
    MATCH (v:VanBan {lab_session: 'buoi_15'})-[r:CONTAINS]->(d:DieuKhoan {lab_session: 'buoi_15'})
    RETURN v.id as doc_id, v.so_ky_hieu as skh, v.allowed_roles as doc_roles, 
           d.id as chunk_id, d.allowed_roles as chunk_roles, r.lab_session as rel_session
    LIMIT 3
    """
    res_sample = session.run(sample_query)
    
    print("\n=== THỬ LẤY 3 QUAN HỆ KIỂM THỬ THỰC TẾ ===")
    for record in res_sample:
        print(f"📄 Văn bản: {record['doc_id']} ({record['skh']}) | Quyền Văn bản: {record['doc_roles']}")
        print(f"   -[CONTAINS (session={record['rel_session']})]-> 🧩 Điều khoản: {record['chunk_id']} | Quyền Điều khoản: {record['chunk_roles']}")
        print("-" * 60)

driver.close()
print("\n[SUCCESS] Cập nhật đồ thị bảo mật Neo4j thành công!")
