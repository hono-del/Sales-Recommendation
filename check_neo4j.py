import sys
import io
from neo4j import GraphDatabase

# UTF-8出力を強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'recommendation'))

with driver.session() as session:
    # 基本的な接続確認
    print("=== Neo4j 接続確認 ===\n")
    
    # 全ノード数
    result = session.run("MATCH (n) RETURN count(n) AS total")
    total = result.single()['total']
    print(f"総ノード数: {total:,}")
    
    # ノードタイプ別の数
    print("\n=== ノードタイプ別 ===")
    result = session.run("MATCH (n) RETURN labels(n)[0] AS type, count(*) AS count ORDER BY count DESC")
    for record in result:
        print(f"  {record['type']:<25} {record['count']:>6,}")
    
    # Need ノードの存在確認
    print("\n=== Need ノード確認 ===")
    result = session.run("MATCH (n:Need) RETURN count(n) AS count")
    need_count = result.single()['count']
    print(f"Need ノード数: {need_count}")
    
    # Consumer-HAS_NEED リレーションシップ確認
    print("\n=== HAS_NEED リレーションシップ確認 ===")
    result = session.run("MATCH (c:Consumer)-[r:HAS_NEED]->(n:Need) RETURN count(r) AS count")
    has_need_count = result.single()['count']
    print(f"HAS_NEED リレーション数: {has_need_count:,}")
    
    # サンプルデータ確認
    if has_need_count > 0:
        print("\n=== サンプル HAS_NEED データ ===")
        result = session.run("""
            MATCH (c:Consumer)-[:HAS_NEED]->(n:Need)
            RETURN c.id AS consumer_id, n.name AS need_name, n.label AS need_label
            LIMIT 5
        """)
        for record in result:
            print(f"  Consumer {record['consumer_id']} → {record['need_name']} ({record['need_label']})")
    else:
        print("\n⚠ HAS_NEED リレーションシップが存在しません")
        print("   → Consumer と Need が接続されていない可能性があります")
    
    # ChildSafety の接続確認
    print("\n=== ChildSafety Need 確認 ===")
    result = session.run("MATCH (n:Need {name: 'ChildSafety'}) RETURN n.name AS name, n.label AS label")
    child_safety = result.single()
    if child_safety:
        print(f"  ChildSafety ノードは存在します: {child_safety['label']}")
        
        # ChildSafety に関心を持つ消費者数
        result = session.run("MATCH (c:Consumer)-[:HAS_NEED]->(n:Need {name: 'ChildSafety'}) RETURN count(c) AS count")
        consumer_count = result.single()['count']
        print(f"  ChildSafety に関心を持つ消費者数: {consumer_count:,}")
    else:
        print("  ⚠ ChildSafety ノードが見つかりません")

driver.close()
