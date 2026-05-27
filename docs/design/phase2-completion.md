# Phase 2 完了メモ — KG Visualization

**完了日**: 2026-05-26

## 成果物

| WBS | 内容 | 状態 |
|-----|------|------|
| W2.1 | `graph-path` API + Neo4j Cypher | ✅ |
| W2.2 | `KnowledgeGraphView`（force-graph, phase 0→6） | ✅ |
| W2.3 | `WhyPanel` + `NarrationBar` | ✅ |
| W2.4 | Recommendation 完全版（除外・Delegation・訴求ポイント） | ✅ |
| W2.5 | KG パフォーマンス（キャッシュ・シミュレーション短縮） | ✅ |

## バックエンド

- **`api/demo/graph_path_service.py`**
  - セッション profile → Need マッチで Cypher 実行
  - 推薦1位車種を自動解決（`recommend_for_session`）
  - Neo4j 不可時は fallback JSON をプロファイルで上書き
  - 120秒 TTL のインメモリキャッシュ、ノード上限 50
- **`api/demo/router.py`** — `GET .../graph-path` をサービス経由に変更
- **`api/demo/recommend_service.py`** — `appeal_points` / `fuel_type` 等を Neo4j から付与

## フロントエンド

- **`KnowledgeGraphView`** — `react-force-graph-2d`、段階アニメーション
- **`WhyPanel`** / **`NarrationBar`**
- **`GraphClient`** — 推薦を先読みし `top_model` 付きで graph-path 取得
- **`RecommendClient`** / **`RecommendationCard`** — Delegation 連動・訴求タグ
- **`DelegationClient`** — 推薦画面への影響説明

## テスト

```powershell
py -m pytest tests/test_phase2_graph_path.py tests/test_demo_api.py tests/test_phase1_recommend.py -q
```

## デモ確認

```powershell
.\start-demo.ps1
```

Opening → Questions(5) → Delegation → **Graph** → Recommend

## Phase 3 へ

- SCR-06 Dealer / SCR-07 Closing 本番品質
- F-007, F-008, F-013
