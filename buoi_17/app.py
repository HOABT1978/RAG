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
log_path = os.path.join(script_dir, 'outputs', 'audit_log.jsonl')

# ----------------- SIDEBAR: CONFIGURATION & STATUS -----------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/e/e0/Logo_Agribank.svg", width=180)
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
st.markdown("<h1 class='header-title'>🛡️ AI COMPLIANCE & AUDIT ASSISTANT</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #9ca3af; font-size:1.1em;'>Hệ thống Trợ lý Kiểm soát Tuân thủ & Sinh Bản nháp Checklist Kiểm toán Agribank</p>", unsafe_allow_html=True)

st.markdown("""
<div class='banner-warning'>
    ⚠️ KHUYẾN CÁO CỦA HỘI ĐỒNG KIỂM TOÁN: Đây là demo sản phẩm trợ lý AI Kiểm toán — Kết quả phân tích mâu thuẫn và gợi ý checklist bắt buộc phải được Kiểm toán viên chuyên trách xác minh và duyệt lại trước khi ban hành chính thức.
</div>
""", unsafe_allow_html=True)

# ----------------- TABS CREATION -----------------
tab1, tab2, tab3 = st.tabs([
    "🔍 UC3 — AI COMPLIANCE CHECKER", 
    "📋 UC4 — AI AUDIT CHECKLIST GENERATOR", 
    "📜 AUDIT LOG & SYSTEM TRAIL"
])

# ================= TAB 1: UC3 — AI COMPLIANCE CHECKER =================
with tab1:
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
            for idx, row in df_conf.iterrows():
                sev = str(row['severity']).upper()
                if sev == 'HIGH':
                    sev_badge = "<span class='badge badge-high'>HIGH</span>"
                elif sev == 'MEDIUM':
                    sev_badge = "<span class='badge badge-medium'>MEDIUM</span>"
                else:
                    sev_badge = "<span class='badge badge-low'>LOW</span>"
                    
                review_badge = f"<span class='badge badge-review'>{row['review_status']}</span>"
                
                st.markdown(f"""
                <div class='glass-card'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;'>
                        <span style='font-size:1.25em; font-weight:700; color:#e11d48;'>Mã xung đột: {row['conflict_id']}</span>
                        <div class="badges-wrapper">
                            {sev_badge}
                            {review_badge}
                        </div>
                    </div>
                    <div style='margin-top:10px; font-size:1.05em;'>
                        <strong>Miền nghiệp vụ</strong>: <code>{row['domain']}</code> | 
                        <strong>Loại mâu thuẫn</strong>: <code style='color:#fbbf24;'>{row['conflict_type']}</code>
                    </div>
                    
                    <div style='margin-top:15px; display:grid; grid-template-columns: 1fr 1fr; gap:20px; border-top:1px solid #1e293b; padding-top:15px;'>
                        <div>
                            <span style='color:#34d399; font-weight:600;'>Văn bản nội bộ (A)</span>: <code>{row['doc_a_id']}</code><br>
                            <i style='color:#9ca3af;'>Trích dẫn: {row['doc_a_citation']}</i>
                            <p style='margin-top:5px; font-style:italic;'>"{row['doc_a_text']}"</p>
                        </div>
                        <div>
                            <span style='color:#f87171; font-weight:600;'>Quy định pháp lý / SBV (B)</span>: <code>{row['doc_b_id']}</code><br>
                            <i style='color:#9ca3af;'>Trích dẫn: {row['doc_b_citation']}</i>
                            <p style='margin-top:5px; font-style:italic;'>"{row['doc_b_text']}"</p>
                        </div>
                    </div>
                    
                    <div style='margin-top:15px; background:rgba(0,0,0,0.2); padding:10px; border-radius:6px; border-left:4px solid #d97706;'>
                        <strong>Phân tích của Trợ lý AI Compliance:</strong><br>
                        {row['description']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ================= TAB 2: UC4 — AI AUDIT CHECKLIST GENERATOR =================
with tab2:
    st.markdown("### Thiết lập bản nháp Checklist Kiểm toán bằng AI")
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
        
    if st.button("📋 Tạo Bản Nháp Checklist Kiểm Toán", use_container_width=True):
        with st.spinner("Động cơ AI Audit đang phân tích và sinh danh sách checklist kiểm soát..."):
            try:
                # Call audit checklist generator python script
                py_exec = sys.executable
                script_path = os.path.join(scripts_dir, 'audit_checklist_gen.py')
                res = subprocess.run([py_exec, script_path], capture_output=True, text=True, encoding='utf-8')
                if res.returncode == 0:
                    st.success("Tạo thành công bản nháp checklist kiểm toán!")
                else:
                    st.error(f"Lỗi khi thực thi: {res.stderr}")
            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")
                
    st.markdown("---")
    st.markdown("#### Bảng Checklist Kiểm toán đề xuất:")
    
    if not os.path.exists(checklist_csv_path):
        st.warning("⚠️ Chưa có dữ liệu checklist. Vui lòng bấm nút 'Tạo Bản Nháp Checklist Kiểm Toán' ở trên.")
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
                        st.markdown(f"**Trích dẫn nguồn gốc:**\n`{row['source_citation']}`")
                        st.markdown(f"**Trạng thái kiểm duyệt:**\n🚨 `{row['review_status']}`")
                        st.markdown(f"**Mã checklist**: `{row['item_id']}`")
                        
                st.markdown("<hr style='margin: 10px 0; border: 0; border-top: 1px solid rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

# ================= TAB 3: AUDIT LOG & SYSTEM TRAIL =================
with tab3:
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
