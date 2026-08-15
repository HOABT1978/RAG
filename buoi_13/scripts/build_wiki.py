import os
import csv
import sys
import io

# Set stdout/stderr to UTF-8 to prevent console printing encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def sanitize_filename(name):
    # Remove characters that are illegal in Windows filenames
    illegal = '<>:"/\\|?*'
    for char in illegal:
        name = name.replace(char, '_')
    return name.strip()

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output_dir = os.path.join(project_dir, 'outputs')
    wiki_dir = os.path.join(project_dir, 'wiki')
    
    # Create subdirectories
    risks_dir = os.path.join(wiki_dir, 'risks')
    controls_dir = os.path.join(wiki_dir, 'controls')
    events_dir = os.path.join(wiki_dir, 'events')
    
    os.makedirs(risks_dir, exist_ok=True)
    os.makedirs(controls_dir, exist_ok=True)
    os.makedirs(events_dir, exist_ok=True)
    
    # 1. Read entities.csv
    entities_path = os.path.join(output_dir, 'entities.csv')
    if not os.path.exists(entities_path):
        print(f"Error: entities.csv not found at {entities_path}", file=sys.stderr)
        sys.exit(1)
        
    entities = {}
    entities_by_id = {}
    with open(entities_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ent = dict(row)
            entities_by_id[ent['id']] = ent
            
    # 2. Read relations.csv
    relations_path = os.path.join(output_dir, 'relations.csv')
    if not os.path.exists(relations_path):
        print(f"Error: relations.csv not found at {relations_path}", file=sys.stderr)
        sys.exit(1)
        
    relations = []
    with open(relations_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        relations = [dict(row) for row in reader]
        
    # Build indexing of relationships for fast lookup
    # source_id -> list of relationships
    outgoing = {}
    # target_id -> list of relationships
    incoming = {}
    for rel in relations:
        s_id = rel['source_id']
        t_id = rel['target_id']
        
        if s_id not in outgoing:
            outgoing[s_id] = []
        outgoing[s_id].append(rel)
        
        if t_id not in incoming:
            incoming[t_id] = []
        incoming[t_id].append(rel)
        
    wiki_pages_count = 0
    wikilink_count = 0
    
    # Track paths for the requested example: KiemSoat -> RuiRo -> SuKienRuiRo
    exemplary_paths = []
    
    # 3. Create individual entity wiki files
    for ent_id, ent in entities_by_id.items():
        ent_type = ent['type']
        ent_name = ent['name']
        filename = sanitize_filename(ent_name) + '.md'
        
        # Determine subdirectory
        if ent_type == 'RuiRo':
            file_path = os.path.join(risks_dir, filename)
        elif ent_type == 'KiemSoat':
            file_path = os.path.join(controls_dir, filename)
        elif ent_type == 'SuKienRuiRo':
            file_path = os.path.join(events_dir, filename)
        else:
            print(f"Warning: Unknown entity type '{ent_type}' for id '{ent_id}'", file=sys.stderr)
            continue
            
        content = []
        # YAML Frontmatter
        content.append("---")
        content.append(f"id: {ent_id}")
        content.append(f"type: {ent_type}")
        content.append(f"verification_status: {ent['verification_status']}")
        content.append(f"data_origin: {ent['data_origin']}")
        content.append("---")
        content.append("")
        
        # Title
        content.append(f"# {ent_type}: {ent_name}")
        content.append("")
        
        # Attributes Table / List
        content.append("## Thông tin thực thể")
        content.append(f"- **Mã thực thể (ID)**: `{ent_id}`")
        content.append(f"- **Trạng thái xác thực**: `{ent['verification_status']}`")
        content.append(f"- **Nguồn dữ liệu**: `{ent['data_origin']}`")
        
        if ent_type == 'RuiRo':
            content.append(f"- **Phân loại rủi ro**: {ent['category']}")
            content.append(f"- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `{ent['inherent_level']}`")
            content.append(f"- **Mức độ rủi ro còn lại (Residual Level)**: `{ent['residual_level']}`")
            content.append(f"- **Đơn vị sở hữu (Owner Unit)**: `{ent['owner_unit_id']}` *(Chưa có dữ liệu master đơn vị)*")
            content.append("")
            content.append("## Mô tả rủi ro")
            content.append(ent['description'] if ent['description'] else "Chưa có mô tả.")
            content.append("")
            content.append("## Nguyên nhân (Cause)")
            content.append(ent['cause'] if ent['cause'] else "Chưa có thông tin.")
            content.append("")
            content.append("## Sự kiện kích hoạt (Event)")
            content.append(ent['event'] if ent['event'] else "Chưa có thông tin.")
            content.append("")
            content.append("## Tác động (Impact)")
            content.append(ent['impact'] if ent['impact'] else "Chưa có thông tin.")
            content.append("")
            
            # Relations: MITIGATES (Controls that mitigate this risk)
            content.append("## Biện pháp kiểm soát giảm thiểu (Mitigating Controls)")
            risk_incoming = incoming.get(ent_id, [])
            mitigating_controls = [r for r in risk_incoming if r['relationship_type'] == 'MITIGATES']
            
            if mitigating_controls:
                for rel in mitigating_controls:
                    ctrl_id = rel['source_id']
                    ctrl_ent = entities_by_id.get(ctrl_id)
                    if ctrl_ent:
                        ctrl_name = ctrl_ent['name']
                        content.append(f"- [[{ctrl_name}]] (Mã: `{ctrl_id}`, Loại quan hệ: `{rel['relationship_type']}`, Trạng thái xác thực: `{rel['verification_status']}`, Trích dẫn: *\"{rel['evidence_quote']}\"*)")
                        wikilink_count += 1
                        
                        # Collect pathways for example printout
                        # Find events associated with this risk
                        risk_outgoing = outgoing.get(ent_id, [])
                        observed_events = [o for o in risk_outgoing if o['relationship_type'] == 'OBSERVED_AS']
                        for ev_rel in observed_events:
                            ev_id = ev_rel['target_id']
                            ev_ent = entities_by_id.get(ev_id)
                            if ev_ent:
                                exemplary_paths.append(f"  {ctrl_name} (KS) -[MITIGATES]-> {ent_name} (RR) -[OBSERVED_AS]-> {ev_ent['name']} (SK)")
            else:
                content.append("Chưa có biện pháp kiểm soát liên quan.")
            content.append("")
            
            # Relations: OBSERVED_AS (Events that this risk materialized as)
            content.append("## Sự kiện rủi ro đã phát sinh (Risk Events)")
            risk_outgoing = outgoing.get(ent_id, [])
            observed_events = [r for r in risk_outgoing if r['relationship_type'] == 'OBSERVED_AS']
            
            if observed_events:
                for rel in observed_events:
                    ev_id = rel['target_id']
                    ev_ent = entities_by_id.get(ev_id)
                    if ev_ent:
                        ev_name = ev_ent['name']
                        content.append(f"- [[{ev_name}]] (Mã: `{ev_id}`, Loại quan hệ: `{rel['relationship_type']}`, Trạng thái xác thực: `{rel['verification_status']}`, Trích dẫn: *\"{rel['evidence_quote']}\"*)")
                        wikilink_count += 1
            else:
                content.append("Chưa phát sinh sự kiện rủi ro liên quan.")
                
        elif ent_type == 'KiemSoat':
            content.append(f"- **Loại kiểm soát**: `{ent['control_type']}`")
            content.append(f"- **Tần suất thực hiện**: `{ent['frequency']}`")
            content.append(f"- **Hiệu lực kiểm soát (Effectiveness)**: `{ent['effectiveness']}`")
            content.append(f"- **Vai trò chịu trách nhiệm**: `{ent['owner_role_id']}` *(Chưa có dữ liệu master vai trò)*")
            content.append("")
            
            # Relations: MITIGATES (Risks mitigated by this control)
            content.append("## Rủi ro giảm thiểu")
            ctrl_outgoing = outgoing.get(ent_id, [])
            mitigated_risks = [r for r in ctrl_outgoing if r['relationship_type'] == 'MITIGATES']
            
            if mitigated_risks:
                for rel in mitigated_risks:
                    risk_id = rel['target_id']
                    risk_ent = entities_by_id.get(risk_id)
                    if risk_ent:
                        risk_name = risk_ent['name']
                        content.append(f"- [[{risk_name}]] (Mã: `{risk_id}`, Loại quan hệ: `{rel['relationship_type']}`, Trạng thái xác thực: `{rel['verification_status']}`, Trích dẫn: *\"{rel['evidence_quote']}\"*)")
                        wikilink_count += 1
            else:
                content.append("Chưa liên kết giảm thiểu cho rủi ro nào.")
                
        elif ent_type == 'SuKienRuiRo':
            content.append(f"- **Thời gian xảy ra**: `{ent['occurred_at']}`")
            content.append(f"- **Thời gian phát hiện**: `{ent['discovered_at']}`")
            content.append(f"- **Mức độ nghiêm trọng**: `{ent['severity']}`")
            content.append(f"- **Tổn thất tài chính**: `{ent['loss_amount_vnd']}` VND")
            content.append("")
            content.append("## Mô tả sự kiện")
            content.append(ent['description'] if ent['description'] else "Chưa có mô tả.")
            content.append("")
            
            # Relations: OBSERVED_AS (Risk corresponding to this event)
            content.append("## Rủi ro gốc phát sinh")
            ev_incoming = incoming.get(ent_id, [])
            associated_risks = [r for r in ev_incoming if r['relationship_type'] == 'OBSERVED_AS']
            
            if associated_risks:
                for rel in associated_risks:
                    risk_id = rel['source_id']
                    risk_ent = entities_by_id.get(risk_id)
                    if risk_ent:
                        risk_name = risk_ent['name']
                        content.append(f"- [[{risk_name}]] (Mã: `{risk_id}`, Loại quan hệ: `{rel['relationship_type']}`, Trạng thái xác thực: `{rel['verification_status']}`, Trích dẫn: *\"{rel['evidence_quote']}\"*)")
                        wikilink_count += 1
            else:
                content.append("Chưa liên kết với rủi ro gốc nào.")
                
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content) + '\n')
        wiki_pages_count += 1
        
    # 4. Create Home.md starting page
    home_content = []
    home_content.append("# Wiki Risk Graph - Portal Đào Tạo")
    home_content.append("")
    home_content.append("Chào mừng bạn đến với Wiki Risk Graph được xây dựng phục vụ đào tạo thực hành.")
    home_content.append("")
    
    # Statistics
    home_content.append("## Thống kê Đồ thị (Wiki Summary)")
    
    # Gather counts
    risks_list = [e for e in entities_by_id.values() if e['type'] == 'RuiRo']
    controls_list = [e for e in entities_by_id.values() if e['type'] == 'KiemSoat']
    events_list = [e for e in entities_by_id.values() if e['type'] == 'SuKienRuiRo']
    
    mitigates_rel = [r for r in relations if r['relationship_type'] == 'MITIGATES']
    observed_rel = [r for r in relations if r['relationship_type'] == 'OBSERVED_AS']
    
    home_content.append(f"- **Tổng số thực thể (Nodes)**: `{len(entities_by_id)}` trang")
    home_content.append(f"  - Rủi ro (RuiRo): `{len(risks_list)}` trang")
    home_content.append(f"  - Biện pháp kiểm soát (KiemSoat): `{len(controls_list)}` trang")
    home_content.append(f"  - Sự kiện rủi ro (SuKienRuiRo): `{len(events_list)}` trang")
    home_content.append(f"- **Tổng số liên kết đồ thị (Edges)**: `{len(relations)}` quan hệ")
    home_content.append(f"  - Quan hệ giảm thiểu (MITIGATES): `{len(mitigates_rel)}` cạnh")
    home_content.append(f"  - Quan hệ phát sinh dưới dạng (OBSERVED_AS): `{len(observed_rel)}` cạnh")
    home_content.append("")
    
    # Risks section
    home_content.append("## 1. Danh sách Rủi ro (Risks)")
    for r in sorted(risks_list, key=lambda x: x['id']):
        home_content.append(f"- [[{r['name']}]] (Mã: `{r['id']}`)")
        wikilink_count += 1
    home_content.append("")
    
    # Controls section
    home_content.append("## 2. Danh sách Biện pháp Kiểm soát (Controls)")
    for c in sorted(controls_list, key=lambda x: x['id']):
        home_content.append(f"- [[{c['name']}]] (Mã: `{c['id']}`)")
        wikilink_count += 1
    home_content.append("")
    
    # Events section
    home_content.append("## 3. Danh sách Sự kiện Rủi ro (Events)")
    for e in sorted(events_list, key=lambda x: x['id']):
        home_content.append(f"- [[{e['name']}]] (Mã: `{e['id']}`)")
        wikilink_count += 1
    home_content.append("")
    
    # Write Home.md
    home_path = os.path.join(wiki_dir, 'Home.md')
    with open(home_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(home_content) + '\n')
    wiki_pages_count += 1
    
    print(f"Wiki pages created: {wiki_pages_count} (including Home.md)")
    print(f"Total wikilinks generated: {wikilink_count}")
    
    print(f"\nVí dụ đường đi kiểm tra (Path: KiemSoat -> RuiRo -> SuKienRuiRo):")
    if exemplary_paths:
        # Print top 3 example paths
        for path in exemplary_paths[:3]:
            print(path)
    else:
        print("  None found.")

if __name__ == '__main__':
    main()
