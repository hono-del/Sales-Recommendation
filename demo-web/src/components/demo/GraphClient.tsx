"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import { DELEGATION_GRAPH_HINT } from "@/lib/delegation-ui";
import { ensureSessionSynced } from "@/lib/session-sync";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { DemoBanner } from "./DemoBanner";
import { ThinkingStoryView, STEP_COUNT } from "./ThinkingStoryView";
import { NarrationBar } from "./NarrationBar";
import { PrimaryButton } from "./PrimaryButton";
import { StyleAwareRecommendSection } from "./StyleAwareRecommendSection";
import type { GraphPathData } from "@/types/graph";

const STEP_DURATION_MS = 900;

export function GraphClient() {
  const sessionId = useRequireSession();
  const demoFallback = useDemoStore((s) => s.demoFallback);
  const delegationLevel = useDemoStore((s) => s.delegationLevel);
  const answers = useDemoStore((s) => s.answers);
  const recommendations = useDemoStore((s) => s.recommendations);
  const excluded = useDemoStore((s) => s.excluded);
  const setRecommendations = useDemoStore((s) => s.setRecommendations);
  const setDemoFallbackStore = useDemoStore((s) => s.setDemoFallback);
  const decisionStyle = useDemoStore((s) => s.decisionStyle);
  const [data, setData] = useState<GraphPathData | null>(null);
  const [loading, setLoading] = useState(true);
  const [phase, setPhase] = useState(0);
  const [animDone, setAnimDone] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const recommendRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const onChange = () => setReducedMotion(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    (async () => {
      try {
        const sid = await ensureSessionSynced();
        if (cancelled) return;

        let topModel: string | undefined;
        if (recommendations.length >= 1) {
          topModel = recommendations[0].model;
        } else if (answers.length >= 4) {
          try {
            const rec = await api.postRecommend(sid);
            if (!cancelled && rec.recommendations?.length) {
              topModel = rec.recommendations[0].model;
              setRecommendations(
                rec.recommendations,
                rec.excluded ?? [],
                rec.demo_fallback,
              );
              setDemoFallbackStore(rec.demo_fallback);
            }
          } catch (e) {
            console.warn("[GraphClient] recommend failed:", e);
          }
        }

        const d = await api.getGraphPath(sid, topModel);
        if (!cancelled) setData(d as GraphPathData);
      } catch (error) {
        console.error("[GraphClient] graph-path error:", error);
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    sessionId,
    answers.length,
    recommendations,
    setRecommendations,
    setDemoFallbackStore,
  ]);

  useEffect(() => {
    if (loading || !data?.thinking_process) return;
    if (reducedMotion) {
      setPhase(STEP_COUNT);
      setAnimDone(true);
      return;
    }
    if (phase >= STEP_COUNT) {
      setAnimDone(true);
      return;
    }
    const t = setTimeout(() => setPhase((p) => p + 1), STEP_DURATION_MS);
    return () => clearTimeout(t);
  }, [loading, data, phase, reducedMotion]);

  const skipAnimation = useCallback(() => {
    setPhase(STEP_COUNT);
    setAnimDone(true);
  }, []);

  const handleExpandRecommend = useCallback(() => {
    setExpanded(true);
    requestAnimationFrame(() => {
      recommendRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-text-muted">
        提案の根拠を構築中…
      </div>
    );
  }

  if (!data?.thinking_process) {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <p className="text-text-muted">データを取得できませんでした。</p>
      </div>
    );
  }

  const tp = data.thinking_process;
  const mergedDecisionStyle = tp.decision_style ?? (decisionStyle
    ? {
        name: decisionStyle.name,
        label: decisionStyle.label,
        description: decisionStyle.description,
        confidence: decisionStyle.confidence,
        secondary_label: decisionStyle.secondaryLabel,
        is_mixed: decisionStyle.isMixed,
      }
    : undefined);
  const thinkingForView = {
    ...tp,
    decision_style: mergedDecisionStyle,
    style_presentation: tp.style_presentation,
  };
  const showCta = animDone || reducedMotion;

  return (
    <>
      {(demoFallback || data.demo_fallback) && <DemoBanner />}
      <main className="mx-auto max-w-4xl px-6 py-8 pb-24">
        <header className="mb-12 text-center">
          <h1 className="text-3xl font-light text-navy">なぜこの提案か</h1>
          <p className="mt-3 text-sm text-text-muted">
            {DELEGATION_GRAPH_HINT[delegationLevel] ||
              "条件で絞り込み、価値観と負荷から体験を導き、一台にたどり着きます"}
          </p>
        </header>

        <ThinkingStoryView
          data={thinkingForView}
          animationPhase={phase}
          sessionId={sessionId ?? undefined}
          topModel={
            recommendations[0]?.model ??
            thinkingForView.vehicle?.name
          }
        />

        {!animDone && !reducedMotion && (
          <div className="mt-8 text-center">
            <button
              type="button"
              onClick={skipAnimation}
              className="text-xs text-text-muted underline hover:text-navy"
            >
              アニメーションをスキップ
            </button>
          </div>
        )}

        <div className="mt-12 space-y-4">
          <NarrationBar active={!animDone} />
          <div className="flex justify-center">
            <PrimaryButton disabled={!showCta} onClick={handleExpandRecommend}>
              {expanded
                ? "詳細を確認中…"
                : showCta
                  ? "おすすめ車種の詳細を見る"
                  : "思考中…"}
            </PrimaryButton>
          </div>
        </div>

        {expanded && (
          <div
            ref={recommendRef}
            id="recommend-expanded"
            className="mt-16 scroll-mt-8 border-t border-border pt-12"
          >
            <h2 className="text-center text-2xl font-light text-navy">
              あなたへのおすすめ（詳細）
            </h2>
            <p className="mt-2 text-center text-sm text-text-muted">
              上記の思考プロセスを経て、以下の3台が選ばれました
            </p>

            {recommendations.length > 0 ? (
              <div className="mt-10">
                <StyleAwareRecommendSection
                  presentation={thinkingForView.style_presentation}
                  recommendations={recommendations}
                  excluded={excluded}
                  delegationLevel={delegationLevel}
                />
              </div>
            ) : (
              <p className="mt-8 text-center text-text-muted">
                推薦データを読み込めませんでした。ページを再読み込みしてください。
              </p>
            )}
          </div>
        )}
      </main>
    </>
  );
}
