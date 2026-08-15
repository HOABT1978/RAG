// A. Xem toàn bộ graph (View the entire graph)
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m LIMIT 300;

// B. Tìm kiểm soát giảm thiểu một rủi ro (Find controls mitigating a specific risk, e.g., 'RR-001')
MATCH (c:KiemSoat)-[r:MITIGATES]->(risk:RuiRo {id: 'RR-001'})
RETURN c, r, risk;

// C. Tìm sự kiện của một rủi ro (Find occurred events for a specific risk, e.g., 'RR-001')
MATCH (risk:RuiRo {id: 'RR-001'})-[r:OBSERVED_AS]->(e:SuKienRuiRo)
RETURN risk, r, e;

// D. Tìm đường đi: KiemSoat -> RuiRo -> SuKienRuiRo (Find all 3-step pathways)
MATCH path = (c:KiemSoat)-[:MITIGATES]->(risk:RuiRo)-[:OBSERVED_AS]->(e:SuKienRuiRo)
RETURN path;

// E. Tìm rủi ro chưa có bất kỳ biện pháp kiểm soát nào (Find risks without any mitigating controls)
MATCH (risk:RuiRo)
WHERE NOT (:KiemSoat)-[:MITIGATES]->(risk)
RETURN risk.id AS risk_id, risk.name AS risk_name;

// F. Tìm các mối quan hệ chưa được xác thực (Find relationships that are not VERIFIED)
MATCH (source)-[r]->(target)
WHERE r.verification_status <> 'VERIFIED'
RETURN labels(source) AS source_label, source.id AS source_id, type(r) AS rel_type, r.verification_status AS status, target.id AS target_id, labels(target) AS target_label;
