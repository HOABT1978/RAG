// ===========================================================================
// CÁC CÂU TRUY VẤN MẪU DUYỆT ĐỒ THỊ - BUỔI 14
// ===========================================================================

// --- QUERY A: Xem toàn bộ đồ thị của Buổi 14 ---
MATCH (n {lab_session: "buoi_14"})-[r]->(m {lab_session: "buoi_14"})
RETURN n, r, m
LIMIT 100;


// --- QUERY B: Truy vấn các điều khoản thuộc một văn bản ---
MATCH (v:VanBan {lab_session: "buoi_14"})-[:CONTAINS]->(d:DieuKhoan)
RETURN v.id AS van_ban_id, v.title AS tieu_de, d.id AS dieu_khoan_id, d.article AS dieu_so, d.text AS noi_dung
LIMIT 50;


// --- QUERY C: Xem chuỗi liên tiếp các điều khoản (mối quan hệ NEXT) ---
MATCH (d1:DieuKhoan {lab_session: "buoi_14"})-[:NEXT]->(d2:DieuKhoan)-[:NEXT]->(d3:DieuKhoan)
RETURN d1.id AS dieu_1, d2.id AS dieu_2, d3.id AS dieu_3
LIMIT 10;


// --- QUERY D: Truy vấn các mối quan hệ liên kết giữa các văn bản pháp lý ---
MATCH (v1:VanBan {lab_session: "buoi_14"})-[r]->(v2:VanBan {lab_session: "buoi_14"})
WHERE type(r) IN ["SUA_DOI_BO_SUNG", "CAN_CU", "VAN_BAN_BO_SUNG", "THAY_THE", "HOP_NHAT"]
RETURN v1.id AS tu_van_ban, v1.so_ky_hieu AS so_hieu_1, type(r) AS loai_quan_he, v2.id AS toi_van_ban, v2.so_ky_hieu AS so_hieu_2;
