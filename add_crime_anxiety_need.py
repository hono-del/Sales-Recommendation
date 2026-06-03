"""
新しいNeed「CrimeAnxietyReduction（防犯不安を減らしたい）」をNeo4jに追加
"""
import sys
import io
from neo4j import GraphDatabase

# UTF-8出力を強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'recommendation'))

with driver.session() as session:
    # 1. 既存のCrimeAnxietyReductionがあるか確認
    result = session.run("MATCH (n:Need {name: 'CrimeAnxietyReduction'}) RETURN count(n) AS cnt")
    existing = result.single()['cnt']
    
    if existing > 0:
        print(f"✓ CrimeAnxietyReduction は既に存在しています（{existing}件）")
    else:
        # 2. 新しいNeedノードを作成
        session.run("""
            CREATE (n:Need {
                name: 'CrimeAnxietyReduction',
                label: '防犯不安を減らしたい',
                group: 'Safety'
            })
        """)
        print("✓ CrimeAnxietyReduction ノードを作成しました")
    
    # 3. SafetyPerformance Capability との接続を確認・作成
    result = session.run("""
        MATCH (n:Need {name: 'CrimeAnxietyReduction'})
        MATCH (c:Capability {name: 'SafetyPerformance'})
        MERGE (c)-[:SUPPORTS]->(n)
        RETURN count(*) AS cnt
    """)
    print(f"✓ SafetyPerformance -[:SUPPORTS]-> CrimeAnxietyReduction 接続を確認しました")
    
    # 4. 最終確認：全Needノード数
    result = session.run("MATCH (n:Need) RETURN count(n) AS total")
    total = result.single()['total']
    print(f"\n現在のNeed総数: {total}個")
    
    # 5. Safetyグループの一覧
    print("\n=== Safetyグループの全Need ===")
    result = session.run("""
        MATCH (n:Need {group: 'Safety'})
        RETURN n.name AS name, n.label AS label
        ORDER BY n.name
    """)
    for record in result:
        print(f"  {record['name']:<30} {record['label']}")

driver.close()
print("\n✓ 完了")
