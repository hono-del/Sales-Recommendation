"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { DelegationSelector } from "./DelegationSelector";
import { PrimaryButton } from "./PrimaryButton";

const MESSAGES: Record<string, string> = {
  guide: "AIは候補を提示します。最終判断はあなたにお任せします。",
  co_pilot: "AIが伴走しながら、一緒に納得解を探します。",
  auto: "AIが最適案を提案します。理由もあわせてご確認ください。",
};

const IMPACT: Record<string, string> = {
  guide: "推薦画面では理由の全文と除外理由の詳細を表示します。",
  co_pilot: "推薦画面ではスコアと理由をバランスよく表示します。",
  auto: "推薦画面ではスコアと結論を優先し、理由は1行に要約します。",
};

export function DelegationClient() {
  const router = useRouter();
  const sessionId = useRequireSession();
  const delegationLevel = useDemoStore((s) => s.delegationLevel);
  const setDelegationLevel = useDemoStore((s) => s.setDelegationLevel);
  const [message, setMessage] = useState(MESSAGES[delegationLevel]);
  const [loading, setLoading] = useState(false);

  async function handleSelect(level: "guide" | "co_pilot" | "auto") {
    setDelegationLevel(level);
    setMessage(MESSAGES[level]);
    if (sessionId) {
      try {
        const res = await api.setDelegation(sessionId, level);
        setMessage(res.message);
      } catch {
        /* ローカル選択のみ */
      }
    }
  }

  async function handleContinue() {
    if (!sessionId) return;
    setLoading(true);
    try {
      await api.setDelegation(sessionId, delegationLevel);
      await api.postEvent(sessionId, {
        screen_id: "SCR-03",
        event_type: "cta_click",
        payload: { delegation_level: delegationLevel },
      });
    } finally {
      setLoading(false);
    }
    router.push("/demo/graph");
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 text-center">
      <h1 className="text-3xl font-light text-navy">AIとの付き合い方を教えてください</h1>
      <p className="mt-4 text-text-muted">
        あなたの意思決定スタイルに合わせて、AIの関わり方を調整します。
      </p>
      <DelegationSelector selected={delegationLevel} onSelect={handleSelect} />
      <p className="mt-8 min-h-[3rem] text-base text-text">{message}</p>
      <p className="mt-2 text-sm text-text-muted">{IMPACT[delegationLevel]}</p>
      <div className="mt-10">
        <PrimaryButton onClick={handleContinue} disabled={loading}>
          {loading ? "準備中…" : "納得の理由を見る"}
        </PrimaryButton>
      </div>
    </main>
  );
}
