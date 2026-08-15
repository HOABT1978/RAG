// Neo4j constraints for Wiki Risk Graph MVP
CREATE CONSTRAINT rui_ro_id IF NOT EXISTS FOR (node:RuiRo) REQUIRE node.id IS UNIQUE;
CREATE CONSTRAINT kiem_soat_id IF NOT EXISTS FOR (node:KiemSoat) REQUIRE node.id IS UNIQUE;
CREATE CONSTRAINT su_kien_rui_ro_id IF NOT EXISTS FOR (node:SuKienRuiRo) REQUIRE node.id IS UNIQUE;
