import os
import csv
import sys
import io
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def find_data_dir():
    # Candidates for data directory relative to the script location or current working directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(script_dir), 'data'),
        os.path.join(script_dir, '..', 'data'),
        os.path.join(os.path.dirname(script_dir), 'buoi_13', 'data'),
        os.path.join(os.getcwd(), 'buoi_13', 'data'),
        os.path.join(os.getcwd(), 'data'),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            return os.path.abspath(c)
    print("Error: Could not find data directory containing the seed CSV files.", file=sys.stderr)
    sys.exit(1)

def inspect_file(file_path):
    print(f"\n==================================================")
    print(f"INSPECTING FILE: {os.path.basename(file_path)}")
    print(f"==================================================")
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None
        
    rows = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            headers = [h.strip() for h in next(reader)]
        except StopIteration:
            print("Empty file!")
            return {
                'headers': [],
                'row_count': 0,
                'rows': [],
                'null_counts': {},
                'duplicates': 0
            }
        
        for r in reader:
            if not r or all(cell.strip() == '' for cell in r):
                continue  # skip empty lines
            rows.append([cell.strip() for cell in r])
            
    row_count = len(rows)
    print(f"Row count (excluding header and empty rows): {row_count}")
    print(f"Columns ({len(headers)}): {', '.join(headers)}")
    
    # Null values check (empty string, 'null', 'nan', etc.)
    null_counts = {h: 0 for h in headers}
    for row in rows:
        for idx, val in enumerate(row):
            if idx < len(headers):
                cell_val = val.strip()
                if cell_val == '' or cell_val.lower() == 'null' or cell_val.lower() == 'nan':
                    null_counts[headers[idx]] += 1
                
    print("Null/Empty counts per column:")
    for h, cnt in null_counts.items():
        print(f"  - {h}: {cnt}")
        
    # Duplicate rows check (exact row match)
    row_tuples = [tuple(r) for r in rows]
    row_counter = Counter(row_tuples)
    duplicates = sum(cnt - 1 for cnt in row_counter.values() if cnt > 1)
    print(f"Duplicate rows: {duplicates}")
    
    # Primary Key candidates check (usually 'id' or first column)
    pk_column = 'id' if 'id' in headers else (headers[0] if headers else None)
    pk_values = []
    if pk_column:
        pk_idx = headers.index(pk_column)
        pk_values = [r[pk_idx].strip() for r in rows if pk_idx < len(r)]
        pk_counter = Counter(pk_values)
        pk_nulls = sum(1 for val in pk_values if val == '')
        pk_duplicates = sum(cnt - 1 for cnt in pk_counter.values() if cnt > 1)
        
        print(f"Primary Key Candidate: '{pk_column}'")
        print(f"  - Unique values: {len(pk_counter)}")
        print(f"  - Nulls in PK: {pk_nulls}")
        print(f"  - Duplicates in PK: {pk_duplicates}")
        if pk_nulls == 0 and pk_duplicates == 0 and len(pk_counter) == row_count:
            print(f"  -> Valid Primary Key!")
        else:
            print(f"  -> INVALID Primary Key! (Needs unique & non-null values)")
    else:
        print("No Primary Key candidate found ('id' or first column).")
        
    return {
        'headers': headers,
        'row_count': row_count,
        'rows': rows,
        'null_counts': null_counts,
        'duplicates': duplicates,
        'pk_column': pk_column,
        'pk_values': set(pk_values) if pk_column else set()
    }

