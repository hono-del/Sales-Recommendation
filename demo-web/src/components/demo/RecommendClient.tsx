"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { ensureSessionSynced } from "@/lib/session-sync";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { DELEGATION_SUBTITLES } from "@/lib/delegation-ui";
import { DemoBanner } from "./DemoBanner";
import { RecommendationCard } from "./RecommendationCard";
import { PrimaryButton } from "./PrimaryButton";
import { ServiceOfferingSection } from "./ServiceOfferingSection";
import { MaximizerRecommendLayout } from "./MaximizerRecommendLayout";
import { SatisficerRecommendLayout } from "./SatisficerRecommendLayout";

function RestartLink() {
  const reset = useDemoStore((s) => s.reset);
  return (
    <Link
      href="/demo/opening"
      className="text-sm text-text-muted underline"
      onClick={() => reset()}
    >
      最初からやり直す
    </Link>
  );
}

export function RecommendClient() {
  const router = useRouter();
  useRequireSession();
  const delegationLevel = useDemoStore((s) => s.delegationLevel);
  const demoFallback = useDemoStore((s) => s.demoFallback);
  const recommendations = useDemoStore((s) => s.recommendations);
  const excluded = useDemoStore((s) => s.excluded);
  const answers = useDemoStore((s) => s.answers);
  const decisionStyle = useDemoStore((s) => s.decisionStyle);
  const setRecommendations = useDemoStore((s) => s.setRecommendations);
  const setDemoFallback = useDemoStore((s) => s.setDemoFallback);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);
  const [services, setServices] = useState<any[]>([]);
  const [servicesLoading, setServicesLoading] = useState(true);

  useEffect(() => {
    if (recommendations.length > 0) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        if (answers.length < 5) {
          throw new Error(
            "5問の回答が揃っていません。質問画面からやり直してください。",
          );
        }

        const sessionId = await ensureSessionSynced();
        if (cancelled) return;

        const res = await api.postRecommend(sessionId);
        if (cancelled) return;

        setRecommendations(res.recommendations, res.excluded, res.demo_fallback);
        setDemoFallback(res.demo_fallback);
        await api.postEvent(sessionId, {
          screen_id: "SCR-05",
          event_type: "enter",
        });
      } catch (e) {
        if (cancelled) return;
        const message =
          e instanceof Error ? e.message : "推薦の取得に失敗しました";

        // 最終手段: 静的 fallback
        try {
          const fb = await api.getFallbackRecommend();
          if (!cancelled && fb.recommendations?.length) {
            setRecommendations(
              fb.recommendations,
              fb.excluded ?? [],
              true,
            );
            setDemoFallback(true);
            setError(null);
            return;
          }
        } catch {
          /* ignore */
        }

        setError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    answers.length,
    recommendations.length,
    setRecommendations,
    setDemoFallback,
  ]);

  // サービス推薦の取得
  useEffect(() => {
    if (loading) return; // 車種推薦のロード中は待機
    
    let cancelled = false;

    (async () => {
      try {
        const sessionId = await ensureSessionSynced();
        if (cancelled) return;

        const data = await api.getServiceRecommendations(sessionId);
        if (cancelled) return;

        setServices(data.services || []);
      } catch (e) {
        console.error("Failed to load service recommendations:", e);
        setServices([]);
      } finally {
        if (!cancelled) setServicesLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [loading]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-text-muted">
        あなたに合う一台を分析中…
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <p className="text-load">{error}</p>
        <p className="mt-2 text-sm text-text-muted">
          API（port 8000）が起動しているか確認してください。
        </p>
        <div className="mt-6 flex flex-col items-center gap-3">
          <Link href="/demo/questions" className="text-navy underline">
            質問に戻る
          </Link>
          <RestartLink />
        </div>
      </div>
    );
  }

  // DecisionStyleに応じたレイアウト選択
  const renderRecommendations = () => {
    const styleName = decisionStyle?.name;

    switch (styleName) {
      case "Maximizer":
        return (
          <MaximizerRecommendLayout
            recommendations={recommendations}
            excluded={excluded}
            delegationLevel={delegationLevel}
          />
        );
      case "Satisficer":
        return (
          <SatisficerRecommendLayout
            recommendations={recommendations}
            excluded={excluded}
            delegationLevel={delegationLevel}
          />
        );
      default:
        // デフォルト表示
        return (
          <section>
            <h1 className="text-center text-3xl font-light text-navy">
              あなたへのおすすめ
            </h1>
            <p className="mt-2 text-center text-text-muted">
              {DELEGATION_SUBTITLES[delegationLevel]}
            </p>
            <div className="mt-10 grid grid-cols-1 items-stretch gap-6 md:grid-cols-2 lg:grid-cols-3">
              {recommendations.map((item, i) => (
                <RecommendationCard
                  key={item.model}
                  item={item}
                  rank={i + 1}
                  delegationLevel={delegationLevel}
                />
              ))}
            </div>
            {excluded.length > 0 && (
              <div className="mt-10">
                <button
                  type="button"
                  onClick={() => setShowExcluded((v) => !v)}
                  className="text-sm text-navy underline"
                >
                  {showExcluded ? "閉じる" : "なぜ外した？"}
                </button>
                {showExcluded && (
                  <ul className="mt-4 space-y-2 rounded-md border border-border bg-surface p-4 text-sm">
                    {excluded.map((ex) => (
                      <li key={ex.model} className="text-text-muted">
                        <span className="font-medium text-text">{ex.model}</span>
                        {" — "}
                        {ex.reason}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>
        );
    }
  };

  return (
    <>
      {demoFallback && <DemoBanner />}
      <main className="mx-auto max-w-[1280px] px-6 py-10">
        {/* セクション1: あなたへのおすすめ車種（DecisionStyleに応じて表示） */}
        {renderRecommendations()}

        {/* セクション2: おすすめサービス・オプション */}
        <section className="mt-16">
          <div className="text-center">
            <h2 className="text-2xl font-light text-navy">
              おすすめサービス・オプション
            </h2>
            <p className="mt-2 text-sm text-text-muted">
              あなたの価値観や負荷に合わせたアップグレード・サポートサービス
            </p>
          </div>
          <div className="mt-8">
            <ServiceOfferingSection services={services} loading={servicesLoading} />
          </div>
        </section>

        {/* アクションボタン */}
        <div
          className="mt-16 flex flex-col items-center gap-4"
          style={{ position: "relative", zIndex: 20 }}
        >
          <PrimaryButton onClick={() => router.push("/demo/graph")}>
            詳しい理由を見る
          </PrimaryButton>
          <button
            onClick={() => router.push("/demo/dealer")}
            className="rounded-md border border-navy px-6 py-3 text-sm font-medium text-navy transition-colors hover:bg-navy/5"
          >
            販売店提案へ
          </button>
          <RestartLink />
        </div>
      </main>
    </>
  );
}
