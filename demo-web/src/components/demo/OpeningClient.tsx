"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type StorageStatusResponse } from "@/lib/api-client";
import { useDemoStore } from "@/stores/demoStore";
import { PrimaryButton } from "./PrimaryButton";

// Supabase ダッシュボード（プロジェクト復旧用）
const SUPABASE_DASHBOARD_URL =
  "https://supabase.com/dashboard/project/vgkojkjsqfpphywcahqk";

/** ストレージ（Supabase）接続ステータスバッジ */
function StorageStatusBadge() {
  const [status, setStatus] = useState<StorageStatusResponse | null>(null);
  const [checking, setChecking] = useState(true);
  const [expanded, setExpanded] = useState(false);

  async function checkStatus() {
    setChecking(true);
    try {
      const s = await api.getStorageStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    checkStatus();
    // 60秒ごとに自動再チェック
    const timer = setInterval(checkStatus, 60000);
    return () => clearInterval(timer);
  }, []);

  // 状態判定
  const isConnected = status?.use_supabase === true && status?.supabase_read_ok === true;
  const isDisconnected = status?.use_supabase === true && status?.supabase_read_ok === false;
  const isLocalMode = status?.use_supabase === false;

  let dotColor = "#9CA3AF"; // グレー（確認中/不明）
  let label = "確認中...";
  if (!checking || status) {
    if (isConnected) {
      dotColor = "#22C55E"; // 緑
      label = "Supabase 接続中";
    } else if (isDisconnected) {
      dotColor = "#EF4444"; // 赤
      label = "Supabase 未接続";
    } else if (isLocalMode) {
      dotColor = "#3B82F6"; // 青
      label = "ローカル保存モード";
    } else if (!status) {
      dotColor = "#9CA3AF";
      label = "状態不明";
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        right: "16px",
        bottom: "16px",
        zIndex: 50,
        maxWidth: "340px",
      }}
    >
      {/* 未接続時の警告パネル */}
      {isDisconnected && expanded && (
        <div
          style={{
            marginBottom: "8px",
            background: "#FEF2F2",
            border: "1px solid #FECACA",
            borderRadius: "12px",
            padding: "16px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            fontSize: "13px",
            lineHeight: 1.6,
            color: "#7F1D1D",
          }}
        >
          <p style={{ fontWeight: 700, marginBottom: "8px" }}>
            ⚠️ フィードバックの永続保存が無効です
          </p>
          <p style={{ marginBottom: "12px" }}>
            Supabase プロジェクトが一時停止されている可能性があります。
            現在のログは一時保存のみで、サーバー再起動時に消えます。
          </p>
          <p style={{ fontWeight: 600, marginBottom: "6px" }}>復旧手順：</p>
          <ol style={{ paddingLeft: "18px", marginBottom: "12px" }}>
            <li>下のボタンから Supabase を開く</li>
            <li>「Restore project」をクリック</li>
            <li>数分待つと自動的に再接続されます</li>
          </ol>
          <a
            href={SUPABASE_DASHBOARD_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "block",
              textAlign: "center",
              background: "#3ECF8E",
              color: "#FFFFFF",
              fontWeight: 700,
              padding: "10px 16px",
              borderRadius: "8px",
              textDecoration: "none",
            }}
          >
            Supabase ダッシュボードを開く →
          </a>
          <button
            onClick={checkStatus}
            style={{
              display: "block",
              width: "100%",
              marginTop: "8px",
              background: "transparent",
              border: "1px solid #FCA5A5",
              color: "#B91C1C",
              fontSize: "12px",
              padding: "6px",
              borderRadius: "8px",
              cursor: "pointer",
            }}
          >
            接続を再確認する
          </button>
        </div>
      )}

      {/* ステータスバッジ本体 */}
      <button
        onClick={() => (isDisconnected ? setExpanded(!expanded) : checkStatus())}
        title={
          isDisconnected
            ? "クリックで復旧手順を表示"
            : "クリックで再確認"
        }
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          marginLeft: "auto",
          background: "rgba(255,255,255,0.95)",
          border: `1px solid ${isDisconnected ? "#FECACA" : "var(--color-border)"}`,
          borderRadius: "999px",
          padding: "8px 14px",
          fontSize: "12px",
          fontWeight: 600,
          color: isDisconnected ? "#B91C1C" : "var(--color-text-muted)",
          boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
          cursor: "pointer",
        }}
      >
        <span
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: dotColor,
            flexShrink: 0,
            animation: checking ? "pulse 1s infinite" : undefined,
          }}
        />
        データ保存: {label}
        {isDisconnected && (
          <span style={{ fontSize: "10px" }}>{expanded ? "▼" : "▲"}</span>
        )}
      </button>
    </div>
  );
}

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
  const setRecommendationType = useDemoStore((s) => s.setRecommendationType);
  const setNeo4jConnected = useDemoStore((s) => s.setNeo4jConnected);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preparingApi, setPreparingApi] = useState(false);
  const [apiProgress, setApiProgress] = useState({ attempt: 0, elapsed: 0 });

  async function handleStart(type: "vehicle" | "service") {
    if (loading) return;
    setLoading(true);
    setError(null);
    setPreparingApi(true);
    setApiProgress({ attempt: 0, elapsed: 0 });
    
    try {
      reset();
      setRecommendationType(type);
      
      // APIが起動するまで待機
      const isReady = await api.waitForApiReady(
        (attempt, maxAttempts, elapsedSeconds) => {
          setApiProgress({ attempt, elapsed: elapsedSeconds });
        },
        20 // 最大20回リトライ（約60秒）
      );
      
      if (!isReady) {
        throw new Error("APIサーバーが応答しません。時間をおいて再度お試しください。");
      }
      
      setPreparingApi(false);
      
      // Neo4j接続確認（バックグラウンド）
      api
        .health()
        .then((h) => setNeo4jConnected(h.neo4j === "connected"))
        .catch(() => setNeo4jConnected(false));

      const session = await api.createSession();
      setSessionId(session.session_id);
      
      // サービスレコメンドの場合は質問ページへ直行
      if (type === "service") {
        router.push("/demo/service/questions");
      } else {
        router.push("/demo/profile");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "セッション開始に失敗しました");
      setLoading(false);
      setPreparingApi(false);
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
          <div style={{ display: "flex", gap: "20px", justifyContent: "center", flexWrap: "wrap" }}>
            <div style={{ minWidth: "240px", textAlign: "center" }}>
              <PrimaryButton onClick={() => handleStart("vehicle")} disabled={loading}>
                {loading ? "準備中…" : "車種レコメンド"}
              </PrimaryButton>
              <p style={{ marginTop: "8px", fontSize: "14px", color: "var(--color-text-muted)" }}>
                あなたに最適な車種を提案
              </p>
            </div>
            <div style={{ minWidth: "240px", textAlign: "center" }}>
              <PrimaryButton onClick={() => handleStart("service")} disabled={loading}>
                {loading ? "準備中…" : "サービスレコメンド"}
              </PrimaryButton>
              <p style={{ marginTop: "8px", fontSize: "14px", color: "var(--color-text-muted)" }}>
                最適なサービスを提案
              </p>
            </div>
          </div>
          {loading && (
            <div style={{ marginTop: "20px" }}>
              {preparingApi ? (
                <div style={{ 
                  background: "rgba(255,255,255,0.95)", 
                  padding: "20px", 
                  borderRadius: "12px",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.1)"
                }}>
                  <div style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    justifyContent: "center",
                    gap: "12px",
                    marginBottom: "12px"
                  }}>
                    <div 
                      className="animate-spin"
                      style={{
                        width: "24px",
                        height: "24px",
                        border: "3px solid var(--color-border)",
                        borderTop: "3px solid var(--color-navy)",
                        borderRadius: "50%"
                      }} 
                    />
                    <p style={{ 
                      fontSize: "16px", 
                      fontWeight: 600,
                      color: "var(--color-navy)" 
                    }}>
                      APIサーバーを起動中...
                    </p>
                  </div>
                  <p style={{ 
                    fontSize: "13px", 
                    color: "var(--color-text-muted)",
                    marginBottom: "8px"
                  }}>
                    初回アクセス時は起動に30秒〜1分程度かかります
                  </p>
                  {apiProgress.attempt > 0 && (
                    <p style={{ 
                      fontSize: "12px", 
                      color: "var(--color-text-muted)" 
                    }}>
                      接続試行: {apiProgress.attempt}回目 | 経過時間: {apiProgress.elapsed}秒
                    </p>
                  )}
                </div>
              ) : (
                <p style={{ fontSize: "13px", color: "var(--color-text-muted)" }}>
                  セッションを準備しています…
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ストレージ接続ステータス（右下固定） */}
      <StorageStatusBadge />
    </main>
  );
}
