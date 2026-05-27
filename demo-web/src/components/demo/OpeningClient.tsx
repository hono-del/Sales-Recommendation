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
  { label: "価格", left: "15%", top: "58%", delay: "4s" },
  { label: "家族", left: "38%", top: "62%", delay: "4.4s" },
  { label: "趣味", left: "65%", top: "56%", delay: "4.8s" },
  { label: "アップグレード", left: "85%", top: "60%", delay: "5.2s" },
  { label: "維持費", left: "18%", top: "78%", delay: "5.6s" },
  { label: "走行性能", left: "48%", top: "82%", delay: "6s" },
  { label: "積載性", left: "78%", top: "76%", delay: "6.4s" },
  { label: "4WD", left: "5%", top: "28%", delay: "6.8s" },
  { label: "ハイブリッド", left: "90%", top: "26%", delay: "7.2s" },
  { label: "快適性", left: "35%", top: "24%", delay: "7.6s" },
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
      router.push("/demo/profile");
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
              padding: "10px 18px",
              fontSize: "16px",
              fontWeight: 500,
              color: "var(--color-text-muted)",
              background: "rgba(255, 255, 255, 0.92)",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
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
            fontSize: "48px",
            fontWeight: 700,
            lineHeight: 1.2,
            color: "var(--color-navy)",
            textShadow: "0 2px 4px rgba(255,255,255,0.8)",
          }}
        >
          Decision Intelligence
        </h1>
        <p
          style={{
            marginTop: "20px",
            fontSize: "22px",
            fontWeight: 600,
            color: "var(--color-navy)",
            background: "rgba(255,255,255,0.85)",
            padding: "8px 16px",
            borderRadius: "8px",
            display: "inline-block",
          }}
        >
          「最適なもの」を探すほど、決めることが難しくなる。
        </p>
        <p
          style={{
            marginTop: "32px",
            fontSize: "18px",
            lineHeight: 1.7,
            fontWeight: 500,
            color: "var(--color-navy)",
            background: "rgba(255,255,255,0.9)",
            padding: "16px 24px",
            borderRadius: "12px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
          }}
        >
          SDV の進化でモビリティは移動手段から、生活体験のパートナーへ。
          <br />
          <br />
          サービスや情報が溢れる世の中で、
          <br />
          私たちは
          <strong style={{ fontWeight: 700, color: "var(--color-gold)" }}>
            「感情的負荷のない納得できる選択」
          </strong>
          を支えます。
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
