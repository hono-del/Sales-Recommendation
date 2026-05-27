"""
batch_llm_extractor.py
----------------------
Anthropic Batch API を使い、rule_based_extractor.py の出力に
decision_style と regret を補完する（50%割引）。

使い方:
  python extractor/batch_llm_extractor.py          # バッチ送信 → batch_id を表示
  python extractor/batch_llm_extractor.py --poll   # 結果取得・マージ（完了後に実行）
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import anthropic

DECISIONS_PATH = Path("data/processed/consumer_decisions.json")
STORIES_PATH   = Path("data/raw/consumer_stories.json")
BATCH_ID_FILE  = Path("data/processed/.batch_id")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """あなたは消費者の購買意思決定を分析する専門家です。
与えられた情報から指定のJSON形式のみで出力してください。"""

PROMPT_TEMPLATE = """以下の自動車購入ストーリーから、decision_style と regret のみを抽出してください。

車種: {vehicle_model}
満足度: {satisfaction_score}/5
購入きっかけ: {kikkake}
ストーリー（概要）: {story_summary}
決め手: {deciding_factor}

出力形式（JSONのみ）:
{{
  "decision_style": "<Maximizer=徹底比較型 | Satisficer=十分型 | Authority-driven=権威依存型 | Delegator=委任型 | Intuitive=直感型 | Impulsive=衝動型>",
  "regret": [
    {{
      "category": "<fuel_cost | cargo_space | ride_quality | size_too_large | size_too_small | price | maintenance | design | technology | other>",
      "description": "<後悔の内容（1文）>",
      "severity": <1-3>
    }}
  ]
}}

注意:
- decision_style は1つだけ選択
- regret は満足度1-3または不満表現がある場合のみ記入。なければ []
- JSONのみ返す"""


def _build_prompt(story: dict) -> str:
    st = story.get("story_text", {})
    if isinstance(st, dict):
        summary      = (st.get("purchase_story", "") or "")[:300]
        deciding     = (st.get("deciding_factor", "") or "")[:150]
    else:
        text     = str(st)
        summary  = text[:300]
        deciding = text[300:450]

    return PROMPT_TEMPLATE.format(
        vehicle_model     = story.get("vehicle_model", "不明"),
        satisfaction_score= story.get("satisfaction_score", "不明"),
        kikkake           = story.get("kikkake", "不明")[:100],
        story_summary     = summary,
        deciding_factor   = deciding,
    )


def submit_batch(stories: list[dict], client: anthropic.Anthropic) -> str:
    """全ストーリーをバッチ送信し batch_id を返す。"""
    requests = []
    for story in stories:
        requests.append({
            "custom_id": story["story_id"],
            "params": {
                "model":      "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "system":     SYSTEM_PROMPT,
                "messages":   [{"role": "user", "content": _build_prompt(story)}],
            },
        })

    print(f"バッチ送信: {len(requests)} 件...")
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch ID: {batch.id}")
    print(f"ステータス: {batch.processing_status}")
    BATCH_ID_FILE.write_text(batch.id, encoding="utf-8")
    print(f"Batch ID を保存しました: {BATCH_ID_FILE}")
    return batch.id


def poll_and_merge(batch_id: str, client: anthropic.Anthropic):
    """バッチ結果を取得し decisions に decision_style / regret をマージ。"""
    print(f"バッチ結果を確認中: {batch_id}")
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        status = batch.processing_status
        print(f"  ステータス: {status} "
              f"(成功:{batch.request_counts.succeeded} / "
              f"エラー:{batch.request_counts.errored} / "
              f"処理中:{batch.request_counts.processing})")
        if status == "ended":
            break
        print("  30秒後に再確認...")
        time.sleep(30)

    # 結果を story_id → {decision_style, regret} にマップ
    results: dict[str, dict] = {}
    for result in client.messages.batches.results(batch_id):
        sid = result.custom_id
        if result.result.type == "succeeded":
            raw = result.result.message.content[0].text.strip()
            try:
                if raw.startswith("```"):
                    raw = re.sub(r"^```\w*\n?", "", raw)
                    raw = re.sub(r"\n?```$", "", raw)
                parsed = json.loads(raw)
                results[sid] = {
                    "decision_style": parsed.get("decision_style"),
                    "regret":         parsed.get("regret", []),
                }
            except json.JSONDecodeError:
                results[sid] = {"decision_style": "Satisficer", "regret": []}
        else:
            results[sid] = {"decision_style": "Satisficer", "regret": []}

    # decisions.json にマージ
    decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    updated = 0
    for d in decisions:
        sid = d.get("story_id")
        if sid in results:
            d["decision_style"] = results[sid]["decision_style"]
            d["regret"]         = results[sid]["regret"]
            updated += 1

    DECISIONS_PATH.write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n{updated} 件の decision_style / regret を更新しました")
    print(f"次のステップ: python graph/graph_builder.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--poll", action="store_true",
                        help="バッチ結果を取得してマージ（送信後に実行）")
    parser.add_argument("--batch-id", default=None,
                        help="ポーリング対象の Batch ID（省略時はファイルから読む）")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    if args.poll:
        # --- ポーリング・マージモード ---
        batch_id = args.batch_id
        if not batch_id:
            if BATCH_ID_FILE.exists():
                batch_id = BATCH_ID_FILE.read_text(encoding="utf-8").strip()
            else:
                print("[ERROR] Batch ID が見つかりません。--batch-id で指定してください")
                sys.exit(1)
        poll_and_merge(batch_id, client)

    else:
        # --- 送信モード ---
        stories = json.loads(STORIES_PATH.read_text(encoding="utf-8"))
        print(f"ストーリー読み込み: {len(stories)} 件")

        # decision_style が未設定のものだけ対象
        decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8")) if DECISIONS_PATH.exists() else []
        done_ids  = {d["story_id"] for d in decisions if d.get("decision_style")}
        pending   = [s for s in stories if s["story_id"] not in done_ids]
        print(f"送信対象: {len(pending)} 件（decision_style 未設定）")

        if not pending:
            print("すべて処理済みです")
            return

        submit_batch(pending, client)
        print("\nバッチ送信完了。通常 1〜24時間で処理されます。")
        print("完了後に以下を実行してください:")
        print("  python extractor/batch_llm_extractor.py --poll")


if __name__ == "__main__":
    main()
