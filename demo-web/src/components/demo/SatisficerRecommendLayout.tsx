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
 * Satisficer（十分型）向けレイアウト
 * - 1位を大きく強調表示
 * - 2位・3位は小さく参考表示
 * - シンプルで決定を促す
 */
export function SatisficerRecommendLayout({
  recommendations,
  excluded,
  delegationLevel,
}: Props) {
  const [showOthers, setShowOthers] = useState(false); // デフォルトOFF

  const topRec = recommendations[0];
  const otherRecs = recommendations.slice(1);

  if (!topRec) return null;

  return (
    <section>
      <div className="text-center">
        <h1 className="text-3xl font-light text-navy">
          あなたに最適な1台
        </h1>
        <p className="mt-2 text-text-muted">
          あなたの条件を満たす最適な1台が見つかりました
        </p>
      </div>

      {/* 1位を大きく表示 */}
      <div className="mx-auto mt-10 max-w-md">
        <div className="mb-4 flex items-center justify-center gap-2">
          <span className="rounded-full bg-navy px-4 py-1 text-sm font-medium text-white">
            おすすめ
          </span>
        </div>
        <RecommendationCard
          item={topRec}
          rank={1}
          delegationLevel={delegationLevel}
        />

        {/* 「この1台で十分な理由」セクション */}
        <div className="mt-6 rounded-md bg-surface p-4">
          <h3 className="text-sm font-medium text-navy">
            この1台で十分な理由
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-text-muted">
            {topRec.appeal_points && topRec.appeal_points.length > 0 ? (
              topRec.appeal_points.slice(0, 3).map((point, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="mt-0.5 text-success">✓</span>
                  <span>{point}</span>
                </li>
              ))
            ) : (
              <>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-success">✓</span>
                  <span>ご予算の範囲内で最適な選択</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-success">✓</span>
                  <span>必要な乗車人数に対応</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-success">✓</span>
                  <span>あなたの価値観に最もマッチ</span>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>

      {/* 他の選択肢（折りたたみ） */}
      {otherRecs.length > 0 && (
        <div className="mx-auto mt-10 max-w-2xl">
          <button
            type="button"
            onClick={() => setShowOthers((v) => !v)}
            className="flex items-center gap-2 text-sm text-navy underline"
          >
            <span>{showOthers ? "▼" : "▶"}</span>
            参考：他の選択肢を見る
          </button>
          {showOthers && (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {otherRecs.map((item, i) => (
                <div key={item.model} className="opacity-75">
                  <p className="mb-2 text-xs text-text-muted">
                    参考 {i + 2}
                  </p>
                  <RecommendationCard
                    item={item}
                    rank={i + 2}
                    delegationLevel={delegationLevel}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 除外車種セクション（折りたたみ） */}
      {excluded.length > 0 && showOthers && (
        <div className="mx-auto mt-6 max-w-2xl">
          <details className="text-sm">
            <summary className="cursor-pointer text-text-muted underline">
              除外した車種（{excluded.length}台）
            </summary>
            <ul className="mt-3 space-y-2 rounded-md border border-border bg-surface p-4 text-sm">
              {excluded.map((ex) => (
                <li key={ex.model} className="text-text-muted">
                  <span className="font-medium text-text">{ex.model}</span>
                  {" — "}
                  {ex.reason}
                </li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </section>
  );
}