def main():
    data_dir = find_data_dir()
    print(f"Using data directory: {data_dir}")
    
    files = {
        'risks': 'risk_profiles_seed.csv',
        'controls': 'controls_seed.csv',
        'events': 'risk_events_seed.csv',
        'relationships': 'relationships_seed.csv'
    }
    
    results = {}
    for key, filename in files.items():
        path = os.path.join(data_dir, filename)
        results[key] = inspect_file(path)
        
    # Analyze References / Foreign Keys and Relationships
    print(f"\n==================================================")
    print(f"CROSS-REFERENCE & RELATIONSHIP INTEGRITY CHECK")
    print(f"==================================================")
    
    # 1. Risk Events reference to Risks
    events_data = results.get('events')
    risks_data = results.get('risks')
    if events_data and risks_data and 'risk_id' in events_data['headers']:
        risk_ids = risks_data['pk_values']
        e_headers = events_data['headers']
        risk_id_idx = e_headers.index('risk_id')
        event_id_idx = e_headers.index('id') if 'id' in e_headers else 0
        
        missing_refs = []
        for r in events_data['rows']:
            e_id = r[event_id_idx] if event_id_idx < len(r) else "unknown"
            r_id = r[risk_id_idx].strip() if risk_id_idx < len(r) else ""
            if r_id not in risk_ids:
                missing_refs.append((e_id, r_id))
                
        print(f"Reference Check: Risk Events ('risk_id') -> Risks ('id')")
        if missing_refs:
            print(f"  -> WARNING: {len(missing_refs)} missing/broken references found:")
            for e_id, r_id in missing_refs:
                print(f"     * Event '{e_id}' references non-existent Risk '{r_id}'")
        else:
            print(f"  -> OK: All risk events reference valid risk profiles.")
            
    # 2. Relationships References
    rel_data = results.get('relationships')
    controls_data = results.get('controls')
    
    if rel_data:
        r_headers = rel_data['headers']
        source_idx = r_headers.index('source_id') if 'source_id' in r_headers else -1
        target_idx = r_headers.index('target_id') if 'target_id' in r_headers else -1
        type_idx = r_headers.index('relationship_type') if 'relationship_type' in r_headers else -1
        
        # Collect valid IDs from controls, risks, events
        valid_control_ids = controls_data['pk_values'] if controls_data else set()
        valid_risk_ids = risks_data['pk_values'] if risks_data else set()
        valid_event_ids = events_data['pk_values'] if events_data else set()
        
        all_valid_ids = valid_control_ids.union(valid_risk_ids).union(valid_event_ids)
        
        # Check relationship types
        rel_types = []
        broken_source_refs = []
        broken_target_refs = []
        
        for r in rel_data['rows']:
            s_id = r[source_idx].strip() if source_idx != -1 and source_idx < len(r) else ""
            t_id = r[target_idx].strip() if target_idx != -1 and target_idx < len(r) else ""
            rel_type = r[type_idx].strip() if type_idx != -1 and type_idx < len(r) else ""
            
            if rel_type:
                rel_types.append(rel_type)
                
            if s_id not in all_valid_ids:
                broken_source_refs.append((s_id, rel_type, t_id))
            if t_id not in all_valid_ids:
                broken_target_refs.append((s_id, rel_type, t_id))
                
        # Report relationship types
        unique_rel_types = set(rel_types)
        print(f"\nRelationship types found in relationships_seed.csv:")
        for rt in sorted(unique_rel_types):
            count = rel_types.count(rt)
            print(f"  - {rt}: {count} occurrences")
            
        # Report broken references in relationships
        print(f"\nReference Check: source_id and target_id integrity")
        
        if broken_source_refs or broken_target_refs:
            print(f"  -> WARNING: Broken references found in relationships!")
            for s_id, rel_type, t_id in broken_source_refs:
                print(f"     * Source ID '{s_id}' in ({s_id} -{rel_type}-> {t_id}) not found in controls, risks, or events.")
            for s_id, rel_type, t_id in broken_target_refs:
                print(f"     * Target ID '{t_id}' in ({s_id} -{rel_type}-> {t_id}) not found in controls, risks, or events.")
        else:
            print(f"  -> OK: All sources and targets in relationships exist in entity tables.")

    # 3. Explicit identification requested in Step 1 guidelines
    print(f"\n==================================================")
    print(f"SUMMARY FOR LESSON PLAN AUDIT")
    print(f"==================================================")
    print(f"1. Node classes identified in data:")
    print(f"   - RuiRo (from risk_profiles_seed.csv)")
    print(f"   - KiemSoat (from controls_seed.csv)")
    print(f"   - SuKienRuiRo (from risk_events_seed.csv)")
    print(f"2. Relationship types identified:")
    print(f"   - MITIGATES")
    print(f"   - OBSERVED_AS")
    print(f"3. Missing master data warning:")
    print(f"   - Cột 'owner_unit_id' (trong risk_profiles_seed.csv) chỉ là mã tham chiếu, hiện chưa có master data phòng ban tương ứng.")
    print(f"   - Cột 'owner_role_id' (trong controls_seed.csv) chỉ là mã tham chiếu, hiện chưa có master data vai trò/chức danh tương ứng.")

if __name__ == "__main__":
    main()
