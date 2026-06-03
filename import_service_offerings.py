"""
ServiceOffering ノードを Neo4j に追加するスクリプト

Excel ファイル: docs/0602_service-offerings-catalog_reviewed.xlsx
"""
import sys
import io
import pandas as pd
from neo4j import GraphDatabase

# UTF-8出力を強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Neo4j接続
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'recommendation'))

# Excelファイル読み込み
df = pd.read_excel('docs/0602_service-offerings-catalog_reviewed.xlsx')

# ヘッダー行を除外
df = df[df['id'] != '案ID（英小文字・数字・_）※']

print(f"=== ServiceOffering インポート開始 ===")
print(f"総サービス数: {len(df)}\n")

with driver.session() as session:
    # 1. 既存のServiceOfferingノードを削除（クリーンスタート）
    result = session.run("MATCH (s:ServiceOffering) DETACH DELETE s")
    print("✓ 既存の ServiceOffering ノードを削除しました\n")
    
    # 2. ServiceOfferingノードを作成
    created_count = 0
    for idx, row in df.iterrows():
        service_id = str(row['id']).strip() if pd.notna(row['id']) else None
        if not service_id:
            continue
        
        # プロパティを準備
        props = {
            'id': service_id,
            'title': str(row['title']) if pd.notna(row['title']) else '',
            'one_liner': str(row['one_liner']) if pd.notna(row['one_liner']) else '',
            'direction': str(row['direction']) if pd.notna(row['direction']) else 'neutral',
            'domain': str(row['domain']) if pd.notna(row['domain']) else '',
            'lifecycle': str(row['lifecycle']) if pd.notna(row['lifecycle']) else '',
            'value_shift': str(row['value_shift_1']) if pd.notna(row['value_shift_1']) else '',
            'pitch_template': str(row['pitch_template']) if pd.notna(row['pitch_template']) else '',
            'eligibility': str(row['eligibility']) if pd.notna(row['eligibility']) else '',
            'need_rationale': str(row['need_rationale']) if pd.notna(row['need_rationale']) else '',
        }
        
        # ServiceOfferingノード作成
        session.run("""
            CREATE (s:ServiceOffering {
                id: $id,
                title: $title,
                one_liner: $one_liner,
                direction: $direction,
                domain: $domain,
                lifecycle: $lifecycle,
                value_shift: $value_shift,
                pitch_template: $pitch_template,
                eligibility: $eligibility,
                need_rationale: $need_rationale
            })
        """, **props)
        
        created_count += 1
        
        # 3. Need とのリレーションを構築
        needs = []
        for i in range(1, 6):  # primary_need_1-3, secondary_need_1-2
            col_name = f'primary_need_{i}' if i <= 3 else f'secondary_need_{i-3}'
            need_name = str(row[col_name]).strip() if pd.notna(row.get(col_name)) else None
            if need_name and need_name != 'nan':
                priority = i if i <= 3 else i + 10  # primary: 1-3, secondary: 11-12
                needs.append((need_name, priority))
        
        for need_name, priority in needs:
            # Need が存在するか確認して ADDRESSES リレーション作成
            result = session.run("""
                MATCH (s:ServiceOffering {id: $service_id})
                MATCH (n:Need {name: $need_name})
                MERGE (s)-[r:ADDRESSES {priority: $priority}]->(n)
                RETURN count(r) AS cnt
            """, service_id=service_id, need_name=need_name, priority=priority)
            if result.single()['cnt'] == 0:
                print(f"  ⚠ Need '{need_name}' が見つかりません（サービス: {service_id}）")
        
        # 4. ValueAxis とのリレーションを構築
        value_axes = []
        for i in range(1, 3):
            col_name = f'value_axis_{i}'
            axis = str(row[col_name]).strip() if pd.notna(row.get(col_name)) else None
            if axis and axis != 'nan':
                value_axes.append(axis)
        
        for axis in value_axes:
            # ValueAxis の仮想ノードは作らず、プロパティとして保存
            # 推薦ロジックで直接参照
            pass
        
        # 5. Load Label の記録（プロパティとして保存）
        load_labels = []
        for i in range(1, 3):
            col_name = f'load_label_{i}'
            load = str(row[col_name]).strip() if pd.notna(row.get(col_name)) else None
            if load and load != 'nan':
                load_labels.append(load)
        
        if load_labels:
            session.run("""
                MATCH (s:ServiceOffering {id: $service_id})
                SET s.load_labels = $load_labels
            """, service_id=service_id, load_labels=load_labels)
        
        # value_axes もプロパティとして保存
        if value_axes:
            session.run("""
                MATCH (s:ServiceOffering {id: $service_id})
                SET s.value_axes = $value_axes
            """, service_id=service_id, value_axes=value_axes)
    
    print(f"✓ {created_count} 個の ServiceOffering ノードを作成しました\n")
    
    # 6. 統計情報を表示
    print("=== 統計情報 ===")
    
    # Direction 分布
    result = session.run("""
        MATCH (s:ServiceOffering)
        RETURN s.direction AS direction, count(*) AS cnt
        ORDER BY cnt DESC
    """)
    print("\nDirection 分布:")
    for record in result:
        print(f"  {record['direction']:<15} {record['cnt']:>3}件")
    
    # Domain 分布
    result = session.run("""
        MATCH (s:ServiceOffering)
        RETURN s.domain AS domain, count(*) AS cnt
        ORDER BY cnt DESC
    """)
    print("\nDomain 分布:")
    for record in result:
        print(f"  {record['domain']:<20} {record['cnt']:>3}件")
    
    # Need 接続状況
    result = session.run("""
        MATCH (s:ServiceOffering)-[:ADDRESSES]->(n:Need)
        RETURN count(DISTINCT s) AS services_with_needs,
               count(*) AS total_connections
    """)
    record = result.single()
    print(f"\nNeed 接続状況:")
    print(f"  Need と接続されたサービス: {record['services_with_needs']}件")
    print(f"  総接続数: {record['total_connections']}件")
    
    # サンプル表示
    print("\n=== サンプル (最初の3件) ===")
    result = session.run("""
        MATCH (s:ServiceOffering)
        OPTIONAL MATCH (s)-[r:ADDRESSES]->(n:Need)
        WITH s, collect({need: n.label, priority: r.priority}) AS needs
        RETURN s.id AS id,
               s.title AS title,
               s.direction AS direction,
               s.domain AS domain,
               needs
        ORDER BY s.id
        LIMIT 3
    """)
    for record in result:
        print(f"\n【{record['id']}】 {record['title']}")
        print(f"  Direction: {record['direction']}")
        print(f"  Domain: {record['domain']}")
        print(f"  Needs: {[n['need'] for n in record['needs'] if n['need']][:3]}")

driver.close()
print("\n✓ インポート完了")
