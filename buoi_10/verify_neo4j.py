"""
Verification - Buổi 10
Kiểm tra số lượng các thực thể và quan hệ đã được nạp vào cơ sở dữ liệu Neo4j.
"""

from neo4j import GraphDatabase

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Mquan@2004"
NEO4J_DB = "kb-hops"

def main():
    print(f"🔌 Kết nối tới Neo4j để xác minh dữ liệu...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # Xác định database
    db_name = NEO4J_DB
    try:
        with driver.session(database=NEO4J_DB) as session:
            session.run("RETURN 1")
    except Exception:
        db_name = None
        
    print(f"📂 Đang kiểm tra trên cơ sở dữ liệu: '{db_name if db_name else 'default'}'\n")
    
    queries = {
        "Số lượng Document nodes (yêu cầu: 15)": "MATCH (d:Document) RETURN count(d) AS count",
        "Số lượng Chunk nodes": "MATCH (c:Chunk) RETURN count(c) AS count",
        "Số lượng quan hệ [:PART_OF] (Chunk ➔ Document)": "MATCH ()-[r:PART_OF]->() RETURN count(r) AS count",
        "Số lượng quan hệ [:PARENT_OF] (Parent Chunk ➔ Child Chunk)": "MATCH ()-[r:PARENT_OF]->() RETURN count(r) AS count",
        "Số lượng quan hệ [:NEXT] (Sibling Chunk ➔ Sibling Chunk)": "MATCH ()-[r:NEXT]->() RETURN count(r) AS count",
        "Số lượng quan hệ chéo giữa các Document (yêu cầu: 8)": "MATCH (d1:Document)-[r]->(d2:Document) RETURN count(r) AS count"
    }
    
    with driver.session(database=db_name) as session:
        for desc, query in queries.items():
            result = session.run(query)
            record = result.single()
            count = record["count"] if record else 0
            print(f"📊 {desc}: {count}")
            
        print("\n🔍 Ví dụ các loại quan hệ chéo giữa các tài liệu:")
        rel_query = "MATCH (d1:Document)-[r]->(d2:Document) RETURN d1.id AS from_doc, type(r) AS rel_type, d2.id AS to_doc, r.relationship AS desc LIMIT 10"
        result = session.run(rel_query)
        for rec in result:
            print(f"  - ({rec['from_doc']}) -[:{rec['rel_type']}]-> ({rec['to_doc']}) | Mô tả: {rec['desc']}")
            
    driver.close()

if __name__ == "__main__":
    main()
