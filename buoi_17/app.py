import os
import sys
import json
import csv
import subprocess
import pandas as pd
import streamlit as st
from datetime import datetime
from neo4j import GraphDatabase

# Configure sys.path to import modules if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(script_dir, 'scripts')
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

def clean_citation(citation_str):
    if not isinstance(citation_str, str):
        return citation_str
    clean = citation_str.strip()
    if clean.startswith('[') and clean.endswith(']'):
        clean = clean[1:-1]
    parts = [p.strip() for p in clean.split('|')]
    if len(parts) > 1:
        last = parts[-1].lower()
        if (last.startswith('doc_') or 
            last.startswith('chk_') or 
            last.startswith('chunk_') or 
            'điều_' in last or 
            '_' in last):
            parts = parts[:-1]
    return " | ".join(parts)

# Set Page Config with custom title and icon
st.set_page_config(
    page_title="AI Compliance & Audit System - Agribank",
    page_icon="🛡️",
    layout="wide"
)

# Custom styling for visual excellence
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    /* Main container and font */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Sidebar styling - Light background */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc !important;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] .stMarkdown p {
        color: #1e293b !important;
    }
    
    /* Glassmorphism containers */
    .glass-card {
        background: rgba(15, 23, 42, 0.6);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(5px);
        margin-bottom: 20px;
    }
    
    /* Badge styling */
    .status-badge, .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badges-wrapper {
        display: flex;
        gap: 8px;
    }
    .badge-high { background-color: #7f1d1d; color: #f87171; border: 1px solid #b91c1c; }
    .badge-medium { background-color: #78350f; color: #fbbf24; border: 1px solid #d97706; }
    .badge-low { background-color: #065f46; color: #34d399; border: 1px solid #059669; }
    .badge-review { background-color: #1e3a8a; color: #93c5fd; border: 1px solid #2563eb; }
    
    /* Header styling with gold/red Agribank tones */
    .header-title {
        background: linear-gradient(135deg, #e11d48, #d97706);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.3em;
        margin-bottom: 5px;
    }
    
    /* Banner styling */
    .banner-warning {
        background-color: #450a0a;
        color: #fecaca;
        padding: 12px 20px;
        border-radius: 8px;
        border-left: 5px solid #dc2626;
        font-weight: 600;
        margin-bottom: 25px;
    }
    
    /* Custom buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #b91c1c, #d97706);
        color: white;
        border: none;
        padding: 8px 20px;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Define paths
data_dir = os.path.join(script_dir, 'data')
policy_csv_path = os.path.join(data_dir, 'agribank_internal_policies.csv')
combined_csv_path = os.path.join(data_dir, 'chunks_combined_secure.csv')
conflicts_csv_path = os.path.join(script_dir, 'outputs', 'compliance_conflicts.csv')
conflicts_report_path = os.path.join(script_dir, 'outputs', 'compliance_conflict_report.md')
checklist_csv_path = os.path.join(script_dir, 'outputs', 'audit_checklist_results.csv')
checklist_report_path = os.path.join(script_dir, 'outputs', 'audit_checklist_report.md')
gap_csv_path = os.path.join(script_dir, 'outputs', 'compliance_gap_results.csv')
gap_report_path = os.path.join(script_dir, 'outputs', 'compliance_gap_report.md')
log_path = os.path.join(script_dir, 'outputs', 'audit_log.jsonl')


# ----------------- SIDEBAR: CONFIGURATION & STATUS -----------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/e/e0/Logo_Agribank.svg", width=180)
st.sidebar.markdown("---")
st.sidebar.markdown("<h2 style='color: #d97706; font-size: 1.3em; margin-top:10px;'>⚙️ Cấu hình Hệ thống</h2>", unsafe_allow_html=True)

# Select LLM Provider
llm_provider = st.sidebar.selectbox(
    "Chọn LLM Provider:",
    options=["Ollama", "Gemini"],
    index=0 if os.getenv("LLM_PROVIDER", "ollama").lower() == "ollama" else 1
)

# Set the environment variable dynamically
os.environ["LLM_PROVIDER"] = llm_provider.lower()

# Check if provider has changed, and if so clear cache to force re-init
if "current_provider" not in st.session_state:
    st.session_state.current_provider = llm_provider.lower()
elif st.session_state.current_provider != llm_provider.lower():
    st.session_state.current_provider = llm_provider.lower()
    # Force re-instantiation of internal lookup system
    if 'lookup_system' in st.session_state:
        del st.session_state['lookup_system']

# Check Ollama Server Status
ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
ollama_online = False
try:
    import requests
    # Try the configured URL first
    res = requests.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=1.0)
    if res.status_code == 200:
        ollama_online = True
except Exception:
    # If failed, try localhost fallback in case it's run on host
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=1.0)
        if res.status_code == 200:
            ollama_online = True
    except Exception:
        ollama_online = False

if ollama_online:
    st.sidebar.markdown("🟢 **Trạng thái Ollama Server**: Online")
else:
    st.sidebar.markdown("🔴 **Trạng thái Ollama Server**: Offline")

st.sidebar.markdown("---")
st.sidebar.markdown("<h2 style='color: #d97706; font-size: 1.3em; margin-top:10px;'>🔑 Xác thực người dùng (RBAC)</h2>", unsafe_allow_html=True)

# User ID & Role Inputs
user_id_demo = st.sidebar.text_input("Mã kiểm toán viên (User ID):", value="auditor_compliance")
user_role = st.sidebar.selectbox(
    "Vai trò nghiệp vụ (User Role):",
    options=["Admin", "Risk_Manager", "KiemToanVien", "Staff"],
    index=1  # Default to Risk_Manager
)

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #9ca3af; font-size: 1em;'>🌐 Trạng thái Dữ liệu Hệ thống</h3>", unsafe_allow_html=True)

# 1. Neo4j Status check
neo4j_uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
neo4j_user = os.getenv("NEO4J_USER", "BUOI_15")
neo4j_password = os.getenv("NEO4J_PASSWORD", "12345678")

neo4j_connected = False
try:
    with GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password)) as driver:
        driver.verify_connectivity()
    neo4j_connected = True
except Exception:
    neo4j_connected = False

if neo4j_connected:
    st.sidebar.markdown("🟢 **Cơ sở dữ liệu Neo4j**: Online")
else:
    st.sidebar.markdown("🔴 **Cơ sở dữ liệu Neo4j**: Offline")

# 2. Internal CSV file check
internal_csv_exists = os.path.exists(policy_csv_path)
if internal_csv_exists:
    st.sidebar.markdown("🟢 **Dữ liệu chính sách nội bộ**: Sẵn sàng")
else:
    st.sidebar.markdown("🔴 **Dữ liệu chính sách nội bộ**: Thiếu")

# 3. Combined CSV check
combined_csv_exists = os.path.exists(combined_csv_path)
if combined_csv_exists:
    st.sidebar.markdown("🟢 **Dữ liệu kết hợp (Combined)**: Sẵn sàng")
else:
    st.sidebar.markdown("🔴 **Dữ liệu kết hợp (Combined)**: Thiếu")

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #9ca3af; font-size: 1em;'>⚙️ Quản trị phiên</h3>", unsafe_allow_html=True)

# Reset Session
if st.sidebar.button("🔄 Làm mới phiên (Reset Session)", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# Clean Audit Log
if st.sidebar.button("🧹 Xóa vết nhật ký (Clean Log)", use_container_width=True):
    if os.path.exists(log_path):
        try:
            open(log_path, 'w', encoding='utf-8').close()
            st.sidebar.success("Đã làm sạch nhật ký kiểm toán!")
        except Exception as e:
            st.sidebar.error(f"Lỗi: {e}")
    else:
        st.sidebar.info("Không có tệp nhật ký để xóa.")

# ----------------- MAIN TITLE & DISCLAIMER BANNER -----------------
st.markdown("<h1 class='header-title'>🛡️ AGRIBANK LOCAL AI SYSTEM - RAG BẢO MẬT & KIỂM TOÁN</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #9ca3af; font-size:1.1em; font-weight:600;'>Hệ thống: {os.getenv('APP_ENV', 'training').upper()} | Vai trò: {user_role} | Provider: {llm_provider.upper()}</p>", unsafe_allow_html=True)

st.markdown("""
<div class='banner-warning'>
    ⚠️ KHUYẾN CÁO CỦA HỘI ĐỒNG KIỂM TOÁN: Đây là demo sản phẩm trợ lý AI Kiểm toán — Kết quả phân tích mâu thuẫn và gợi ý checklist bắt buộc phải được Kiểm toán viên chuyên trách xác minh và duyệt lại trước khi ban hành chính thức.
</div>
""", unsafe_allow_html=True)

# Helper to map gap domains in UC2
def get_gap_domain(doc_id):
    if not isinstance(doc_id, str):
        return "Khác"
    doc_id = doc_id.lower()
    if 'car' in doc_id:
        return "CAR & Rủi ro"
    elif 'at' in doc_id:
        return "An toàn kho quỹ"
    elif 'td' in doc_id:
        return "Tín dụng"
    elif 'hr' in doc_id:
        return "Nhân sự"
    elif 'bh' in doc_id:
        return "Bảo hiểm"
    elif 'it' in doc_id:
        return "CNTT & AI"
    return "Khác"

# ----------------- TABS CREATION -----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 UC1 — TRA CỨU QUY ĐỊNH",
    "⚖️ UC2 — COMPLIANCE GAP ANALYSIS",
    "🛡️ UC3 — AI COMPLIANCE CHECKER",
    "📋 UC4 — AI AUDIT CHECKLIST GENERATOR",
    "📜 AUDIT LOG & SYSTEM TRAIL"
])

# ================= TAB 1: UC1 — INTERNAL LOOKUP =================
with tab1:
    st.markdown("### Tra cứu quy định nội bộ (Internal Lookup)")
    st.markdown("Hệ thống tra cứu quy định nội bộ Agribank có lọc phân quyền RBAC và trích dẫn tài liệu gốc.")
    
    # Lazy initialize the lookup system
    if 'lookup_system' not in st.session_state:
        try:
            from scripts.internal_lookup import InternalLookupSystem
            st.session_state.lookup_system = InternalLookupSystem()
        except Exception as e:
            st.error(f"Không thể khởi tạo động cơ tra cứu: {e}")
            
    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        question = st.text_input("Nhập câu hỏi cần tra cứu:", value="Hồ sơ đề nghị cấp Giấy phép lần đầu của quỹ tín dụng nhân dân cần danh sách nhân sự dự kiến bầu, bổ nhiệm gồm những ai?", key="uc1_question")
    with q_col2:
        top_k = st.slider("Số lượng tài liệu trích xuất (Top-K):", min_value=1, max_value=10, value=5, step=1)
        
    if st.button("🚀 Thực hiện Tra cứu", use_container_width=True):
        if not question.strip():
            st.warning("Vui lòng nhập câu hỏi!")
        else:
            with st.spinner("Đang tra cứu cơ sở dữ liệu quy định và tổng hợp câu trả lời..."):
                if 'lookup_system' in st.session_state and st.session_state.lookup_system:
                    try:
                        res = st.session_state.lookup_system.lookup(
                            question=question,
                            user_role=user_role,
                            user_id=user_id_demo,
                            top_k=top_k
                        )
                        st.session_state.uc1_result = res
                        st.success("Hoàn thành tra cứu!")
                    except Exception as e:
                        st.error(f"Lỗi khi tra cứu: {e}")
                else:
                    st.error("Động cơ tra cứu chưa được khởi tạo thành công.")
                    
    # Display lookup result
    if 'uc1_result' in st.session_state:
        res = st.session_state.uc1_result
        st.markdown("---")
        st.markdown("#### Kết quả trả về:")
        
        # Display response
        st.info(res['answer'])
        
        # Access Scope & Request ID
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(f"**Phạm vi truy cập (Access Scope):** `{res['access_scope']}`")
        with col_meta2:
            st.markdown(f"**Mã kiểm toán (Request ID):** `{res['request_id']}`")
            
        # Display Citations in Expander
        if res.get('citations'):
            with st.expander("📖 Xem tài liệu tham chiếu (Citations)"):
                for cite in res['citations']:
                    st.markdown(f"- `{clean_citation(cite)}`")
                    
        # Display Chunk IDs in Expander
        if res.get('document_id/chunk_id'):
            with st.expander("🔗 Xem mã phân đoạn (Document/Chunk IDs)"):
                for dc in res['document_id/chunk_id']:
                    st.markdown(f"- `{dc}`")

# ================= TAB 2: UC2 — COMPLIANCE GAP ANALYSIS =================
with tab2:
    st.markdown("### Phân tích chênh lệch tuân thủ (Compliance Gap Analysis)")
    st.markdown("Phát hiện khoảng trống và sự chênh lệch giữa quy định của Ngân hàng Nhà nước và quy trình nội bộ Agribank.")
    
    col_gap1, col_gap2 = st.columns([3, 1])
    with col_gap1:
        gap_domain_filter = st.selectbox(
            "Lọc theo Miền nghiệp vụ (Gap):",
            options=["Tất cả", "An toàn kho quỹ", "CAR & Rủi ro", "Tín dụng", "Bảo hiểm", "CNTT & AI"]
        )
    with col_gap2:
        gap_class_filter = st.selectbox(
            "Lọc theo Phân loại tuân thủ:",
            options=["Tất cả", "DAP_UNG", "THIEU", "CHENH_LECH", "CHUA_DU_BANG_CHUNG"]
        )
        
    if st.button("⚖️ Chạy Phân Tích Chênh Lệch Tuân Thủ (Toàn bộ)", use_container_width=True):
        with st.spinner("Động cơ Compliance Gap đang thực hiện đối chiếu quy định..."):
            try:
                # Call compliance gap python script
                py_exec = sys.executable
                script_path = os.path.join(scripts_dir, 'compliance_gap.py')
                res = subprocess.run([py_exec, script_path], capture_output=True, text=True, encoding='utf-8')
                if res.returncode == 0:
                    st.success("Hoàn thành phân tích chênh lệch tuân thủ!")
                else:
                    st.error(f"Lỗi khi thực thi: {res.stderr}")
            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")
                
    st.markdown("---")
    st.markdown("#### Bảng kết quả phân tích chênh lệch:")
    
    if not os.path.exists(gap_csv_path):
        st.warning("⚠️ Chưa có dữ liệu chênh lệch tuân thủ. Vui lòng bấm nút 'Chạy Phân Tích Chênh Lệch Tuân Thủ' ở trên.")
    else:
        df_gap = pd.read_csv(gap_csv_path)
        
        # Apply filters
        df_gap['inferred_domain'] = df_gap['internal_document_id'].apply(get_gap_domain)
        if gap_domain_filter != "Tất cả":
            df_gap = df_gap[df_gap['inferred_domain'] == gap_domain_filter]
        if gap_class_filter != "Tất cả":
            df_gap = df_gap[df_gap['classification'] == gap_class_filter]
            
        if df_gap.empty:
            st.info("Không phát hiện chênh lệch tuân thủ nào phù hợp với bộ lọc hiện tại.")
        else:
            # Action: Download Buttons
            col_gap_d1, col_gap_d2 = st.columns([1, 4])
            with col_gap_d1:
                # Download CSV
                gap_csv_data = df_gap.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Tải Gap CSV",
                    data=gap_csv_data,
                    file_name="compliance_gap_results.csv",
                    mime="text/csv",
                    key="download_gap_csv",
                    use_container_width=True
                )
            with col_gap_d2:
                # Download Markdown report if exists
                if os.path.exists(gap_report_path):
                    with open(gap_report_path, 'r', encoding='utf-8') as f:
                        gap_md_data = f.read()
                    st.download_button(
                        label="📥 Tải báo cáo phân tích đầy đủ (Markdown)",
                        data=gap_md_data.encode('utf-8'),
                        file_name="compliance_gap_report.md",
                        mime="text/markdown",
                        key="download_gap_md"
                    )
                    
            # Render each gap finding in a container
            for idx, row in df_gap.iterrows():
                with st.container(border=True):
                    g_col1, g_col2 = st.columns([3, 1])
                    with g_col1:
                        st.subheader(f"⚖️ Phát hiện: {row['gap_id']}")
                    with g_col2:
                        cls = str(row['classification']).upper()
                        if cls == 'DAP_UNG':
                            st.success("🟢 ĐÁP ỨNG")
                        elif cls == 'THIEU':
                            st.error("🔴 THIẾU")
                        elif cls == 'CHENH_LECH':
                            st.warning("🟡 CHÊNH LỆCH")
                        else:
                            st.info("⚪ CHƯA ĐỦ BẰNG CHỨNG")
                            
                    st.markdown(f"**Miền nghiệp vụ:** `{row['inferred_domain']}` | **Độ tin cậy:** `{row['confidence']:.2f}` | **Trạng thái:** `{row['review_status']}`")
                    st.divider()
                    
                    # Columns External & Internal for comparison
                    col_ext, col_int = st.columns(2)
                    with col_ext:
                        st.markdown(f"🛑 **Quy định pháp lý / NHNN**: `{row['external_document_id']}`")
                        st.caption(f"Trích dẫn: {clean_citation(row['external_citation'])}")
                        st.markdown(f"*{row['external_requirement']}*")
                        
                    with col_int:
                        st.markdown(f"🟢 **Quy trình nội bộ Agribank**: `{row['internal_document_id']}`")
                        st.caption(f"Trích dẫn: {clean_citation(row['internal_citation']) if isinstance(row['internal_citation'], str) else 'N/A'}")
                        st.markdown(f"*{row['internal_evidence'] if isinstance(row['internal_evidence'], str) else 'Chưa có quy định nội bộ.'}*")
                        
                    st.divider()
                    
                    # AI Analysis Box
                    st.markdown("💡 **Phân tích chi tiết chênh lệch:**")
                    st.info(row['reason'])
                    st.caption(f"Request ID: `{row['request_id']}`")

# ================= TAB 3: UC3 — AI COMPLIANCE CHECKER =================
with tab3:
    st.markdown("### Kiểm tra mâu thuẫn & So sánh chéo quy định")
    st.markdown("Đối chiếu các Quy định/Quy chế nội bộ Agribank với nhau hoặc với các Thông tư của Ngân hàng Nhà nước.")
    
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        domain_filter = st.selectbox(
            "Chọn Miền nghiệp vụ cần đối chiếu:",
            options=["Tất cả", "An toàn kho quỹ", "CAR & Rủi ro", "Tín dụng", "Bảo hiểm", "CNTT & AI", "Nhân sự", "Tài chính mua sắm", "Xử lý nợ"]
        )
    with col_f2:
        doc_filter = st.selectbox(
            "Hoặc chọn Văn bản nội bộ cụ thể:",
            options=["Tất cả", "agr_at01", "agr_car02", "agr_td03", "agr_fx04", "agr_gp05", "agr_bh06", "agr_it07", "agr_hr08", "agr_tc09", "agr_xln10"]
        )
        
    if st.button("🚀 Chạy đối chiếu & Phát hiện Xung đột", use_container_width=True):
        with st.spinner("Động cơ AI Compliance đang thực hiện so sánh chéo..."):
            try:
                # Call compliance checker python script
                py_exec = sys.executable
                script_path = os.path.join(scripts_dir, 'compliance_checker.py')
                res = subprocess.run([py_exec, script_path], capture_output=True, text=True, encoding='utf-8')
                if res.returncode == 0:
                    st.success("Hoàn thành phân tích chênh lệch tuân thủ!")
                else:
                    st.error(f"Lỗi khi thực thi: {res.stderr}")
            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")
                
    st.markdown("---")
    st.markdown("#### Kết quả phân tích mâu thuẫn thực tế:")
    
    if not os.path.exists(conflicts_csv_path):
        st.warning("⚠️ Chưa có dữ liệu mâu thuẫn. Vui lòng bấm nút 'Chạy đối chiếu & Phát hiện Xung đột' ở trên.")
    else:
        df_conf = pd.read_csv(conflicts_csv_path)
        
        # Apply filters
        if domain_filter != "Tất cả":
            df_conf = df_conf[df_conf['domain'] == domain_filter]
        if doc_filter != "Tất cả":
            df_conf = df_conf[(df_conf['doc_a_id'] == doc_filter) | (df_conf['doc_b_id'] == doc_filter)]
            
        if df_conf.empty:
            st.info("Không phát hiện mâu thuẫn hay điểm chênh lệch nào phù hợp với bộ lọc hiện tại.")
        else:
            # Action: Download Buttons
            col_d1, col_d2 = st.columns([1, 4])
            with col_d1:
                # Download CSV
                csv_data = df_conf.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Tải CSV",
                    data=csv_data,
                    file_name="compliance_conflicts.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_d2:
                # Download Markdown report if exists
                if os.path.exists(conflicts_report_path):
                    with open(conflicts_report_path, 'r', encoding='utf-8') as f:
                        md_data = f.read()
                    st.download_button(
                        label="📥 Tải báo cáo kiểm tra đầy đủ (Markdown)",
                        data=md_data.encode('utf-8'),
                        file_name="compliance_conflict_report.md",
                        mime="text/markdown"
                    )
            
            # Render each conflict in a card
            # Render each conflict in a native Streamlit card (prevents raw HTML rendering bugs)
            for idx, row in df_conf.iterrows():
                with st.container(border=True):
                    # Title and Badges
                    c_col1, c_col2 = st.columns([3, 1])
                    with c_col1:
                        st.subheader(f"🛡️ Mã xung đột: {row['conflict_id']}")
                    with c_col2:
                        sev = str(row['severity']).upper()
                        if sev == 'HIGH':
                            st.error("🚨 Severity: HIGH")
                        elif sev == 'MEDIUM':
                            st.warning("⚠️ Severity: MEDIUM")
                        else:
                            st.info("ℹ️ Severity: LOW")
                            
                    st.markdown(f"**Miền nghiệp vụ:** `{row['domain']}` | **Loại mâu thuẫn:** `{row['conflict_type']}` | **Trạng thái:** `{row['review_status']}`")
                    st.divider()
                    
                    # Columns A & B for policy comparison
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"🟢 **Văn bản nội bộ (A)**: `{row['doc_a_id']}`")
                        st.caption(f"Trích dẫn: {clean_citation(row['doc_a_citation'])}")
                        st.markdown(f"*{row['doc_a_text']}*")
                        
                    with col_b:
                        st.markdown(f"🔴 **Quy định pháp lý / SBV (B)**: `{row['doc_b_id']}`")
                        st.caption(f"Trích dẫn: {clean_citation(row['doc_b_citation'])}")
                        st.markdown(f"*{row['doc_b_text']}*")
                        
                    st.divider()
                    
                    # AI Analysis Box
                    st.markdown("💡 **Phân tích của Trợ lý AI Compliance:**")
                    st.info(row['description'])

# ================= TAB 4: UC4 — AI AUDIT CHECKLIST GENERATOR =================
with tab4:
    st.markdown("### Thiết lập Checklist Kiểm toán bằng AI")
    st.markdown("Chọn phạm vi miền nghiệp vụ và cấp độ chi nhánh để AI trích xuất các câu hỏi kiểm soát bắt buộc dựa trên văn bản gốc.")
    
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        selected_domain = st.selectbox(
            "Chọn Miền nghiệp vụ kiểm toán:",
            options=["An toàn Kho quỹ", "Bảo mật CNTT & AI", "Phán quyết Tín dụng", "Quản lý CAR"]
        )
    with col_c2:
        selected_unit = st.selectbox(
            "Chọn Phạm vi Đơn vị (Unit Scope):",
            options=["Chi nhánh & Phòng giao dịch", "Chi nhánh", "Khối CNTT & AI", "Phòng Kế toán"]
        )
        
    if st.button("📋 Tạo Checklist Kiểm Toán", use_container_width=True):
        with st.spinner("Động cơ AI Audit đang phân tích và sinh danh sách checklist kiểm soát..."):
            try:
                # Call audit checklist generator python script
                py_exec = sys.executable
                script_path = os.path.join(scripts_dir, 'audit_checklist_gen.py')
                res = subprocess.run([py_exec, script_path], capture_output=True, text=True, encoding='utf-8')
                if res.returncode == 0:
                    st.success("Tạo thành công checklist kiểm toán!")
                else:
                    st.error(f"Lỗi khi thực thi: {res.stderr}")
            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")
                
    st.markdown("---")
    st.markdown("#### Bảng Checklist Kiểm toán đề xuất:")
    
    if not os.path.exists(checklist_csv_path):
        st.warning("⚠️ Chưa có dữ liệu checklist. Vui lòng bấm nút 'Tạo Checklist Kiểm Toán' ở trên.")
    else:
        df_check = pd.read_csv(checklist_csv_path)
        
        # Filter checklist by user selections
        # Map selections to match CSV fields
        filtered_check = df_check[df_check['domain'] == selected_domain]
        if not filtered_check.empty:
            # We can filter on unit scope if required, or keep it wide
            pass
        else:
            filtered_check = df_check.copy()  # Fallback to all if selected domain is not generated
            
        if filtered_check.empty:
            st.info("Không tìm thấy đầu mục checklist nào phù hợp.")
        else:
            # Download Buttons
            col_dl1, col_dl2 = st.columns([1, 4])
            with col_dl1:
                # CSV
                csv_data_check = filtered_check.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Tải Checklist (CSV)",
                    data=csv_data_check,
                    file_name="audit_checklist.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_dl2:
                # JSON
                json_data_check = filtered_check.to_json(orient='records', force_ascii=False, indent=4)
                st.download_button(
                    label="📥 Tải Checklist (JSON)",
                    data=json_data_check.encode('utf-8'),
                    file_name="audit_checklist.json",
                    mime="application/json"
                )
            
            # Interactive Grid rendering for popup preservation
            st.write("")
            
            # Render checklist table
            for idx, row in filtered_check.iterrows():
                risk = str(row['risk_level']).upper()
                if risk == 'HIGH':
                    risk_badge = "🔴 HIGH"
                elif risk == 'MEDIUM':
                    risk_badge = "🟡 MEDIUM"
                else:
                    risk_badge = "🟢 LOW"
                    
                col_stt, col_quest, col_risk, col_cite = st.columns([0.5, 4, 3, 2.5])
                
                with col_stt:
                    st.markdown(f"**{idx+1}**")
                with col_quest:
                    st.write(row['audit_question'])
                with col_risk:
                    st.write(f"**Rủi ro**: {row['risk_description']}")
                    st.write(f"Cấp độ: {risk_badge}")
                with col_cite:
                    # Popover for details / Citations (Streamlit 1.31+)
                    with st.popover("📖 Xem nguồn gốc"):
                        st.markdown(f"**Trích dẫn nguồn gốc:**\n{clean_citation(row['source_citation'])}")
                        st.markdown(f"**Trạng thái kiểm duyệt:**\n🚨 {row['review_status']}")
                        st.markdown(f"**Mã checklist**: {row['item_id']}")
                        
                st.markdown("<hr style='margin: 10px 0; border: 0; border-top: 1px solid rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

# ================= TAB 5: AUDIT LOG & SYSTEM TRAIL =================
with tab5:
    st.markdown("### Lịch sử vết ghi nhận hệ thống (Audit Trail & Logging)")
    st.markdown("Tất cả các hành động của kiểm toán viên và động cơ AI Compliance/Audit đều được ghi vết bảo mật.")
    
    if not os.path.exists(log_path):
        st.warning("⚠️ Chưa có tệp nhật ký `audit_log.jsonl`. Vui lòng chạy các tính năng đối chiếu để tạo lịch sử.")
    else:
        audit_events = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        audit_events.append(json.loads(line.strip()))
                    except Exception:
                        pass
                        
        # Extract unique actions and roles for filter options
        unique_actions = list(set([ev.get('action', 'UNKNOWN') for ev in audit_events]))
        
        roles_set = set()
        for ev in audit_events:
            val = ev.get('user_role', 'Guest')
            if isinstance(val, list):
                for r in val:
                    roles_set.add(str(r))
            elif isinstance(val, str):
                if val.startswith('[') and val.endswith(']'):
                    try:
                        parsed = json.loads(val)
                        if isinstance(parsed, list):
                            for r in parsed:
                                roles_set.add(str(r))
                        else:
                            roles_set.add(str(parsed))
                    except Exception:
                        roles_set.add(val)
                else:
                    roles_set.add(val)
            else:
                roles_set.add(str(val))
        unique_roles = list(roles_set)
        
        col_lf1, col_lf2 = st.columns([1, 1])
        with col_lf1:
            log_action_filter = st.selectbox("Lọc theo Hành động (Action):", options=["Tất cả"] + unique_actions)
        with col_lf2:
            log_role_filter = st.selectbox("Lọc theo Vai trò (User Role):", options=["Tất cả"] + unique_roles)
            
        # Apply filters & RBAC safety (Admin can see all, others can only see events with their own role)
        filtered_events = []
        for ev in audit_events:
            # Check RBAC permission to view log
            log_roles = ev.get('user_role', [])
            if isinstance(log_roles, str):
                try:
                    log_roles = json.loads(log_roles)
                except Exception:
                    log_roles = [log_roles]
            
            # Admin can view all. Non-admin can only view logs matching their own role.
            rbac_allowed = (user_role == "Admin" or any(r == user_role for r in log_roles))
            if not rbac_allowed:
                continue
                
            # Apply UI filters
            action_match = (log_action_filter == "Tất cả" or ev.get('action') == log_action_filter)
            role_match = (log_role_filter == "Tất cả" or ev.get('user_role') == log_role_filter)
            
            if action_match and role_match:
                filtered_events.append(ev)
                
        st.markdown(f"Đang hiển thị **{len(filtered_events)} / {len(audit_events)}** sự kiện kiểm toán được cấp phép:")
        
        if filtered_events:
            log_data = []
            for ev in filtered_events:
                # Safe masking (redacted)
                for key in list(ev.keys()):
                    if 'key' in key.lower() or 'pass' in key.lower() or 'secret' in key.lower():
                        ev[key] = '[REDACTED]'
                        
                log_data.append({
                    'Thời gian (UTC)': ev.get('timestamp', ''),
                    'Request ID': ev.get('request_id', ''),
                    'Người dùng': ev.get('user_id_demo', ''),
                    'Vai trò': ", ".join(ev.get('user_role', [])) if isinstance(ev.get('user_role'), list) else ev.get('user_role'),
                    'Hành động': ev.get('action', ''),
                    'Truy vấn': ev.get('query', ''),
                    'Hạn mức loại bỏ (RBAC)': ev.get('rbac_excluded_count', 0),
                    'Trạng thái': ev.get('status', 'SUCCESS')
                })
                
            df_log_display = pd.DataFrame(log_data)
            st.dataframe(df_log_display, use_container_width=True, hide_index=True)
        else:
            st.info("Không có sự kiện nhật ký kiểm toán nào khớp với bộ lọc nghiệp vụ hiện tại.")
