import os
import sys
import io

# Set stdout/stderr to UTF-8 to prevent console printing encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    # 1. Try to import neo4j driver
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("Lỗi: Chưa cài đặt thư viện 'neo4j'. Vui lòng chạy 'pip install neo4j'.")
        sys.exit(1)

    # 2. Load configurations from .env
    env_vars = {}
    env_path = os.path.join(project_dir, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip()
                    
    uri = env_vars.get('NEO4J_URI')
    user = env_vars.get('NEO4J_USER')
    password = env_vars.get('NEO4J_PASSWORD')
    db_name = env_vars.get('NEO4J_DATABASE', 'neo4j')
    
    if not uri or not user or not password:
        print("Lỗi: Thiếu cấu hình Neo4j trong file .env tại buoi_13/.env")
        sys.exit(1)
        
    print(f"Đang kết nối tới Neo4j để kiểm tra dữ liệu ({uri})...")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception as e:
        print(f"Lỗi kết nối Neo4j: {e}")
        sys.exit(1)
        
    # Query database counts
    with driver.session(database=db_name) as session:
        # Count Nodes
        cnt_rui_ro = session.run("MATCH (n:RuiRo) RETURN count(n) AS cnt").single()['cnt']
        cnt_kiem_soat = session.run("MATCH (n:KiemSoat) RETURN count(n) AS cnt").single()['cnt']
        cnt_su_kien = session.run("MATCH (n:SuKienRuiRo) RETURN count(n) AS cnt").single()['cnt']
        
        # Count Edges
        cnt_mitigates = session.run("MATCH ()-[r:MITIGATES]->() RETURN count(r) AS cnt").single()['cnt']
        cnt_observed = session.run("MATCH ()-[r:OBSERVED_AS]->() RETURN count(r) AS cnt").single()['cnt']
        
        print("\n==================================================")
        print("KẾT QUẢ KIỂM TRA DỮ LIỆU THỰC TẾ TRÊN NEO4J")
        print("==================================================")
        print(f"1. Số lượng Node:")
        print(f"   - Rủi ro (:RuiRo) : {cnt_rui_ro} nodes")
        print(f"   - Kiểm soát (:KiemSoat) : {cnt_kiem_soat} nodes")
        print(f"   - Sự kiện rủi ro (:SuKienRuiRo) : {cnt_su_kien} nodes")
        print(f"2. Số lượng Edge:")
        print(f"   - Giảm thiểu ([:MITIGATES]) : {cnt_mitigates} relations")
        print(f"   - Phát sinh dưới dạng ([:OBSERVED_AS]) : {cnt_observed} relations")
        
        total_nodes = cnt_rui_ro + cnt_kiem_soat + cnt_su_kien
        total_edges = cnt_mitigates + cnt_observed
        
        print(f"--------------------------------------------------")
        print(f"-> Tổng cộng: {total_nodes} Nodes và {total_edges} Edges đã sẵn sàng.")
        
        if total_nodes == 34 and total_edges == 22:
            print("=> ĐÁNH GIÁ: DỮ LIỆU ĐÃ ĐƯỢC CHUYỂN ĐẦY ĐỦ & CHÍNH XÁC!")
        else:
            print("=> ĐÁNH GIÁ: DỮ LIỆU CHƯA KHỚP HOẶC THIẾU BẢN GHI.")
            
    driver.close()

if __name__ == '__main__':
    main()
