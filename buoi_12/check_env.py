import os
import sys
from pathlib import Path

# Reconfigure stdout to use UTF-8 for Vietnamese console printing
sys.stdout.reconfigure(encoding='utf-8')

def check_python():
    print("--- 1. Kiểm tra Python & Virtual Environment ---")
    python_ver = sys.version
    print(f"Python Version: {python_ver}")
    
    # Check if inside virtual environment
    # sys.prefix != sys.base_prefix is typical check for venv
    is_venv = sys.prefix != sys.base_prefix or 'VIRTUAL_ENV' in os.environ
    if is_venv:
        print("[PASS] Đang sử dụng Virtual Environment.")
        return True
    else:
        print("[FAIL] KHÔNG sử dụng Virtual Environment.")
        return False

def check_data_files():
    print("\n--- 2. Kiểm tra các file dữ liệu đầu vào ---")
    root_dir = Path(__file__).resolve().parents[1]
    metadata_path = root_dir / "ner_kb" / "metadata.csv"
    content_path = root_dir / "ner_kb" / "content.csv"
    
    pass_all = True
    if metadata_path.exists():
        print(f"[PASS] File metadata.csv tồn tại tại: {metadata_path}")
    else:
        print(f"[FAIL] File metadata.csv KHÔNG tồn tại tại: {metadata_path}")
        pass_all = False
        
    if content_path.exists():
        print(f"[PASS] File content.csv tồn tại tại: {content_path}")
    else:
        print(f"[FAIL] File content.csv KHÔNG tồn tại tại: {content_path}")
        pass_all = False
        
    return pass_all

def check_packages():
    print("\n--- 3. Kiểm tra các package Python ---")
    packages = {
        "pandas": "pandas",
        "beautifulsoup4": "bs4",
        "python-dotenv": "dotenv",
        "google-genai": "google.genai",
        "neo4j": "neo4j"
    }
    
    missing = []
    for pkg_name, import_name in packages.items():
        try:
            __import__(import_name)
            # Try to get version if available
            module = sys.modules.get(import_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"[PASS] Đã import thành công {pkg_name} (phiên bản: {version})")
        except ImportError:
            print(f"[FAIL] KHÔNG THỂ import {pkg_name}")
            missing.append(pkg_name)
            
    return missing

def check_env_file():
    print("\n--- 4. Kiểm tra file cấu hình .env ---")
    current_dir = Path(__file__).resolve().parent
    env_path = current_dir / ".env"
    
    if not env_path.exists():
        print(f"[FAIL] File .env không tồn tại tại: {env_path}")
        return False
        
    print(f"[PASS] File .env tồn tại tại: {env_path}")
    
    # Load env variables
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        
        gemini_key = os.getenv("GEMINI_API_KEY")
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_pass = os.getenv("NEO4J_PASSWORD")
        neo4j_db = os.getenv("NEO4J_DATABASE")
        
        # Check GEMINI_API_KEY
        if gemini_key:
            # Mask API Key to avoid printing secrets
            masked_key = gemini_key[:5] + "..." + gemini_key[-5:] if len(gemini_key) > 10 else "..."
            print(f"[PASS] GEMINI_API_KEY đã được cấu hình (đã che: {masked_key})")
        else:
            print("[FAIL] GEMINI_API_KEY chưa được cấu hình hoặc rỗng.")
            
        # Check Neo4j variables
        if neo4j_uri and neo4j_user and neo4j_pass:
            print(f"[PASS] Cấu hình Neo4j URI: {neo4j_uri}")
            print(f"[PASS] Cấu hình Neo4j User: {neo4j_user}")
            print(f"[PASS] Cấu hình Neo4j Password: (đã ẩn)")
            if neo4j_db:
                print(f"[PASS] Cấu hình Neo4j Database: {neo4j_db}")
            return {
                "uri": neo4j_uri,
                "user": neo4j_user,
                "password": neo4j_pass,
                "database": neo4j_db
            }
        else:
            print("[FAIL] Thiếu cấu hình kết nối Neo4j trong file .env.")
            return False
            
    except Exception as e:
        print(f"[FAIL] Lỗi khi đọc file .env: {str(e)}")
        return False

def check_neo4j_connection(config):
    if not config:
        print("\n--- 5. Kiểm tra kết nối Neo4j ---")
        print("[FAIL] Bỏ qua kiểm tra kết nối vì thiếu cấu hình.")
        return False
        
    print("\n--- 5. Kiểm tra kết nối Neo4j ---")
    try:
        from neo4j import GraphDatabase
        
        print(f"🔌 Đang thử kết nối tới Neo4j tại {config['uri']}...")
        driver = GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"]))
        driver.verify_connectivity()
        print("[PASS] Kết nối tới Neo4j thành công!")
        
        # Test query database
        db_name = config.get("database") or "neo4j"
        with driver.session(database=db_name) as session:
            result = session.run("RETURN 1 AS val")
            record = result.single()
            if record and record["val"] == 1:
                print(f"[PASS] Đã kết nối và truy vấn thành công trên database '{db_name}'.")
            else:
                print(f"[FAIL] Truy vấn test trên database '{db_name}' thất bại.")
                
        driver.close()
        return True
    except Exception as e:
        print(f"[FAIL] Không thể kết nối hoặc truy vấn Neo4j. Chi tiết lỗi: {str(e)}")
        return False

def main():
    print("==================================================")
    print("🔎 BƯỚC 0: KIỂM TRA MÔ TRƯỜNG PROJECT (SESSION 12)")
    print("==================================================")
    
    venv_ok = check_python()
    files_ok = check_data_files()
    missing_pkgs = check_packages()
    env_config = check_env_file()
    
    neo4j_ok = False
    if "neo4j" not in missing_pkgs and env_config:
        neo4j_ok = check_neo4j_connection(env_config)
    else:
        print("\n--- 5. Kiểm tra kết nối Neo4j ---")
        print("[FAIL] Thiếu thư viện neo4j hoặc thiếu cấu hình .env.")
        
    print("\n==================================================")
    print("📊 BÁO CÁO TỔNG HỢP KẾT QUẢ:")
    print("==================================================")
    print(f"1. Virtual Environment:   {'[PASS]' if venv_ok else '[FAIL]'}")
    print(f"2. Input Data Files:      {'[PASS]' if files_ok else '[FAIL]'}")
    print(f"3. Python Packages:       {'[PASS]' if not missing_pkgs else f'[FAIL] (Thiếu: {', '.join(missing_pkgs)})'}")
    print(f"4. File .env Cấu hình:    {'[PASS]' if env_config else '[FAIL]'}")
    print(f"5. Kết nối Neo4j:         {'[PASS]' if neo4j_ok else '[FAIL]'}")
    print("==================================================")
    
    if venv_ok and files_ok and not missing_pkgs and env_config and neo4j_ok:
        print("🎉 CHÚC MỪNG: TẤT CẢ CÁC ĐIỀU KIỆN ĐỀU ĐẠT (PASS)!")
        print("Sẵn sàng thực hiện BƯỚC 1.")
        sys.exit(0)
    else:
        print("⚠️ CẢNH BÁO: Có một số điều kiện chưa đạt (FAIL). Vui lòng khắc phục trước khi đi tiếp.")
        sys.exit(1)

if __name__ == "__main__":
    main()
