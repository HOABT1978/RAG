import os
import csv
import sys
import io

# Set stdout/stderr to UTF-8 to prevent console printing encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(project_dir, 'data')
    output_dir = os.path.join(project_dir, 'outputs')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Paths to source files
    risks_path = os.path.join(data_dir, 'risk_profiles_seed.csv')
    controls_path = os.path.join(data_dir, 'controls_seed.csv')
    events_path = os.path.join(data_dir, 'risk_events_seed.csv')
    relations_path = os.path.join(data_dir, 'relationships_seed.csv')
    
    # 1. Read source CSV files
    risks = []
    if os.path.exists(risks_path):
        with open(risks_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            risks = [dict(row) for row in reader]
            
    controls = []
    if os.path.exists(controls_path):
        with open(controls_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            controls = [dict(row) for row in reader]
            
    events = []
    if os.path.exists(events_path):
        with open(events_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            events = [dict(row) for row in reader]
            
    relations_raw = []
    if os.path.exists(relations_path):
        with open(relations_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            relations_raw = [dict(row) for row in reader]
            
    # 2. Build Entities list
    entities = []
    entity_ids = set()
    
    # Column mapping for entities.csv
    # We define all headers to merge the structures
    entity_headers = [
        'id', 'type', 'name', 'description', 'source_file', 'data_origin', 'verification_status',
        # Risk specific attributes
        'category', 'cause', 'event', 'impact', 'inherent_level', 'residual_level', 'owner_unit_id',
        # Control specific attributes
        'control_type', 'frequency', 'owner_role_id', 'effectiveness',
        # Event specific attributes
        'occurred_at', 'discovered_at', 'severity', 'loss_amount_vnd'
    ]
    
    # Map Risk Profiles (RuiRo)
    for r in risks:
        r_id = r['id'].strip()
        entity_ids.add(r_id)
        entities.append({
            'id': r_id,
            'type': 'RuiRo',
            'name': r['name'].strip(),
            'description': r['description'].strip(),
            'source_file': 'risk_profiles_seed.csv',
            'data_origin': r['data_origin'].strip(),
            'verification_status': r['verification_status'].strip(),
            'category': r['category'].strip(),
            'cause': r['cause'].strip(),
            'event': r['event'].strip(),
            'impact': r['impact'].strip(),
            'inherent_level': r['inherent_level'].strip(),
            'residual_level': r['residual_level'].strip(),
            'owner_unit_id': r['owner_unit_id'].strip(),
            'control_type': '', 'frequency': '', 'owner_role_id': '', 'effectiveness': '',
            'occurred_at': '', 'discovered_at': '', 'severity': '', 'loss_amount_vnd': ''
        })
        
    # Map Controls (KiemSoat)
    for c in controls:
        c_id = c['id'].strip()
        entity_ids.add(c_id)
        entities.append({
            'id': c_id,
            'type': 'KiemSoat',
            'name': c['name'].strip(),
            'description': '', # Controls seed does not have a description column
            'source_file': 'controls_seed.csv',
            'data_origin': c['data_origin'].strip(),
            'verification_status': c['verification_status'].strip(),
            'category': '', 'cause': '', 'event': '', 'impact': '', 'inherent_level': '', 'residual_level': '', 'owner_unit_id': '',
            'control_type': c['control_type'].strip(),
            'frequency': c['frequency'].strip(),
            'owner_role_id': c['owner_role_id'].strip(),
            'effectiveness': c['effectiveness'].strip(),
            'occurred_at': '', 'discovered_at': '', 'severity': '', 'loss_amount_vnd': ''
        })
        
    # Map Risk Events (SuKienRuiRo)
    for e in events:
        e_id = e['id'].strip()
        entity_ids.add(e_id)
        entities.append({
            'id': e_id,
            'type': 'SuKienRuiRo',
            'name': f"Sự kiện rủi ro {e_id}", # Generate a name or use description/ID
            'description': e['description'].strip(),
            'source_file': 'risk_events_seed.csv',
            'data_origin': e['data_origin'].strip(),
            'verification_status': e['verification_status'].strip(),
            'category': '', 'cause': '', 'event': '', 'impact': '', 'inherent_level': '', 'residual_level': '', 'owner_unit_id': '',
            'control_type': '', 'frequency': '', 'owner_role_id': '', 'effectiveness': '',
            'occurred_at': e['occurred_at'].strip(),
            'discovered_at': e['discovered_at'].strip(),
            'severity': e['severity'].strip(),
            'loss_amount_vnd': e['loss_amount_vnd'].strip()
        })
        
    # 3. Write entities.csv
    entities_out_path = os.path.join(output_dir, 'entities.csv')
    with open(entities_out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=entity_headers)
        writer.writeheader()
        for ent in entities:
            writer.writerow(ent)
            
    print(f"Normalized entities saved to: {entities_out_path}")
    print(f"Total entities: {len(entities)}")
    
    # Count by type
    type_counts = {}
    for ent in entities:
        t = ent['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    print("Entity counts by type:")
    for t, cnt in type_counts.items():
        print(f"  - {t}: {cnt}")
        
    # 4. Build Relations list
    relations = []
    orphan_errors = []
    
    relation_headers = [
        'source_id', 'relationship_type', 'target_id', 'source',
        'evidence_quote', 'confidence', 'verification_status', 'data_origin'
    ]
    
    # Process and validate relationships
    for rel in relations_raw:
        s_id = rel['source_id'].strip()
        t_id = rel['target_id'].strip()
        rel_type = rel['relationship_type'].strip()
        
        # Check for orphan references
        if s_id not in entity_ids:
            orphan_errors.append(f"Orphan reference: source_id '{s_id}' not found in entities.csv (relation: {s_id} -{rel_type}-> {t_id})")
        if t_id not in entity_ids:
            orphan_errors.append(f"Orphan reference: target_id '{t_id}' not found in entities.csv (relation: {s_id} -{rel_type}-> {t_id})")
            
        relations.append({
            'source_id': s_id,
            'relationship_type': rel_type,
            'target_id': t_id,
            'source': rel['source'].strip(),
            'evidence_quote': rel['evidence_quote'].strip(),
            'confidence': rel['confidence'].strip(),
            'verification_status': rel['verification_status'].strip(),
            'data_origin': rel['data_origin'].strip()
        })
        
    # 5. Write relations.csv
    relations_out_path = os.path.join(output_dir, 'relations.csv')
    with open(relations_out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=relation_headers)
        writer.writeheader()
        for rel in relations:
            writer.writerow(rel)
            
    print(f"\nNormalized relations saved to: {relations_out_path}")
    print(f"Total relations: {len(relations)}")
    
    # Count by type
    rel_counts = {}
    for rel in relations:
        rt = rel['relationship_type']
        rel_counts[rt] = rel_counts.get(rt, 0) + 1
    print("Relation counts by relationship_type:")
    for rt, cnt in rel_counts.items():
        print(f"  - {rt}: {cnt}")
        
    # Report orphans
    print(f"\nOrphan reference validation:")
    if orphan_errors:
        print(f"  -> WARNING/ERROR: {len(orphan_errors)} orphan references found:")
        for err in orphan_errors:
            print(f"     * {err}")
    else:
        print("  -> OK: No orphan references detected.")

if __name__ == '__main__':
    main()
