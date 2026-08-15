import os
import csv
import re
import sys
import io

# Set stdout/stderr to UTF-8 to prevent console printing encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def extract_frontmatter_and_links(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Extract YAML frontmatter
    frontmatter = {}
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        for line in fm_text.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                frontmatter[key.strip()] = val.strip()
                
    # Extract Obsidian wikilinks: [[Link Target]] or [[Link Target|Display Text]]
    # Match [[...]] but exclude any double brackets nested if any
    links = re.findall(r'\[\[(.*?)\]\]', content)
    cleaned_links = []
    for link in links:
        # If there's a display pipe like [[Target|Display]], take the target part
        if '|' in link:
            link = link.split('|', 0)
        cleaned_links.append(link.strip())
        
    return frontmatter, cleaned_links

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output_dir = os.path.join(project_dir, 'outputs')
    wiki_dir = os.path.join(project_dir, 'wiki')
    
    entities_csv_path = os.path.join(output_dir, 'entities.csv')
    relations_csv_path = os.path.join(output_dir, 'relations.csv')
    
    # 1. Check outputs files existence
    if not os.path.exists(entities_csv_path) or not os.path.exists(relations_csv_path):
        print("Error: Normalization files entities.csv or relations.csv do not exist.", file=sys.stderr)
        sys.exit(1)
        
    # Read entities from CSV
    csv_entities = {}
    csv_duplicate_ids = []
    with open(entities_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            eid = row['id'].strip()
            if eid in csv_entities:
                csv_duplicate_ids.append(eid)
            csv_entities[eid] = dict(row)
            
    # Read relations from CSV
    csv_relations = []
    with open(relations_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        csv_relations = [dict(row) for row in reader]
        
    # 2. Scan Wiki Folder for Markdown Files
    markdown_files = []
    for root, dirs, files in os.walk(wiki_dir):
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(os.path.join(root, file))
                
    wiki_pages = {} # filename_without_ext -> file_path
    wiki_metadata = {} # file_path -> (frontmatter, links)
    wiki_by_id = {} # id -> file_path
    
    total_wikilinks_count = 0
    
    for fpath in markdown_files:
        fname = os.path.splitext(os.path.basename(fpath))[0]
        wiki_pages[fname] = fpath
        
        fm, links = extract_frontmatter_and_links(fpath)
        wiki_metadata[fpath] = (fm, links)
        total_wikilinks_count += len(links)
        
        if fm.get('id'):
            wiki_by_id[fm['id']] = fpath
            
    # 3. Analyze Issues
    broken_links = [] # (source_file, link_target)
    entity_id_mismatches_missing_in_csv = [] # wiki files with IDs missing in CSV
    entity_id_mismatches_missing_in_wiki = [] # CSV entities missing in Wiki
    broken_relations = [] # relation rows with missing source/target in Wiki
    unmitigated_risks = [] # Risks with no mitigating controls
    unassociated_risks = [] # Risks with no events
    orphan_pages = [] # Pages with no incoming/outgoing links (except Home.md)
    
    # Track link graph for orphan check
    # We build an adjacency list representing direct links between pages
    # Source page -> targets, and Target page -> sources
    links_to = {fname: set() for fname in wiki_pages}
    links_from = {fname: set() for fname in wiki_pages}
    
    for fpath, (fm, links) in wiki_metadata.items():
        src_name = os.path.splitext(os.path.basename(fpath))[0]
        if src_name == 'Home':
            continue
            
        for link in links:
            # Home links don't count towards normal relationships in orphan check
            if link == 'Home':
                continue
            # Check if target page exists in wiki
            if link not in wiki_pages:
                broken_links.append((os.path.basename(fpath), link))
            else:
                links_to[src_name].add(link)
                links_from[link].add(src_name)
                
    # Check ID alignment
    for eid in csv_entities:
        if eid not in wiki_by_id:
            entity_id_mismatches_missing_in_wiki.append(eid)
            
    for eid, fpath in wiki_by_id.items():
        if eid not in csv_entities:
            entity_id_mismatches_missing_in_csv.append((os.path.basename(fpath), eid))
            
    # Verify relations integrity
    for rel in csv_relations:
        s_id = rel['source_id']
        t_id = rel['target_id']
        rel_type = rel['relationship_type']
        
        if s_id not in csv_entities or t_id not in csv_entities:
            broken_relations.append(rel)
            
    # Audit Risks for controls and events
    # We check relationships from relations.csv directly for correctness
    for eid, ent in csv_entities.items():
        if ent['type'] == 'RuiRo':
            # Check mitigating controls
            controls_mitigating = [r for r in csv_relations if r['target_id'] == eid and r['relationship_type'] == 'MITIGATES']
            if not controls_mitigating:
                unmitigated_risks.append((eid, ent['name']))
                
            # Check events
            events_associated = [r for r in csv_relations if r['source_id'] == eid and r['relationship_type'] == 'OBSERVED_AS']
            if not events_associated:
                unassociated_risks.append((eid, ent['name']))
                
    # Detect Orphan Pages (no links to and no links from other content pages, ignoring Home)
    for fname in wiki_pages:
        if fname == 'Home':
            continue
        in_count = len(links_from[fname])
        out_count = len(links_to[fname])
        if in_count == 0 and out_count == 0:
            # Determine path to find ID
            fpath = wiki_pages[fname]
            fm, _ = wiki_metadata[fpath]
            orphan_pages.append((fname, fm.get('id', 'N/A')))
            
    # 4. Generate Report
    report = []
    report.append("# BÁO CÁO KIỂM THỬ WIKI RISK GRAPH")
    report.append("")
    report.append("Báo cáo này được tự động tạo bởi script `validate_wiki.py` để đánh giá tính toàn vẹn của dữ liệu và hệ thống Wiki liên kết.")
    report.append("")
    
    report.append("## 1. Số liệu tổng hợp")
    report.append(f"- **Tổng số tệp tin Markdown (.md)**: `{len(markdown_files)}` tệp")
    report.append(f"- **Tổng số liên kết chéo (Wikilinks)**: `{total_wikilinks_count}` liên kết")
    report.append(f"- **Tổng số thực thể trong entities.csv**: `{len(csv_entities)}` thực thể")
    report.append(f"- **Tổng số quan hệ trong relations.csv**: `{len(csv_relations)}` quan hệ")
    report.append("")
    
    report.append("## 2. Kiểm thử tính toàn vẹn (Tính đúng đắn của code)")
    
    # Broken links
    report.append("### A. Liên kết chéo bị hỏng (Broken Wikilinks)")
    if broken_links:
        report.append(f"❌ Phát hiện `{len(broken_links)}` liên kết bị hỏng:")
        for src, target in broken_links:
            report.append(f"  - Tệp `{src}` trỏ tới trang không tồn tại: `[[{target}]]`")
    else:
        report.append("✅ Không phát hiện liên kết chéo bị hỏng.")
    report.append("")
    
    # Duplicates ID
    report.append("### B. Thực thể bị trùng ID trong entities.csv")
    if csv_duplicate_ids:
        report.append(f"❌ Phát hiện `{len(csv_duplicate_ids)}` ID bị trùng lặp:")
        for eid in csv_duplicate_ids:
            report.append(f"  - ID: `{eid}`")
    else:
        report.append("✅ Không phát hiện ID trùng lặp trong thực thể.")
    report.append("")
    
    # ID mismatch
    report.append("### C. Lệch khớp ID giữa Wiki và entities.csv")
    if entity_id_mismatches_missing_in_csv or entity_id_mismatches_missing_in_wiki:
        if entity_id_mismatches_missing_in_csv:
            report.append(f"❌ Phát hiện `{len(entity_id_mismatches_missing_in_csv)}` trang Wiki có ID không tồn tại trong entities.csv:")
            for fname, eid in entity_id_mismatches_missing_in_csv:
                report.append(f"  - Tệp `{fname}` chứa ID: `{eid}`")
        if entity_id_mismatches_missing_in_wiki:
            report.append(f"❌ Phát hiện `{len(entity_id_mismatches_missing_in_wiki)}` ID từ entities.csv không được tạo trang Wiki tương ứng:")
            for eid in entity_id_mismatches_missing_in_wiki:
                report.append(f"  - ID: `{eid}`")
    else:
        report.append("✅ Hoàn toàn khớp ID giữa Wiki và entities.csv.")
    report.append("")
    
    # Broken relations
    report.append("### D. Quan hệ chứa thực thể không tồn tại (Broken Relations)")
    if broken_relations:
        report.append(f"❌ Phát hiện `{len(broken_relations)}` quan hệ chứa thực thể không tồn tại:")
        for rel in broken_relations:
            report.append(f"  - Quan hệ: `{rel['source_id']} -{rel['relationship_type']}-> {rel['target_id']}`")
    else:
        report.append("✅ Tất cả quan hệ đều trỏ đến các thực thể tồn tại.")
    report.append("")
    
    report.append("## 3. Kiểm thử nghiệp vụ rủi ro (Tính đầy đủ của dữ liệu nguồn)")
    report.append("> [!IMPORTANT]")
    report.append("> Các phát hiện dưới đây phản ánh **khoảng trống dữ liệu nguồn (Data Gaps)** từ file hạt giống (seed CSVs) chứ không phải lỗi lập trình.")
    report.append("")
    
    # Unmitigated risks
    report.append("### A. Rủi ro chưa có biện pháp kiểm soát giảm thiểu (Unmitigated Risks)")
    if unmitigated_risks:
        report.append(f"⚠️ Phát hiện `{len(unmitigated_risks)}` rủi ro trống biện pháp kiểm soát:")
        for eid, name in unmitigated_risks:
            report.append(f"  - Rủi ro `{eid}`: **[[{name}]]**")
    else:
        report.append("✅ Tất cả rủi ro đều có biện pháp kiểm soát.")
    report.append("")
    
    # Risks without events
    report.append("### B. Rủi ro chưa có sự kiện thực tế phát sinh (Risks without Events)")
    if unassociated_risks:
        report.append(f"⚠️ Phát hiện `{len(unassociated_risks)}` rủi ro chưa có sự kiện phát sinh:")
        for eid, name in unassociated_risks:
            report.append(f"  - Rủi ro `{eid}`: **[[{name}]]**")
    else:
        report.append("✅ Tất cả rủi ro đều ghi nhận ít nhất một sự kiện thực tế phát sinh.")
    report.append("")
    
    # Orphan pages
    report.append("### C. Trang mồ côi (Orphan Pages)")
    if orphan_pages:
        report.append(f"⚠️ Phát hiện `{len(orphan_pages)}` trang mồ côi (không có kết nối ngoại trừ trang chủ Home):")
        for fname, eid in orphan_pages:
            report.append(f"  - Trang `{fname}` (ID: `{eid}`)")
    else:
        report.append("✅ Không có trang thực thể nào bị cô lập (mồ côi).")
    report.append("")
    
    # Write report file
    report_out_path = os.path.join(output_dir, 'wiki_validation_report.md')
    with open(report_out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report) + '\n')
        
    print(f"Validation report successfully written to: {report_out_path}")
    
    # Display summary on console
    print(f"\n==================================================")
    print(f"VALIDATION SUMMARY")
    print(f"==================================================")
    print(f"Markdown files: {len(markdown_files)}")
    print(f"Total wikilinks: {total_wikilinks_count}")
    print(f"Broken wikilinks: {len(broken_links)}")
    print(f"Unmitigated risks: {len(unmitigated_risks)}")
    print(f"Orphan pages: {len(orphan_pages)}")

if __name__ == '__main__':
    main()
