"use client";

import { useState } from "react";
import type { Recommendation, ExcludedModel } from "@/types/demo";
import type { DelegationLevel } from "@/stores/demoStore";
import { RecommendationCard } from "./RecommendationCard";

type Props = {
  recommendations: Recommendation[];
  excluded: ExcludedModel[];
  delegationLevel: DelegationLevel;
};

/**
 * Maximizer（徹底比較型）向けレイアウト
 * - 3候補を横並び比較表形式で表示
 * - 除外車種をデフォルト表示
 * - 比較しやすい情報密度
 */
export function MaximizerRecommendLayout({
  recommendations,
  excluded,
  delegationLevel,
}: Props) {
  const [showExcluded, setShowExcluded] = useState(true); // デフォルトON

  return (
    <section>
      <div className="text-center">
        <h1 className="text-3xl font-light text-navy">
          あなたへのおすすめ
        </h1>
        <p className="mt-2 text-text-muted">
          3台を徹底比較しました。それぞれの長所・短所を明確にしています。
        </p>
      </div>

      {/* 比較表形式（横並び3列） */}
      <div className="mt-10 grid grid-cols-1 items-stretch gap-6 md:grid-cols-3">
        {recommendations.map((item, i) => (
          <div key={item.model} className="flex flex-col">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium text-navy">
                候補 {i + 1}
              </span>
              <span className="text-xs text-text-muted">
                スコア: {item.score.toFixed(1)}
              </span>
            </div>
            <RecommendationCard
              item={item}
              rank={i + 1}
              delegationLevel={delegationLevel}
            />
            {/* 長所・短所を追加 */}
            {item.appeal_points && item.appeal_points.length > 0 && (
              <div className="mt-3 rounded-md bg-surface p-3">
                <p className="text-xs font-medium text-success">長所</p>
                <ul className="mt-1 space-y-1 text-xs text-text-muted">
                  {item.appeal_points.map((point, idx) => (
                    <li key={idx}>✓ {point}</li>
                  ))}
                </ul>
              </div>
            )}
            {item.gap_vs_top && item.gap_vs_top.length > 0 && i > 0 && (
              <div className="mt-2 rounded-md bg-surface p-3">
                <p className="text-xs font-medium text-text-muted">
                  1位との差
                </p>
                <ul className="mt-1 space-y-1 text-xs text-text-muted">
                  {item.gap_vs_top.map((gap, idx) => (
                    <li key={idx}>△ {gap}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 除外車種セクション（デフォルト表示） */}
      {excluded.length > 0 && (
        <div className="mt-10">
          <button
            type="button"
            onClick={() => setShowExcluded((v) => !v)}
            className="flex items-center gap-2 text-sm text-navy underline"
          >
            <span>{showExcluded ? "▼" : "▶"}</span>
            なぜ外した？（{excluded.length}台）
          </button>
          {showExcluded && (
            <div className="mt-4 rounded-md border border-border bg-surface p-4">
              <p className="mb-3 text-sm font-medium text-text">
                除外した車種も含め、全ての選択肢を検討いただけます
              </p>
              <ul className="space-y-2 text-sm">
                {excluded.map((ex) => (
                  <li key={ex.model} className="text-text-muted">
                    <span className="font-medium text-text">{ex.model}</span>
                    {" — "}
                    {ex.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 詳細比較表へのリンク */}
      <div className="mt-6 text-center">
        <p className="text-sm text-text-muted">
          より詳細なスペック比較は「詳しい理由を見る」からご確認いただけます
        </p>
      </div>
    </section>
  );
}
