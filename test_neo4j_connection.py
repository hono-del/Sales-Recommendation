# -*- coding: utf-8 -*-
"""Neo4j ローカル接続テスト"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from neo4j import GraphDatabase
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "recommendation")

print(f"接続先: {NEO4J_URI}")
print(f"ユーザー: {NEO4J_USER}")
print("-" * 50)

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print("[OK] ドライバー作成成功")
    
    driver.verify_connectivity()
    print("[OK] 接続確認成功")
    
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as total")
        record = result.single()
        total_nodes = record["total"]
        print(f"[OK] ノード総数: {total_nodes}")
    
    with driver.session() as session:
        result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
        record = result.single()
        total_rels = record["total"]
        print(f"[OK] リレーション総数: {total_rels}")
    
    driver.close()
    print("\n[SUCCESS] 接続テスト成功")
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    print("\n対処方法:")
    print("1. Docker Desktop が起動しているか確認")
    print("2. Neo4j コンテナが起動しているか確認:")
    print("   docker ps -a | findstr neo4j-poc")
    print("3. コンテナを起動:")
    print("   docker start neo4j-poc")
