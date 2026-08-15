"""
Streamlit Dashboard - Buổi 13: Wiki Risk Graph MVP
Trực quan hóa và kiểm soát quy trình chuẩn hóa, sinh Wiki Markdown và nạp dữ liệu vào Neo4j.
"""

import streamlit as st
import pandas as pd
import json
import time
import os
import re
import sys
import io
import subprocess
from pathlib import Path
from neo4j import GraphDatabase

# Configure page settings
st.set_page_config(
    page_title="Wiki Risk Graph Studio — Buổi 13",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thư mục cơ sở
BASE_DIR = Path("d:/Rag_thuchanh/RAG")
BUOI_13_DIR = BASE_DIR / "buoi_13"
DATA_DIR = BUOI_13_DIR / "data"
OUTPUTS_DIR = BUOI_13_DIR / "outputs"
WIKI_DIR = BUOI_13_DIR / "wiki"
SCRIPTS_DIR = BUOI_13_DIR / "scripts"

# Custom CSS for Premium Design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .logo-text {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ff4b4b, #8a2be2, #00bfff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        margin-left: 10px;
        text-align: center;
    }
    
    .badge-success { background-color: rgba(0, 255, 102, 0.15); color: #00ff66; border: 1px solid rgba(0, 255, 102, 0.3); }
    .badge-warning { background-color: rgba(255, 165, 0, 0.15); color: #ffa500; border: 1px solid rgba(255, 165, 0, 0.3); }
    .badge-danger { background-color: rgba(255, 75, 75, 0.15); color: #ff4b4b; border: 1px solid rgba(255, 75, 75, 0.3); }
    
    .card {
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        background-color: #1e1e24;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to run pipeline scripts using sys.executable
def run_pipeline_script(script_name):
    script_path = SCRIPTS_DIR / script_name
    python_exe = sys.executable  # Runs in the current virtual environment
    
    try:
        t0 = time.time()
        result = subprocess.run(
            [python_exe, "-X", "utf8", str(script_path)],
            cwd=str(BUOI_13_DIR),
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        elapsed = time.time() - t0
        return result.returncode == 0, result.stdout, result.stderr, elapsed
    except Exception as e:
        return False, "", str(e), 0.0

def main():
    st.markdown('<div class="logo-text">Wiki Risk Graph Studio</div>', unsafe_allow_html=True)
    st.markdown("##### Quản lý & Trực quan hóa Đồ thị Rủi ro Đào tạo (Buổi 13)")
    st.write("---")

    # SIDEBAR: CONFIG CONNECTION
    st.sidebar.markdown("### 🔌 Kết nối Neo4j")
    
    # Read default settings from .env
    default_uri = "neo4j://127.0.0.1:7687"
    default_user = "BUOI_13"
    default_pass = "12345678"
    default_db = "neo4j"
    
    env_path = BUOI_13_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "NEO4J_URI": default_uri = v
                    elif k == "NEO4J_USER": default_user = v
                    elif k == "NEO4J_PASSWORD": default_pass = v
                    elif k == "NEO4J_DATABASE": default_db = v

    neo4j_uri = st.sidebar.text_input("Bolt Connection URL", value=default_uri)
    neo4j_user = st.sidebar.text_input("User Name", value=default_user)
    neo4j_password = st.sidebar.text_input("Password", type="password", value=default_pass)
    neo4j_db = st.sidebar.text_input("Database Name", value=default_db)

    # Test Neo4j connection
    driver = None
    neo4j_status = False
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        driver.verify_connectivity()
        st.sidebar.success("✅ Kết nối Neo4j thành công!")
        neo4j_status = True
    except Exception as e:
        st.sidebar.error(f"❌ Neo4j Offline: {e}")
        st.sidebar.info("💡 Vui lòng mở Neo4j Desktop và Start database instance.")

    # FUNCTION TABS
    tab_dashboard, tab_wiki, tab_data, tab_neo4j, tab_seeds = st.tabs([
        "📋 Pipeline Dashboard",
        "📖 Wiki Explorer",
        "📂 Normalized Data View",
        "🌲 Neo4j Cypher Traversal",
        "🌱 Raw Seeds Viewer"
    ])

    # -----------------------------------------------------------------------
    # TAB 1: PIPELINE DASHBOARD
    # -----------------------------------------------------------------------
    with tab_dashboard:
        st.markdown("### 📋 Trạng thái luồng xử lý dữ liệu (Data Pipeline)")
        st.write("Dưới đây là các bước xây dựng hệ thống từ CSV hạt giống đến Đồ thị tri thức:")
        
        steps = [
            {"num": 1, "name": "Kiểm tra Dữ liệu Hạt giống (Inspect Data)", "file": None, "script": "inspect_data.py", "desc": "Kiểm tra dòng, cột, null, trùng lặp và tham chiếu lỗi."},
            {"num": 2, "name": "Chuẩn hóa Thực thể & Quan hệ (Normalize Data)", "file": "entities.csv", "script": "build_entities.py", "desc": "Tạo outputs/entities.csv và outputs/relations.csv."},
            {"num": 3, "name": "Sinh Wiki Markdown Obsidian (Build Wiki)", "file": "wiki/Home.md", "script": "build_wiki.py", "desc": "Tạo các trang markdown wiki liên kết chéo."},
            {"num": 4, "name": "Kiểm thử liên kết chéo Wiki (Validate Wiki)", "file": "wiki_validation_report.md", "script": "validate_wiki.py", "desc": "Quét kiểm thử broken links, orphan pages và sinh báo cáo."},
            {"num": 5, "name": "Nạp dữ liệu vào Đồ thị Neo4j (Load Neo4j)", "file": None, "script": "load_neo4j.py", "desc": "Sử dụng MERGE nạp các Node và Edge vào Neo4j."},
            {"num": 6, "name": "Xác thực số liệu Neo4j thực tế (Verify Neo4j)", "file": None, "script": "verify_neo4j.py", "desc": "Truy vấn database đếm node và edge thực tế."}
        ]
        
        for step in steps:
            col_status, col_desc, col_action = st.columns([1.5, 5, 2.5])
            
            # Check if file/status exists
            exists = False
            if step["num"] == 1:
                exists = True
            elif step["num"] == 2:
                exists = (OUTPUTS_DIR / "entities.csv").exists() and (OUTPUTS_DIR / "relations.csv").exists()
            elif step["num"] == 3:
                exists = (WIKI_DIR / "Home.md").exists()
            elif step["num"] == 4:
                exists = (OUTPUTS_DIR / "wiki_validation_report.md").exists()
            elif step["num"] == 5 or step["num"] == 6:
                if neo4j_status:
                    try:
                        with driver.session(database=neo4j_db) as session:
                            res = session.run("MATCH (n) RETURN count(n) AS cnt").single()
                            exists = (res["cnt"] > 0)
                    except:
                        exists = False
            
            with col_status:
                if exists:
                    st.markdown("<span class='status-badge badge-success'>HOÀN THÀNH</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='status-badge badge-warning'>CHƯA CHẠY</span>", unsafe_allow_html=True)
                    
            with col_desc:
                st.markdown(f"**Bước {step['num']}: {step['name']}**")
                st.caption(step["desc"])
                
            with col_action:
                if st.button(f"Chạy Bước {step['num']}", key=f"run_btn_{step['num']}"):
                    with st.spinner(f"Đang chạy {step['script']}..."):
                        success, stdout, stderr, elapsed = run_pipeline_script(step["script"])
                        if success:
                            st.success(f"✅ Hoàn thành trong {elapsed:.2f} giây!")
                            with st.expander("Xem Output ghi nhận:"):
                                st.code(stdout)
                            st.rerun()
                        else:
                            st.error("❌ Thất bại khi thực thi!")
                            with st.expander("Chi tiết lỗi:"):
                                st.code(stderr)
            st.markdown("---")

    # -----------------------------------------------------------------------
    # TAB 2: WIKI EXPLORER
    # -----------------------------------------------------------------------
    with tab_wiki:
        st.markdown("### 📖 Trình đọc & Khảo sát Wiki Markdown (Obsidian Vault)")
        st.write("Khảo sát các trang tài liệu được sinh tự động:")
        
        if not (WIKI_DIR / "Home.md").exists():
            st.warning("⚠️ Vui lòng chạy Bước 3 (Build Wiki) để tạo dữ liệu Wiki.")
        else:
            col_nav, col_content = st.columns([1, 2])
            
            with col_nav:
                st.markdown("##### 📁 Cấu trúc Wiki")
                
                # List categories
                categories = {
                    "Trang chủ": WIKI_DIR,
                    "Rủi ro (risks)": WIKI_DIR / "risks",
                    "Kiểm soát (controls)": WIKI_DIR / "controls",
                    "Sự kiện (events)": WIKI_DIR / "events"
                }
                
                selected_cat = st.radio("Chọn thư mục:", list(categories.keys()))
                folder_path = categories[selected_cat]
                
                # List files
                files = []
                if folder_path.exists():
                    files = [f.name for f in folder_path.iterdir() if f.is_file() and f.name.endswith(".md")]
                
                selected_file = st.selectbox("Chọn trang tài liệu:", sorted(files))
                
            with col_content:
                if selected_file:
                    file_to_read = folder_path / selected_file
                    st.markdown(f"**📄 Đường dẫn**: `{file_to_read.relative_to(BASE_DIR)}`")
                    st.markdown("---")
                    
                    with open(file_to_read, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                        
                    # Basic parser to make wikilinks readable and clean in Streamlit markdown
                    # Convert [[Link Target]] to bold or link
                    clean_md = re.sub(r'\[\[(.*?)\]\]', r'**\1**', md_content)
                    
                    # Highlight YAML frontmatter
                    if clean_md.startswith("---"):
                        parts = clean_md.split("---", 2)
                        if len(parts) >= 3:
                            st.code(parts[1], language="yaml")
                            st.markdown(parts[2])
                        else:
                            st.markdown(clean_md)
                    else:
                        st.markdown(clean_md)

    # -----------------------------------------------------------------------
    # TAB 3: NORMALIZED DATA VIEW
    # -----------------------------------------------------------------------
    with tab_data:
        st.markdown("### 📂 Thực thể & Quan hệ sau khi Chuẩn hóa")
        
        entities_file = OUTPUTS_DIR / "entities.csv"
        relations_file = OUTPUTS_DIR / "relations.csv"
        
        if not entities_file.exists() or not relations_file.exists():
            st.warning("⚠️ Không tìm thấy file csv chuẩn hóa. Vui lòng chạy Bước 2 trước.")
        else:
            col_ent_view, col_rel_view = st.columns([1, 1])
            
            with col_ent_view:
                st.markdown("##### 🏷️ Bảng `entities.csv`")
                df_ent = pd.read_csv(entities_file)
                
                # Filter by entity type
                ent_types = ["TẤT CẢ"] + list(df_ent["type"].unique())
                sel_ent_type = st.selectbox("Lọc theo loại thực thể:", ent_types)
                
                if sel_ent_type == "TẤT CẢ":
                    st.dataframe(df_ent, hide_index=True)
                else:
                    st.dataframe(df_ent[df_ent["type"] == sel_ent_type], hide_index=True)
                    
            with col_rel_view:
                st.markdown("##### 🔗 Bảng `relations.csv`")
                df_rel = pd.read_csv(relations_file)
                
                # Filter by relationship type
                rel_types = ["TẤT CẢ"] + list(df_rel["relationship_type"].unique())
                sel_rel_type = st.selectbox("Lọc theo loại quan hệ:", rel_types)
                
                if sel_rel_type == "TẤT CẢ":
                    st.dataframe(df_rel, hide_index=True)
                else:
                    st.dataframe(df_rel[df_rel["relationship_type"] == sel_rel_type], hide_index=True)

    # -----------------------------------------------------------------------
    # TAB 4: NEO4J CYPHER TRAVERSAL
    # -----------------------------------------------------------------------
    with tab_neo4j:
        st.markdown("### 🌲 Truy vấn & Duyệt đồ thị rủi ro bằng Cypher")
        
        if not neo4j_status:
            st.warning("⚠️ Không thể kết nối Neo4j. Vui lòng kiểm tra Sidebar và bật Neo4j lên.")
        else:
            # Query selection
            queries = {
                "A. Xem toàn bộ đồ thị (Limit 100)": "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN labels(n)[0] AS type_n, n.id AS id_n, n.name AS name_n, type(r) AS rel, labels(m)[0] AS type_m, m.id AS id_m, m.name AS name_m LIMIT 100",
                "B. Biện pháp kiểm soát giảm thiểu rủi ro RR-001": "MATCH (c:KiemSoat)-[r:MITIGATES]->(risk:RuiRo {id: 'RR-001'}) RETURN c.id AS control_id, c.name AS control_name, r.verification_status AS verification, risk.id AS risk_id, risk.name AS risk_name",
                "C. Các sự kiện thực tế của rủi ro RR-001": "MATCH (risk:RuiRo {id: 'RR-001'})-[r:OBSERVED_AS]->(e:SuKienRuiRo) RETURN risk.id AS risk_id, risk.name AS risk_name, e.id AS event_id, e.occurred_at AS occurred_at, e.loss_amount_vnd AS loss_vnd",
                "D. Truy vết đầy đủ: KiemSoat -> RuiRo -> SuKienRuiRo": "MATCH path = (c:KiemSoat)-[:MITIGATES]->(risk:RuiRo)-[:OBSERVED_AS]->(e:SuKienRuiRo) RETURN c.id AS control_id, c.name AS control_name, risk.id AS risk_id, risk.name AS risk_name, e.id AS event_id, e.severity AS severity",
                "E. Tìm rủi ro trống (không có bất kỳ biện pháp kiểm soát nào)": "MATCH (risk:RuiRo) WHERE NOT (:KiemSoat)-[:MITIGATES]->(risk) RETURN risk.id AS risk_id, risk.name AS risk_name, risk.category AS category",
                "F. Tìm liên kết chưa được xác thực (status <> 'VERIFIED')": "MATCH (source)-[r]->(target) WHERE r.verification_status <> 'VERIFIED' RETURN labels(source)[0] AS src_label, source.id AS src_id, type(r) AS rel_type, target.id AS tgt_id"
            }
            
            sel_q = st.selectbox("Chọn truy vấn phân tích đồ thị mẫu:", list(queries.keys()))
            cypher_query = st.text_area("Mã truy vấn Cypher:", value=queries[sel_q], height=120)
            
            if st.button("Thực thi truy vấn Cypher", type="primary"):
                with st.spinner("Đang chạy truy vấn trên Neo4j..."):
                    try:
                        with driver.session(database=neo4j_db) as session:
                            res = session.run(cypher_query)
                            records = [dict(r) for r in res]
                            
                            if records:
                                df_res = pd.DataFrame(records)
                                st.success(f"✅ Tìm thấy {len(records)} bản ghi!")
                                st.dataframe(df_res, use_container_width=True)
                            else:
                                st.info("ℹ️ Kết quả truy vấn trống (0 bản ghi).")
                    except Exception as ex:
                        st.error(f"❌ Truy vấn bị lỗi: {ex}")

    # -----------------------------------------------------------------------
    # TAB 5: RAW SEEDS VIEWER
    # -----------------------------------------------------------------------
    with tab_seeds:
        st.markdown("### 🌱 Xem Dữ liệu Hạt giống Gốc (Raw CSV Seeds)")
        st.write("Hiển thị nội dung 4 tệp tin CSV hạt giống nguyên bản:")
        
        seed_files = {
            "risk_profiles_seed.csv": DATA_DIR / "risk_profiles_seed.csv",
            "controls_seed.csv": DATA_DIR / "controls_seed.csv",
            "risk_events_seed.csv": DATA_DIR / "risk_events_seed.csv",
            "relationships_seed.csv": DATA_DIR / "relationships_seed.csv"
        }
        
        sel_seed = st.selectbox("Chọn tệp CSV hạt giống:", list(seed_files.keys()))
        seed_path = seed_files[sel_seed]
        
        if seed_path.exists():
            df_seed = pd.read_csv(seed_path)
            st.dataframe(df_seed, hide_index=True)
        else:
            st.error(f"Không tìm thấy file hạt giống tại {seed_path}")

    # Close driver correctly at end of Streamlit run
    if driver:
        driver.close()

if __name__ == '__main__':
    main()
