"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { useDemoStore } from "@/stores/demoStore";
import { PrimaryButton } from "./PrimaryButton";

/** 浮遊タグの配置（left/top は %） */
const FLOATING_TAGS: { label: string; left: string; top: string; delay: string }[] = [
  { label: "EV", left: "6%", top: "14%", delay: "0s" },
  { label: "HEV", left: "24%", top: "10%", delay: "0.4s" },
  { label: "ADAS", left: "42%", top: "16%", delay: "0.8s" },
  { label: "コネクテッド", left: "62%", top: "11%", delay: "1.2s" },
  { label: "SUV", left: "82%", top: "15%", delay: "1.6s" },
  { label: "ミニバン", left: "10%", top: "38%", delay: "2s" },
  { label: "燃費", left: "30%", top: "42%", delay: "2.4s" },
  { label: "安全", left: "55%", top: "36%", delay: "2.8s" },
  { label: "デザイン", left: "72%", top: "40%", delay: "3.2s" },
  { label: "オプション", left: "88%", top: "34%", delay: "3.6s" },
];

export function OpeningClient() {
  const router = useRouter();
  const reset = useDemoStore((s) => s.reset);
  const setSessionId = useDemoStore((s) => s.setSessionId);
  const setNeo4jConnected = useDemoStore((s) => s.setNeo4jConnected);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      reset();
      // health は Neo4j 確認で遅いため待たずバックグラウンド実行
      api
        .health()
        .then((h) => setNeo4jConnected(h.neo4j === "connected"))
        .catch(() => setNeo4jConnected(false));

      const session = await api.createSession();
      setSessionId(session.session_id);
      router.push("/demo/questions");
    } catch (e) {
      setError(e instanceof Error ? e.message : "セッション開始に失敗しました");
      setLoading(false);
    }
  }

  return (
    <main
      style={{
        position: "relative",
        display: "flex",
        minHeight: "calc(100vh - 56px)",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        padding: "0 24px",
      }}
    >
      {/* 背景の浮遊タグ */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 0,
        }}
      >
        {FLOATING_TAGS.map((item) => (
          <span
            key={item.label}
            className="opening-float-tag"
            style={{
              position: "absolute",
              left: item.left,
              top: item.top,
              transform: "translate(-50%, -50%)",
              animationDelay: item.delay,
              whiteSpace: "nowrap",
              padding: "6px 12px",
              fontSize: "14px",
              color: "var(--color-text-muted)",
              background: "rgba(255, 255, 255, 0.88)",
              border: "1px solid var(--color-border)",
              borderRadius: "6px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.07)",
            }}
          >
            {item.label}
          </span>
        ))}
      </div>

      <div
        style={{
          position: "relative",
          zIndex: 10,
          maxWidth: "640px",
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontSize: "32px",
            fontWeight: 300,
            lineHeight: 1.3,
            color: "var(--color-navy)",
          }}
        >
          選択肢が多い時代
        </h1>
        <p
          style={{
            marginTop: "16px",
            fontSize: "18px",
            color: "var(--color-text-muted)",
          }}
        >
          「最適なもの」を探すほど、決めることが難しくなる。
        </p>
        <p
          style={{
            marginTop: "24px",
            fontSize: "16px",
            lineHeight: 1.6,
            color: "var(--color-text)",
          }}
        >
          SDV の進化で車は機能の集合体から、生活体験のパートナーへ。
          <br />
          私たちは Knowledge Graph で、なぜその一台かを一緒に見つけます。
        </p>
        {error && (
          <p style={{ marginTop: "16px", fontSize: "14px", color: "var(--color-load)" }} role="alert">
            {error}
          </p>
        )}
        <div style={{ marginTop: "40px", position: "relative", zIndex: 20 }}>
          <PrimaryButton onClick={handleStart} disabled={loading}>
            {loading ? "準備中…" : "体験を開始する"}
          </PrimaryButton>
          {loading && (
            <p style={{ marginTop: "12px", fontSize: "13px", color: "var(--color-text-muted)" }}>
              セッションを準備しています…
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
