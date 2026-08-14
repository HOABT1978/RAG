import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Configure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("==================================================")
    print("🔌 BƯỚC 7: KIỂM TRA KẾT NỐI NEO4J")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parents[1]
    env_path = root_dir / "buoi_12" / ".env"
    
    # 1. Đọc cấu hình từ .env
    if not env_path.exists():
        print(f"❌ KHÔNG tìm thấy file .env tại: {env_path}")
        print("Neo4j connection: FAIL")
        sys.exit(1)
        
    load_dotenv(env_path)
    
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    db_name = os.getenv("NEO4J_DATABASE") or "neo4j"
    
    if not uri or not user or not password:
        print("❌ Thiếu thông tin cấu hình Neo4j trong file .env (URI, USER hoặc PASSWORD).")
        print("Neo4j connection: FAIL")
        sys.exit(1)
        
    # 2. Không in password ra màn hình
    print(f"📡 Đang kết nối tới Neo4j URI: {uri}")
    print(f"👤 Username: {user}")
    print(f"📂 Database dự kiến sử dụng: {db_name}")
    
    driver = None
    try:
        # 3. Dùng official neo4j Python driver
        # 4. Mở driver
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # 5. Verify connectivity
        driver.verify_connectivity()
        print("✅ Xác minh kết nối thành công (verify_connectivity PASS).")
        
        # 6. Chạy query đọc đơn giản để xác nhận database hoạt động
        with driver.session(database=db_name) as session:
            result = session.run("RETURN 1 AS test_val")
            record = result.single()
            if record and record["test_val"] == 1:
                print(f"✅ Truy vấn kiểm tra thành công trên database '{db_name}' (RETURN 1 PASS).")
            else:
                raise ValueError("Truy vấn thử nghiệm không trả về kết quả mong muốn.")
                
        # Connection PASS
        print("\n==================================================")
        print("Neo4j connection: PASS")
        print(f"Database đang sử dụng: {db_name}")
        print("==================================================")
        
    except Exception as e:
        print("\n==================================================")
        print("Neo4j connection: FAIL")
        print(f"❌ Gặp lỗi kết nối: {str(e)}")
        print("==================================================")
        if driver:
            try:
                driver.close()
            except:
                pass
        sys.exit(1)
        
    finally:
        # 7. Đóng driver đúng cách
        if driver:
            driver.close()
            print("🔒 Đã đóng driver kết nối Neo4j thành công.")

if __name__ == "__main__":
    main()
