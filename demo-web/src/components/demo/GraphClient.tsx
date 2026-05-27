"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { DELEGATION_GRAPH_HINT } from "@/lib/delegation-ui";
import { ensureSessionSynced } from "@/lib/session-sync";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { DemoBanner } from "./DemoBanner";
import { KnowledgeGraphView } from "./KnowledgeGraphView";
import { WhyPanel } from "./WhyPanel";
import { NarrationBar } from "./NarrationBar";
import { PrimaryButton } from "./PrimaryButton";
import {
  MAX_ANIMATION_PHASE,
  PHASE_DURATION_MS,
} from "@/lib/graph-animation";
import type { GraphPathData } from "@/types/graph";

export function GraphClient() {
  const router = useRouter();
  const sessionId = useRequireSession();
  const demoFallback = useDemoStore((s) => s.demoFallback);
  const delegationLevel = useDemoStore((s) => s.delegationLevel);
  const answers = useDemoStore((s) => s.answers);
  const setRecommendations = useDemoStore((s) => s.setRecommendations);
  const setDemoFallbackStore = useDemoStore((s) => s.setDemoFallback);
  const [data, setData] = useState<GraphPathData | null>(null);
  const [loading, setLoading] = useState(true);
  const [phase, setPhase] = useState(0);
  const [animDone, setAnimDone] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

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
        if (answers.length >= 4) {
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
          } catch {
            /* graph-path は top_model なしでも可 */
          }
        }

        const d = await api.getGraphPath(sid, topModel);
        if (!cancelled) setData(d as GraphPathData);
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sessionId, answers.length, setRecommendations, setDemoFallbackStore]);

  useEffect(() => {
    if (loading || !data?.nodes.length) return;
    if (reducedMotion) {
      setPhase(MAX_ANIMATION_PHASE);
      setAnimDone(true);
      return;
    }
    if (phase >= MAX_ANIMATION_PHASE) {
      setAnimDone(true);
      return;
    }
    const t = setTimeout(() => setPhase((p) => p + 1), PHASE_DURATION_MS);
    return () => clearTimeout(t);
  }, [loading, data, phase, reducedMotion]);

  const skipAnimation = useCallback(() => {
    setPhase(MAX_ANIMATION_PHASE);
    setAnimDone(true);
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-text-muted">
        グラフを構築中…
      </div>
    );
  }

  if (!data?.nodes?.length) {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <p className="text-text-muted">グラフデータを取得できませんでした。</p>
        <div style={{ marginTop: 24 }}>
          <PrimaryButton onClick={() => router.push("/demo/recommend")}>
            おすすめ車種を見る
          </PrimaryButton>
        </div>
      </div>
    );
  }

  const showWhy = phase >= 2;
  const showCta = animDone || reducedMotion;

  return (
    <>
      {(demoFallback || data.demo_fallback) && <DemoBanner />}
      <main className="mx-auto max-w-[1280px] px-6 py-8">
        <header className="mb-6">
          <h1 className="text-2xl font-light text-navy">なぜこの提案か</h1>
          <p className="mt-2 text-sm text-text-muted">
            {DELEGATION_GRAPH_HINT[delegationLevel]}
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[55fr_45fr]">
          <div className="min-w-0">
            <KnowledgeGraphView
              nodes={data.nodes}
              edges={data.edges}
              animationPhase={phase}
            />
            {!animDone && !reducedMotion && (
              <button
                type="button"
                onClick={skipAnimation}
                className="mt-2 text-xs text-text-muted underline hover:text-navy"
              >
                アニメーションをスキップ
              </button>
            )}
          </div>
          <div>
            {data.why_panel && (
              <WhyPanel data={data.why_panel} visible={showWhy} />
            )}
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <NarrationBar active={!animDone} />
          <div className="flex justify-center">
            <PrimaryButton
              disabled={!showCta}
              onClick={() => router.push("/demo/recommend")}
            >
              {showCta ? "おすすめ車種を見る" : "グラフを構築中…"}
            </PrimaryButton>
          </div>
        </div>
      </main>
    </>
  );
}
