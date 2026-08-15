"""
Streamlit Dashboard - Buổi 12: Knowledge Graph Construction
Trực quan hóa và kiểm soát quy trình chuẩn hóa, trích xuất thực thể, quan hệ và xây dựng Đồ thị Tri thức.
"""

import streamlit as st
import pandas as pd
import json
import time
import os
import re
import subprocess
from pathlib import Path
from neo4j import GraphDatabase

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Knowledge Graph Studio — Buổi 12",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thư mục chứa dữ liệu đầu ra và code
BASE_DIR = Path("d:/Rag_thuchanh/RAG")
NER_KB_DIR = BASE_DIR / "ner_kb"
BUOI_12_DIR = BASE_DIR / "buoi_12"

# Custom CSS cho phong cách tối giản hiện đại (Premium Dark Theme)
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
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-left: 10px;
    }
    
    .badge-success { background-color: rgba(0, 255, 102, 0.15); color: #00ff66; border: 1px solid rgba(0, 255, 102, 0.3); }
    .badge-warning { background-color: rgba(255, 165, 0, 0.15); color: #ffa500; border: 1px solid rgba(255, 165, 0, 0.3); }
    .badge-danger { background-color: rgba(255, 75, 75, 0.15); color: #ff4b4b; border: 1px solid rgba(255, 75, 75, 0.3); }
</style>
""", unsafe_allow_html=True)

# Helper function to run pipeline scripts
def run_pipeline_script(script_name):
    script_path = BUOI_12_DIR / script_name
    python_exe = BASE_DIR / "rag_foundation" / "buoi_05" / ".venv" / "Scripts" / "python.exe"
    
    # Use system python if virtual env python is not found
    if not python_exe.exists():
        python_exe = "python"
        
    try:
        t0 = time.time()
        result = subprocess.run(
            [str(python_exe), "-X", "utf8", str(script_path)],
            cwd=str(BUOI_12_DIR),
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        elapsed = time.time() - t0
        return result.returncode == 0, result.stdout, result.stderr, elapsed
    except Exception as e:
        return False, "", str(e), 0.0

def main():
    st.markdown('<div class="logo-text">Knowledge Graph Studio</div>', unsafe_allow_html=True)
    st.markdown("##### Xây dựng & Quản lý Đồ thị Tri thức Pháp luật (Buổi 12)")
    st.write("---")

    # SIDEBAR: CẤU HÌNH KẾT NỐI
    st.sidebar.markdown("### 🔌 Kết nối Neo4j")
    
    # Đọc cấu hình mặc định từ file .env
    default_uri = "bolt://localhost:7687"
    default_user = "HOABT1978"
    default_pass = "Mquan@2004"
    default_db = "neo4j"
    
    env_path = BUOI_12_DIR / ".env"
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

    # Thử kết nối Neo4j
    driver = None
    neo4j_status = False
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        driver.verify_connectivity()
        st.sidebar.success("✅ Kết nối Neo4j thành công!")
        neo4j_status = True
    except Exception as e:
        st.sidebar.error(f"❌ Neo4j Offline: {e}")
        st.sidebar.info("💡 Vui lòng bật Neo4j Desktop và Start database instance.")

    # TABS CHỨC NĂNG
    tab_dashboard, tab_clean, tab_entity, tab_rel, tab_neo4j = st.tabs([
        "📋 Pipeline Dashboard",
        "🧼 Data Clean & Enrich",
        "🏷️ Entity Normalization",
        "🔗 Relationship Validation",
        "🌲 Neo4j Graph Viewer"
    ])

    # -----------------------------------------------------------------------
    # TAB 1: PIPELINE DASHBOARD
    # -----------------------------------------------------------------------
    with tab_dashboard:
        st.markdown("### 📋 Trạng thái các bước trong đường ống dữ liệu (Pipeline)")
        st.write("Kiểm tra sự tồn tại của các file dữ liệu trung gian và điều khiển chạy các bước xử lý:")
        
        # Danh sách các bước
        steps = [
            {"num": 1, "name": "Làm sạch HTML & Đánh giá dữ liệu", "file": "cleaned_documents.csv", "script": "clean_data.py"},
            {"num": 2, "name": "Trích xuất ứng viên bằng luật (Rule-based)", "file": "relation_candidates.csv", "script": "extract_candidates.py"},
            {"num": 3, "name": "Gemini Entity Extraction & Làm giàu Metadata", "file": "enriched_metadata.csv", "script": "enrich_metadata.py"},
            {"num": 4, "name": "Chuẩn hóa thực thể (Entity Normalization)", "file": "entities.csv", "script": "normalize_entities.py"},
            {"num": 5, "name": "Trích xuất quan hệ (Relationship Extraction)", "file": "relationships_raw.csv", "script": "extract_relationships.py"},
            {"num": 6, "name": "Kiểm chứng quan hệ (Relationship Validation)", "file": "relationships.csv", "script": "validate_relationships.py"},
            {"num": 7, "name": "Neo4j Connection Check", "file": None, "script": "test_neo4j_connection.py"},
            {"num": 8, "name": "Import Đồ thị tri thức vào Neo4j", "file": None, "script": "import_graph.py"}
        ]
        
        # Grid hiển thị trạng thái
        for step in steps:
            col_status, col_desc, col_action = st.columns([1.5, 5, 2.5])
            
            # Kiểm tra trạng thái file
            file_exists = False
            if step["file"]:
                file_path = NER_KB_DIR / step["file"]
                file_exists = file_path.exists()
            elif step["num"] == 7:
                file_exists = neo4j_status
            elif step["num"] == 8:
                # Nếu đã import, ta check xem có document node nào trong Neo4j không
                if neo4j_status:
                    try:
                        with driver.session(database=neo4j_db) as session:
                            res = session.run("MATCH (d:Document) RETURN count(d) AS count").single()
                            file_exists = (res["count"] > 0)
                    except:
                        file_exists = False
            
            with col_status:
                if file_exists:
                    st.markdown("<span class='status-badge badge-success'>PASS</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='status-badge badge-warning'>MISSING / NOT RUN</span>", unsafe_allow_html=True)
                    
            with col_desc:
                st.markdown(f"**Bước {step['num']}: {step['name']}**")
                if step["file"]:
                    st.caption(f"Yêu cầu đầu ra: `{step['file']}`")
                elif step["num"] == 7:
                    st.caption(f"Kiểm tra cổng Bolt {neo4j_uri}")
                elif step["num"] == 8:
                    st.caption("Nạp các nút và quan hệ vào cơ sở dữ liệu")
                    
            with col_action:
                btn_label = f"Chạy Bước {step['num']}"
                if st.button(btn_label, key=f"run_btn_{step['num']}"):
                    with st.spinner(f"Đang thực thi {step['script']}..."):
                        success, stdout, stderr, elapsed = run_pipeline_script(step["script"])
                        if success:
                            st.success(f"✅ Bước {step['num']} hoàn thành thành công trong {elapsed:.2f} giây!")
                            with st.expander("Xem Output ghi nhận:"):
                                st.code(stdout)
                            st.rerun()
                        else:
                            st.error(f"❌ Bước {step['num']} thất bại!")
                            with st.expander("Xem chi tiết lỗi:"):
                                st.code(stderr)
            st.markdown("---")

    # -----------------------------------------------------------------------
    # TAB 2: DATA CLEAN & ENRICH (STEP 1 - 3)
    # -----------------------------------------------------------------------
    with tab_clean:
        st.markdown("### 🧼 Làm sạch dữ liệu và Làm giàu Metadata")
        
        cleaned_file = NER_KB_DIR / "cleaned_documents.csv"
        metadata_file = NER_KB_DIR / "enriched_metadata.csv"
        original_meta_file = NER_KB_DIR / "metadata.csv"
        
        if not cleaned_file.exists():
            st.warning("⚠️ Không tìm thấy cleaned_documents.csv. Vui lòng chạy Bước 1 trước.")
        else:
            df_cleaned = pd.read_csv(cleaned_file)
            df_meta = pd.read_csv(metadata_file) if metadata_file.exists() else pd.read_csv(original_meta_file)
            
            # Bộ chọn tài liệu để kiểm tra
            doc_id = st.selectbox("Chọn mã tài liệu (Document ID):", options=df_cleaned['id'].unique())
            
            doc_meta = df_meta[df_meta['id'] == doc_id].iloc[0]
            doc_clean = df_cleaned[df_cleaned['id'] == doc_id].iloc[0]
            
            col_meta, col_text = st.columns([1, 1])
            
            with col_meta:
                st.markdown("#### 📄 Thông tin Metadata (Sau khi làm giàu):")
                meta_dict = doc_meta.to_dict()
                # Hiển thị đẹp dưới dạng bảng
                df_temp = pd.DataFrame(list(meta_dict.items()), columns=["Thuộc tính", "Giá trị"])
                st.dataframe(df_temp, use_container_width=True, hide_index=True)
                
            with col_text:
                st.markdown("#### 🧼 Văn bản sạch (Cleaned Text):")
                st.text_area("Nội dung văn bản sau khi loại bỏ HTML tags:", value=doc_clean['content_clean'], height=450)

    # -----------------------------------------------------------------------
    # TAB 3: ENTITY NORMALIZATION (STEP 4)
    # -----------------------------------------------------------------------
    with tab_entity:
        st.markdown("### 🏷️ Chuẩn hóa thực thể (Entity Normalization)")
        
        entities_file = NER_KB_DIR / "entities.csv"
        if not entities_file.exists():
            st.warning("⚠️ Không tìm thấy entities.csv. Vui lòng chạy Bước 4 trước.")
        else:
            df_entities = pd.read_csv(entities_file)
            
            # Phân bố thực thể theo nhãn loại
            st.markdown("#### Phân bố loại thực thể:")
            type_counts = df_entities['entity_type'].value_counts()
            
            col_chart, col_table = st.columns([1, 2])
            with col_chart:
                st.bar_chart(type_counts)
                
            with col_table:
                # Bộ lọc theo loại thực thể
                selected_type = st.selectbox("Lọc theo loại thực thể (Entity Type):", options=["Tất cả"] + list(df_entities['entity_type'].unique()))
                search_query = st.text_input("Tìm kiếm tên thực thể:")
                
                df_filtered = df_entities.copy()
                if selected_type != "Tất cả":
                    df_filtered = df_filtered[df_filtered['entity_type'] == selected_type]
                if search_query:
                    df_filtered = df_filtered[df_filtered['canonical_name'].str.contains(search_query, case=False, na=False)]
                    
                st.write(f"Tìm thấy **{len(df_filtered)}** thực thể:")
                st.dataframe(df_filtered, use_container_width=True, hide_index=True)

    # -----------------------------------------------------------------------
    # TAB 4: RELATIONSHIP VALIDATION (STEP 5 - 6)
    # -----------------------------------------------------------------------
    with tab_rel:
        st.markdown("### 🔗 Kiểm chứng quan hệ (Relationship Validation)")
        
        rels_file = NER_KB_DIR / "relationships.csv"
        report_file = NER_KB_DIR / "validation_report.csv"
        
        if not rels_file.exists() or not report_file.exists():
            st.warning("⚠️ Không tìm thấy tệp relationships.csv hoặc validation_report.csv. Vui lòng chạy Bước 6 trước.")
        else:
            df_rels = pd.read_csv(rels_file)
            df_report = pd.read_csv(report_file)
            
            # Thống kê kết quả kiểm chứng
            st.markdown("#### Báo cáo kiểm chứng quan hệ từ validation_report.csv:")
            status_counts = df_report['status'].value_counts()
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Tổng quan hệ kiểm thử", len(df_report))
            col_stat2.metric("Quan hệ Hợp lệ (VALID)", status_counts.get("VALID", 0))
            col_stat3.metric("Quan hệ Bị loại bỏ (INVALID/ERROR)", status_counts.get("INVALID", 0) + status_counts.get("ERROR", 0))
            
            st.write("---")
            
            col_v, col_e = st.columns([1, 1])
            
            with col_v:
                st.markdown("#### ✅ Danh sách quan hệ hợp lệ (Đã đưa vào Neo4j):")
                st.dataframe(df_rels[['source', 'target', 'relationship_type', 'confidence', 'method']], use_container_width=True, hide_index=True)
                
            with col_e:
                st.markdown("#### ❌ Danh sách quan hệ lỗi bị loại bỏ:")
                df_errors = df_report[df_report['status'] != 'VALID']
                st.dataframe(df_errors[['source', 'target', 'relationship_type', 'status', 'reason']], use_container_width=True, hide_index=True)

    # -----------------------------------------------------------------------
    # TAB 5: NEO4J GRAPH VIEWER
    # -----------------------------------------------------------------------
    with tab_neo4j:
        st.markdown("### 🌲 Khám phá Đồ thị Tri thức trên Neo4j")
        
        if not neo4j_status:
            st.info("Trạng thái Neo4j đang offline. Vui lòng kết nối database để xem dữ liệu.")
        else:
            with driver.session(database=neo4j_db) as session:
                st.markdown("#### 📊 Thống kê nhanh các Thực thể đồ thị hiện tại:")
                col_n1, col_n2, col_n3, col_n4, col_n5 = st.columns(5)
                
                doc_c = session.run("MATCH (d:Document) RETURN count(d) AS count").single()["count"]
                cq_c = session.run("MATCH (c:CoQuan) RETURN count(c) AS count").single()["count"]
                nk_c = session.run("MATCH (n:NguoiKy) RETURN count(n) AS count").single()["count"]
                dt_c = session.run("MATCH (d:DoiTuongApDung) RETURN count(d) AS count").single()["count"]
                lv_c = session.run("MATCH (l:LinhVuc) RETURN count(l) AS count").single()["count"]
                
                col_n1.metric("Nút Document", doc_c)
                col_n2.metric("Nút Cơ Quan", cq_c)
                col_n3.metric("Nút Người Ký", nk_c)
                col_n4.metric("Nút Đối Tượng Áp Dụng", dt_c)
                col_n5.metric("Nút Lĩnh Vực", lv_c)
                
            st.markdown("---")
            st.markdown("#### 💻 Thử nghiệm truy vấn Cypher:")
            cypher_q = st.text_area("Nhập mã Cypher truy vấn đồ thị tri thức:", value="MATCH (d:Document)-[r]->(e) RETURN d.id AS `Từ Tài Liệu`, type(r) AS `Mối quan hệ`, labels(e)[0] AS `Nhãn thực thể`, e.name AS `Tên thực thể` LIMIT 15")
            
            if st.button("Truy vấn Đồ thị"):
                with driver.session(database=neo4j_db) as session:
                    try:
                        res = session.run(cypher_q)
                        records = [dict(rec) for rec in res]
                        if records:
                            df_res = pd.DataFrame(records)
                            st.dataframe(df_res, use_container_width=True)
                        else:
                            st.info("Không có kết quả trả về từ truy vấn.")
                    except Exception as e:
                        st.error(f"Lỗi thực thi: {e}")

    if driver:
        driver.close()

if __name__ == "__main__":
    main()
