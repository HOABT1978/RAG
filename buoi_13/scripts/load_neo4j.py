import os
import csv
import sys
import io

# Set stdout/stderr to UTF-8 to prevent console printing encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def print_neo4j_instructions():
    print("""
================================================================================
HƯỚNG DẪN CÀI ĐẶT & CHẠY NEO4J (NEO4J SETUP & RUN GUIDE)
================================================================================
Để import dữ liệu Risk Graph vào Neo4j, hãy thực hiện các bước sau:

1. Khởi chạy cơ sở dữ liệu Neo4j bằng Docker:
   docker run --name wiki-risk-neo4j -p 7474:7474 -p 7687:7687 -d -e NEO4J_AUTH=neo4j/password123 neo4j:latest

2. Hoặc khởi chạy thông qua Neo4j Desktop / Neo4j Aura (Cloud).

3. Cài đặt thư viện Python neo4j driver (nếu chưa cài):
   pip install neo4j

4. Cập nhật file `.env` tại thư mục gốc dự án:
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password123
   NEO4J_DATABASE=neo4j

5. Chạy lại script này:
   python buoi_13/scripts/load_neo4j.py
================================================================================
""")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output_dir = os.path.join(project_dir, 'outputs')
    
    # 1. Try to import neo4j driver
    try:
        from neo4j import GraphDatabase
        from neo4j.exceptions import ServiceUnavailable, AuthError
    except ImportError:
        print("Thông báo: Thư viện 'neo4j' chưa được cài đặt trong môi trường Python.")
        print_neo4j_instructions()
        return

    # 2. Load configurations from environment or .env file
    # Simple .env parser to avoid external dependencies like dotenv
    env_vars = {}
    env_path = os.path.join(os.path.dirname(project_dir), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip()
                    
    uri = env_vars.get('NEO4J_URI', os.environ.get('NEO4J_URI'))
    user = env_vars.get('NEO4J_USER', os.environ.get('NEO4J_USER'))
    password = env_vars.get('NEO4J_PASSWORD', os.environ.get('NEO4J_PASSWORD'))
    db_name = env_vars.get('NEO4J_DATABASE', os.environ.get('NEO4J_DATABASE', 'neo4j'))
    
    if not uri or not user or not password:
        print("Thông báo: Thiếu cấu hình kết nối Neo4j trong file .env hoặc biến môi trường.")
        print_neo4j_instructions()
        return
        
    print(f"Đang kết nối tới Neo4j tại địa chỉ {uri}...")
    
    # 3. Connect to Neo4j
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        # Verify connectivity
        driver.verify_connectivity()
    except (ServiceUnavailable, AuthError, Exception) as e:
        print(f"Lỗi: Không thể kết nối tới cơ sở dữ liệu Neo4j.")
        print(f"Chi tiết lỗi: {e}")
        print_neo4j_instructions()
        return
        
    # 4. Load CSV files
    entities_path = os.path.join(output_dir, 'entities.csv')
    relations_path = os.path.join(output_dir, 'relations.csv')
    
    if not os.path.exists(entities_path) or not os.path.exists(relations_path):
        print(f"Lỗi: Không tìm thấy file dữ liệu chuẩn hóa entities.csv hoặc relations.csv tại {output_dir}.")
        driver.close()
        return
        
    entities = []
    with open(entities_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        entities = [dict(row) for row in reader]
        
    relations = []
    with open(relations_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        relations = [dict(row) for row in reader]
        
    # 5. Import entities
    print(f"Bắt đầu nạp {len(entities)} thực thể vào Neo4j...")
    
    query_merge_risk = """
    MERGE (n:RuiRo {id: $id})
    ON CREATE SET n.name = $name, n.description = $description, n.category = $category,
                  n.cause = $cause, n.event = $event, n.impact = $impact,
                  n.inherent_level = $inherent_level, n.residual_level = $residual_level,
                  n.owner_unit_id = $owner_unit_id, n.data_origin = $data_origin,
                  n.verification_status = $verification_status
    ON MATCH SET n.name = $name, n.description = $description, n.category = $category,
                 n.cause = $cause, n.event = $event, n.impact = $impact,
                 n.inherent_level = $inherent_level, n.residual_level = $residual_level,
                 n.owner_unit_id = $owner_unit_id, n.data_origin = $data_origin,
                 n.verification_status = $verification_status
    """
    
    query_merge_control = """
    MERGE (n:KiemSoat {id: $id})
    ON CREATE SET n.name = $name, n.control_type = $control_type, n.frequency = $frequency,
                  n.owner_role_id = $owner_role_id, n.effectiveness = $effectiveness,
                  n.data_origin = $data_origin, n.verification_status = $verification_status
    ON MATCH SET n.name = $name, n.control_type = $control_type, n.frequency = $frequency,
                 n.owner_role_id = $owner_role_id, n.effectiveness = $effectiveness,
                 n.data_origin = $data_origin, n.verification_status = $verification_status
    """
    
    query_merge_event = """
    MERGE (n:SuKienRuiRo {id: $id})
    ON CREATE SET n.name = $name, n.occurred_at = $occurred_at, n.discovered_at = $discovered_at,
                  n.severity = $severity, n.loss_amount_vnd = toInteger($loss_amount_vnd),
                  n.description = $description, n.data_origin = $data_origin,
                  n.verification_status = $verification_status
    ON MATCH SET n.name = $name, n.occurred_at = $occurred_at, n.discovered_at = $discovered_at,
                 n.severity = $severity, n.loss_amount_vnd = toInteger($loss_amount_vnd),
                 n.description = $description, n.data_origin = $data_origin,
                 n.verification_status = $verification_status
    """
    
    node_counts = {"RuiRo": 0, "KiemSoat": 0, "SuKienRuiRo": 0}
    
    with driver.session(database=db_name) as session:
        # Create schema constraints first
        session.run("CREATE CONSTRAINT rui_ro_id IF NOT EXISTS FOR (node:RuiRo) REQUIRE node.id IS UNIQUE")
        session.run("CREATE CONSTRAINT kiem_soat_id IF NOT EXISTS FOR (node:KiemSoat) REQUIRE node.id IS UNIQUE")
        session.run("CREATE CONSTRAINT su_kien_rui_ro_id IF NOT EXISTS FOR (node:SuKienRuiRo) REQUIRE node.id IS UNIQUE")
        
        for ent in entities:
            etype = ent['type']
            if etype == 'RuiRo':
                session.run(query_merge_risk, **ent)
                node_counts["RuiRo"] += 1
            elif etype == 'KiemSoat':
                session.run(query_merge_control, **ent)
                node_counts["KiemSoat"] += 1
            elif etype == 'SuKienRuiRo':
                session.run(query_merge_event, **ent)
                node_counts["SuKienRuiRo"] += 1
                
    print(f"Đã nạp thành công các thực thể:")
    for k, v in node_counts.items():
        print(f"  - {k}: {v}")
        
    # 6. Import relationships
    print(f"Bắt đầu nạp {len(relations)} quan hệ liên kết...")
    
    query_edge_mitigates = """
    MATCH (src:KiemSoat {id: $source_id})
    MATCH (tgt:RuiRo {id: $target_id})
    MERGE (src)-[r:MITIGATES]->(tgt)
    ON CREATE SET r.source = $source, r.evidence_quote = $evidence_quote,
                  r.confidence = toFloat($confidence), r.verification_status = $verification_status,
                  r.data_origin = $data_origin
    ON MATCH SET r.source = $source, r.evidence_quote = $evidence_quote,
                 r.confidence = toFloat($confidence), r.verification_status = $verification_status,
                 r.data_origin = $data_origin
    """
    
    query_edge_observed = """
    MATCH (src:RuiRo {id: $source_id})
    MATCH (tgt:SuKienRuiRo {id: $target_id})
    MERGE (src)-[r:OBSERVED_AS]->(tgt)
    ON CREATE SET r.source = $source, r.evidence_quote = $evidence_quote,
                  r.confidence = toFloat($confidence), r.verification_status = $verification_status,
                  r.data_origin = $data_origin
    ON MATCH SET r.source = $source, r.evidence_quote = $evidence_quote,
                 r.confidence = toFloat($confidence), r.verification_status = $verification_status,
                 r.data_origin = $data_origin
    """
    
    rel_counts = {"MITIGATES": 0, "OBSERVED_AS": 0}
    
    with driver.session(database=db_name) as session:
        for rel in relations:
            rtype = rel['relationship_type']
            if rtype == 'MITIGATES':
                session.run(query_edge_mitigates, **rel)
                rel_counts["MITIGATES"] += 1
            elif rtype == 'OBSERVED_AS':
                session.run(query_edge_observed, **rel)
                rel_counts["OBSERVED_AS"] += 1
                
    print(f"Đã nạp thành công các quan hệ:")
    for k, v in rel_counts.items():
        print(f"  - {k}: {v}")
        
    print("\nNhập dữ liệu vào Neo4j hoàn tất thành công! Đồ thị đã sẵn sàng truy vấn.")
    driver.close()

if __name__ == '__main__':
    main()
