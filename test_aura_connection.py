from neo4j import GraphDatabase

try:
    driver = GraphDatabase.driver(
        'neo4j+s://25257eca.databases.neo4j.io',
        auth=('neo4j', 'QkO185nprozriIlwgthTJC9Iiksgu2td')
    )
    driver.verify_connectivity()
    print('✓ Neo4j Aura接続成功')
    
    result = driver.execute_query('MATCH (n) RETURN count(n) as total')
    total_nodes = result.records[0]['total']
    print(f'ノード数: {total_nodes}')
    
    # Consumer数確認
    result2 = driver.execute_query('MATCH (c:Consumer) RETURN count(c) as consumers')
    consumer_count = result2.records[0]['consumers']
    print(f'Consumerノード数: {consumer_count}')
    
    # VehicleModel数確認
    result3 = driver.execute_query('MATCH (v:VehicleModel) RETURN count(v) as vehicles')
    vehicle_count = result3.records[0]['vehicles']
    print(f'VehicleModelノード数: {vehicle_count}')
    
    driver.close()
    print('\n✓ データが存在します。Renderで使用できます。')
except Exception as e:
    print(f'✗ 接続エラー: {e}')
