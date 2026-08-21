import os
import sys
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from neo4j import GraphDatabase

# Add scripts directory to sys.path to enable imports
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts'))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

# Import lookup system and logger
from internal_lookup import InternalLookupSystem
from audit_logger import AuditLogger

# Set Page Config with custom title and icon
st.set_page_config(
    page_title="Hệ thống RAG Phân Quyền & Giám Sát Tuân Thủ",
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
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #374151;
    }
    
    /* Glassmorphism containers */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(5px);
        margin-bottom: 20px;
    }
    
    /* Badge styling */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-granted { background-color: #065f46; color: #34d399; }
    .badge-denied { background-color: #7f1d1d; color: #f87171; }
    
    .badge-dapung { background-color: #065f46; color: #34d399; }
    .badge-thieu { background-color: #7f1d1d; color: #f87171; }
    .badge-chenhlech { background-color: #78350f; color: #fbbf24; }
    .badge-chuadu { background-color: #374151; color: #9ca3af; }
    
    /* Header styling with gold/red Agribank tones */
    .header-title {
        background: linear-gradient(135deg, #b91c1c, #d97706);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.2em;
        margin-bottom: 5px;
    }
    
    /* Banner styling */
    .banner-warning {
        background-color: #78350f;
        color: #fef3c7;
        padding: 12px 20px;
        border-radius: 8px;
        border-left: 5px solid #d97706;
        font-weight: 600;
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR: CONFIGURATION & STATUS -----------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/e/e0/Logo_Agribank.svg", width=180)
st.sidebar.markdown("<h2 style='color: #d97706; font-size: 1.3em;'>🔑 Đóng vai người dùng (RBAC)</h2>", unsafe_allow_html=True)

# User ID Demo
user_id_demo = st.sidebar.text_input("User ID Demo:", value="demo_user_01")

# User Role
from src.config import VALID_ROLES
user_role = st.sidebar.selectbox(
    "Vai trò hiện tại (User Role):",
    options=VALID_ROLES,
    index=VALID_ROLES.index("Guest")
)

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #9ca3af; font-size: 1em;'>🌐 Trạng thái Kết nối Hệ thống</h3>", unsafe_allow_html=True)

# Dynamic Neo4j Status check
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
    st.sidebar.markdown("🟢 **Neo4j DB**: Đang kết nối (Online)")
else:
    st.sidebar.markdown("🔴 **Neo4j DB**: Mất kết nối (Offline)")
    
# Initialize Lookup System
@st.cache_resource
def get_lookup_system():
    return InternalLookupSystem()

lookup_system = get_lookup_system()

# ----------------- MAIN TITLE & DISCLAIMER BANNER -----------------
st.markdown("<h1 class='header-title'>🛡️ SECURE RAG & COMPLIANCE GAP ANALYSIS</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #9ca3af;'>Hệ thống tìm kiếm bảo mật phân quyền dữ liệu và đối chiếu tự động chênh lệch tuân thủ bằng AI</p>", unsafe_allow_html=True)

st.markdown("""
<div class='banner-warning'>
    ⚠️ BANNER CẢNH BÁO: Demo đào tạo — Mọi kết quả phân tích chênh lệch tuân thủ do AI đề xuất bắt buộc phải được kiểm toán viên có thẩm quyền xác minh lại (NEEDS_HUMAN_REVIEW).
</div>
""", unsafe_allow_html=True)

# ----------------- TABS CREATION -----------------
tab1, tab2, tab3 = st.tabs(["🔍 TRA CỨU QUY ĐỊNH", "📊 COMPLIANCE GAP CHECKER", "📋 NHẬT KÝ KIỂM TOÁN (AUDIT)"])

# ================= TAB 1: TRA CỨU QUY ĐỊNH =================
with tab1:
    st.markdown("### Tra cứu quy định nội bộ và văn bản pháp luật")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        question = st.text_input("Nhập câu hỏi tra cứu của bạn:", value="Hồ sơ đề nghị cấp Giấy phép lần đầu gồm những gì?")
    with col2:
        top_k = st.slider("Số lượng kết quả (Top-K):", min_value=1, max_value=10, value=5)
        
    if st.button("🚀 Thực hiện Tra cứu", use_container_width=True):
        if question.strip():
            with st.spinner("Hệ thống đang kiểm tra phân quyền và truy xuất dữ liệu..."):
                res = lookup_system.lookup(question, user_role=user_role, user_id=user_id_demo, top_k=top_k)
                
            # Determine access decision based on role query outputs
            # If no chunks are returned and the answer indicates fallback, or if denied
            is_denied = (len(res['citations']) == 0)
            decision_badge = "<span class='status-badge badge-denied'>DENIED</span>" if is_denied else "<span class='status-badge badge-granted'>GRANTED</span>"
            
            st.markdown("---")
            
            # Row of badges
            st.markdown(f"""
            **Mã yêu cầu (Request ID)**: `{res['request_id']}` | 
            **Quyền truy cập (Access Scope)**: `{res['access_scope']}` | 
            **Quyết định truy cập (Access Decision)**: {decision_badge}
            """, unsafe_allow_html=True)
            
            # Answer Display
            st.markdown("#### 💬 Câu trả lời của AI:")
            st.info(res['answer'])
            
            # Show citations and documents only if access is GRANTED (Not empty)
            if not is_denied:
                st.markdown("#### 📄 Nguồn trích dẫn (Citations) được phép truy cập:")
                for cit in res['citations']:
                    st.write(f"- {cit}")
                    
                st.markdown("#### 🧩 Phân đoạn tài liệu (Document/Chunk IDs):")
                st.code(", ".join(res['document_id/chunk_id']))
            else:
                st.warning("🔒 Truy cập bị từ chối đối với nội dung bảo mật hoặc không tìm thấy dữ liệu phù hợp với vai trò của bạn.")
        else:
            st.error("Vui lòng nhập câu hỏi trước khi bấm tra cứu.")

# ================= TAB 2: COMPLIANCE GAP CHECKER =================
with tab2:
    st.markdown("### Kết quả đối chiếu chênh lệch tuân thủ (Compliance Gap Analysis)")
    
    results_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'outputs', 'compliance_gap_results.csv'))
    
    if not os.path.exists(results_path):
        st.warning("⚠️ Không tìm thấy tệp kết quả đối chiếu `compliance_gap_results.csv`. Vui lòng chạy script `compliance_gap.py` trước để sinh kết quả.")
    else:
        # Load CSV data
        df_gap = pd.read_csv(results_path)
        
        # Summary KPI Cards
        total_gaps = len(df_gap)
        dap_ung = len(df_gap[df_gap['classification'] == 'DAP_UNG'])
        chenh_lech = len(df_gap[df_gap['classification'] == 'CHENH_LECH'])
        thieu = len(df_gap[df_gap['classification'] == 'THIEU'])
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Tổng số điều khoản đối chiếu", total_gaps)
        kpi2.metric("Đạt chuẩn (DAP_UNG)", dap_ung)
        kpi3.metric("Chênh lệch (CHENH_LECH)", chenh_lech)
        kpi4.metric("Thiếu (THIEU)", thieu)
        
        st.markdown("#### Danh sách chênh lệch tuân thủ phát hiện:")
        
        # Format table for display
        display_df = df_gap[['gap_id', 'external_citation', 'internal_citation', 'classification', 'confidence', 'review_status']].copy()
        display_df.columns = ["Mã Gap", "Quy định bên ngoài (NHNN)", "Quy trình nội bộ", "Phân loại", "Độ tin cậy", "Trạng thái Review"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### Xem chi tiết Phát hiện:")
        selected_gap_id = st.selectbox("Chọn Mã Gap để xem chi tiết đối chiếu:", options=df_gap['gap_id'].tolist())
        
        if selected_gap_id:
            gap_row = df_gap[df_gap['gap_id'] == selected_gap_id].iloc[0]
            
            # Styling badge for classification
            cls = gap_row['classification']
            if cls == 'DAP_UNG':
                badge = "<span class='status-badge badge-dapung'>DAP_UNG</span>"
            elif cls == 'THIEU':
                badge = "<span class='status-badge badge-thieu'>THIEU</span>"
            elif cls == 'CHENH_LECH':
                badge = "<span class='status-badge badge-chenhlech'>CHENH_LECH</span>"
            else:
                badge = "<span class='status-badge badge-chuadu'>CHUA_DU_BANG_CHUNG</span>"
                
            st.markdown(f"""
            <div class='glass-card'>
                <h3 style='color:#d97706; margin-top:0;'>Phát hiện {gap_row['gap_id']} — Phân loại: {badge}</h3>
                <table style='width:100%; border-collapse: collapse; margin-top:15px;'>
                    <tr style='border-bottom:1px solid #374151;'>
                        <td style='width:25%; font-weight:600; padding:10px 0;'>Yêu cầu bên ngoài:</td>
                        <td style='padding:10px;'>{gap_row['external_requirement']} <br><i style='color:#9ca3af;'>Nguồn: {gap_row['external_citation']} (ID: {gap_row['external_chunk_id']})</i></td>
                    </tr>
                    <tr style='border-bottom:1px solid #374151;'>
                        <td style='font-weight:600; padding:10px 0;'>Bằng chứng nội bộ (Agribank):</td>
                        <td style='padding:10px;'>{gap_row['internal_evidence'] if pd.notna(gap_row['internal_evidence']) else '<i>Không có quy trình tương ứng</i>'} <br><i style='color:#9ca3af;'>Nguồn: {gap_row['internal_citation'] if pd.notna(gap_row['internal_citation']) else 'N/A'} (ID: {gap_row['internal_chunk_id'] if pd.notna(gap_row['internal_chunk_id']) else 'N/A'})</i></td>
                    </tr>
                    <tr style='border-bottom:1px solid #374151;'>
                        <td style='font-weight:600; padding:10px 0;'>Lý do phân loại:</td>
                        <td style='padding:10px;'>{gap_row['reason']}</td>
                    </tr>
                    <tr style='border-bottom:1px solid #374151;'>
                        <td style='font-weight:600; padding:10px 0;'>Độ tin cậy (Confidence):</td>
                        <td style='padding:10px;'><code>{gap_row['confidence']:.2f}</code></td>
                    </tr>
                    <tr>
                        <td style='font-weight:600; padding:10px 0;'>Trạng thái soát xét:</td>
                        <td style='padding:10px; color:#fbbf24; font-weight:600;'>🚨 {gap_row['review_status']}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

# ================= TAB 3: AUDIT TRAIL =================
with tab3:
    st.markdown("### Lịch sử ghi nhận nghiệp vụ hệ thống (Audit Trail Log)")
    
    log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'outputs', 'audit_log.jsonl'))
    
    if not os.path.exists(log_path):
        st.warning("⚠️ Chưa có tệp nhật ký `audit_log.jsonl`. Vui lòng chạy các kịch bản tra cứu/đối chiếu để tạo lịch sử.")
    else:
        # Read JSONL file
        audit_events = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        audit_events.append(json.loads(line.strip()))
                    except Exception:
                        pass
                        
        # Filter log events based on current user role (RBAC filter on logs)
        filtered_events = []
        for event in audit_events:
            # Get roles in log (could be string or list)
            log_roles = event.get('user_role', [])
            if isinstance(log_roles, str):
                try:
                    log_roles = json.loads(log_roles)
                except Exception:
                    log_roles = [log_roles]
                    
            # Admin can see everything
            # Others can only see logs if they match their role
            if user_role == "Admin" or any(r == user_role for r in log_roles):
                filtered_events.append(event)
                
        st.markdown(f"Đang hiển thị **{len(filtered_events)} / {len(audit_events)}** nhật ký kiểm toán phù hợp với vai trò `{user_role}`.")
        
        # Display logs in table
        if filtered_events:
            # Format table data
            log_data = []
            for ev in filtered_events:
                # Double-check: ensure no secrets are exposed in logs (redundant guardrail)
                for key in ev:
                    if 'key' in key.lower() or 'pass' in key.lower() or 'secret' in key.lower():
                        ev[key] = '[REDACTED]'
                        
                log_data.append({
                    'Thời gian (UTC)': ev.get('timestamp', ''),
                    'Request ID': ev.get('request_id', ''),
                    'Người dùng': ev.get('user_id_demo', ''),
                    'Vai trò': ", ".join(ev.get('user_role', [])) if isinstance(ev.get('user_role'), list) else ev.get('user_role'),
                    'Hành động': ev.get('action', ''),
                    'Truy vấn (Query)': ev.get('query', ''),
                    'Hạn mức loại bỏ (RBAC)': ev.get('rbac_excluded_count', 0),
                    'Trạng thái': ev.get('status', 'SUCCESS')
                })
                
            df_log_display = pd.DataFrame(log_data)
            st.dataframe(df_log_display, use_container_width=True, hide_index=True)
        else:
            st.info("Không có nhật ký kiểm toán nào được phép xem cho vai trò này.")
