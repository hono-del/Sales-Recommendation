import sys
import io
from neo4j import GraphDatabase

# UTF-8出力を強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'recommendation'))

with driver.session() as session:
    result = session.run('''
        MATCH (n:Need)
        RETURN n.name AS name, n.label AS label, n.group AS group
        ORDER BY n.group, n.name
    ''')
    
    needs = [dict(r) for r in result]
    print(f'Total Needs: {len(needs)}')
    print()
    
    # グループ別に表示
    current_group = None
    for need in needs:
        if need['group'] != current_group:
            current_group = need['group']
            print(f'\n=== {current_group} ===')
        print(f'  {need["name"]:<35} {need["label"]}')

driver.close()
