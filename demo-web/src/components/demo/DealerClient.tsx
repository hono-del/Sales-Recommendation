"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { PrimaryButton } from "./PrimaryButton";

type DealerTalk = {
  insight: {
    customer_type: string;
    scenes: string[];
    anxieties: string[];
    values: string[];
  };
  talk_script: string;
  generated_by?: string;
};

export function DealerClient() {
  const router = useRouter();
  const sessionId = useRequireSession();
  const delegationLevel = useDemoStore((s) => s.delegationLevel);
  const recommendations = useDemoStore((s) => s.recommendations);
  const demoFallback = useDemoStore((s) => s.demoFallback);
  const [talk, setTalk] = useState<DealerTalk | null>(null);
  const [loading, setLoading] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false);

  const topModel = recommendations[0]?.model ?? "";
  const topScore = recommendations[0]?.score ?? 0;

  useEffect(() => {
    if (!sessionId || !topModel || isInitialized) return;
    
    console.log("[DealerClient] Fetching dealer talk for:", { topModel, delegationLevel });
    setIsInitialized(true);
    
    api
      .postDealerTalk(sessionId, {
        top_model: topModel,
        delegation_level: delegationLevel,
      })
      .then((data) => {
        console.log("[DealerClient] API response:", data);
        setTalk(data);
      })
      .catch((error) => {
        console.error("[DealerClient] API error:", error);
        setTalk({
          insight: {
            customer_type: "バランス型",
            scenes: ["日常利用"],
            anxieties: ["後悔", "維持費"],
            values: ["安心", "効率"],
          },
          talk_script:
            "お客様の重視ポイントに合わせ、試乗で実感していただく提案が有効です。",
          generated_by: "template",
        });
      })
      .finally(() => setLoading(false));
  }, [sessionId, topModel, delegationLevel, isInitialized]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-text-muted">
        販売店向けトークを準備中…
      </div>
    );
  }

  const insight = talk?.insight;
  const matchScore = topScore ? Math.round(topScore * 100) : 92;

  return (
    <main className="mx-auto max-w-[1100px] px-6 py-10">
      <h1 className="text-center text-3xl font-light text-navy">販売店サポート</h1>
      <p className="mt-2 text-center text-text-muted">
        KG ベースの顧客インサイト＋提案トーク
      </p>
      
      {/* KPI summary */}
      <div className="mt-8 grid grid-cols-3 gap-4">
        <div className="rounded-md border border-border bg-surface p-4 text-center">
          <p className="text-2xl font-light text-navy">{matchScore}%</p>
          <p className="mt-1 text-xs text-text-muted">マッチ度</p>
        </div>
        <div className="rounded-md border border-border bg-surface p-4 text-center">
          <p className="text-2xl font-light text-navy">{topModel || "—"}</p>
          <p className="mt-1 text-xs text-text-muted">推薦車種</p>
        </div>
        <div className="rounded-md border border-border bg-surface p-4 text-center">
          <p className="text-2xl font-light text-navy">{insight?.customer_type || "—"}</p>
          <p className="mt-1 text-xs text-text-muted">顧客タイプ</p>
        </div>
      </div>
      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="rounded-md border border-gold/30 bg-surface p-6">
          <div className="mb-4 flex items-center gap-2">
            <span className="text-2xl">👤</span>
            <h2 className="text-lg font-medium text-navy">顧客インサイト</h2>
          </div>
          {insight && (
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="font-medium text-navy">タイプ</dt>
                <dd className="text-text-muted">{insight.customer_type}</dd>
              </div>
              <div>
                <dt className="font-medium text-navy">シーン</dt>
                <dd className="text-text-muted">{insight.scenes.join("、")}</dd>
              </div>
              <div>
                <dt className="font-medium text-navy">不安</dt>
                <dd className="text-text-muted">{insight.anxieties.join("、")}</dd>
              </div>
              <div>
                <dt className="font-medium text-navy">価値観</dt>
                <dd className="text-text-muted">{insight.values.join("、")}</dd>
              </div>
            </dl>
          )}
        </div>
        <div className="rounded-md border border-navy/20 bg-surface p-6">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">💬</span>
              <h2 className="text-lg font-medium text-navy">提案トーク</h2>
            </div>
            {talk?.generated_by === "llm" && (
              <span className="rounded-full bg-gold/10 px-3 py-1 text-xs font-medium text-gold">
                AI生成
              </span>
            )}
          </div>
          <div className="rounded-md bg-bg p-4">
            <p className="whitespace-pre-line text-sm leading-relaxed text-text">
              {talk?.talk_script}
            </p>
          </div>
          <p className="mt-3 text-xs text-text-muted">
            {talk?.generated_by === "llm"
              ? "※ Claude API による顧客プロファイル個別生成"
              : "※ テンプレート生成。LLM 統合で完全パーソナライズ可能"}
          </p>
        </div>
      </div>
      <div className="mt-10 rounded-md border border-border bg-surface p-6">
        <h3 className="text-base font-medium text-navy">次のアクション</h3>
        <ul className="mt-3 space-y-2 text-sm text-text">
          <li className="flex items-start gap-2">
            <span className="text-success">✓</span>
            <span>試乗予約（家族同伴を推奨）</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-success">✓</span>
            <span>グレード・オプション相談</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-success">✓</span>
            <span>購入後サポート（AXIS）案内</span>
          </li>
        </ul>
      </div>

      <div className="mt-12 flex flex-col items-center gap-4">
        <PrimaryButton onClick={() => router.push("/demo/closing")}>
          購入後体験を見る
        </PrimaryButton>
        <button
          type="button"
          onClick={() => router.push("/demo/recommend")}
          className="text-sm text-navy underline"
        >
          ← おすすめに戻る
        </button>
      </div>
    </main>
  );
}
