"use client";

import { useEffect, useState } from "react";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { api } from "@/lib/api-client";
import { ServiceOfferingSection } from "./ServiceOfferingSection";
import { PrimaryButton } from "./PrimaryButton";
import { useRouter } from "next/navigation";

type ServiceOffering = {
  id: string;
  title: string;
  one_liner: string;
  direction: "upgrade" | "downgrade" | "neutral";
  domain: string;
  score: number;
  matched_needs: string[];
  matched_loads: string[];
  value_alignment: number;
  pitch: string;
  need_rationale: string;
};

export function ServiceRecommendClient() {
  const router = useRouter();
  const sessionId = useRequireSession();
  const answers = useDemoStore((s) => s.answers);

  const [services, setServices] = useState<ServiceOffering[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    
    const validSessionId = sessionId; // 型ガード

    async function fetchServices() {
      try {
        setLoading(true);
        setError(null);
        
        const data = await api.getServiceRecommendations(validSessionId);
        setServices((data.services || []) as ServiceOffering[]);
      } catch (e) {
        console.error("サービス推薦エラー:", e);
        setError(e instanceof Error ? e.message : "サービス推薦の取得に失敗しました");
      } finally {
        setLoading(false);
      }
    }

    fetchServices();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-navy border-t-transparent"></div>
          <p className="mt-4 text-text-muted">
            あなたに最適なサービスを分析中...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-[840px] px-6 py-10">
        <div className="rounded-md border border-load/40 bg-load/10 p-6 text-center">
          <p className="mb-4 text-navy">{error}</p>
          <PrimaryButton onClick={() => router.push("/demo/opening")}>
            最初に戻る
          </PrimaryButton>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1024px] px-6 py-10">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-navy">
          あなたにおすすめのサービス
        </h2>
        <p className="mt-2 text-text-muted">
          ご回答いただいた価値観から、最適なサービスを提案します
        </p>
      </div>

      {answers.length > 0 && (
        <div className="mb-6 rounded-md border border-border bg-surface p-4">
          <h3 className="mb-2 text-sm font-medium text-navy">回答内容</h3>
          <div className="flex flex-wrap gap-2">
            {answers.map((a) => (
              <span
                key={a.question_id}
                className="rounded-full bg-navy/10 px-3 py-1 text-xs text-navy"
              >
                Q{a.question_index}
              </span>
            ))}
          </div>
        </div>
      )}

      <ServiceOfferingSection services={services} loading={false} />

      {services.length > 0 && (
        <div className="mt-8 text-center">
          <p className="text-sm text-text-muted">
            これらのサービスについて、詳しくお知りになりたい場合はお問い合わせください
          </p>
        </div>
      )}

      <div className="mt-12 flex justify-center gap-4">
        <button
          onClick={() => router.push("/demo/service/reasoning")}
          className="rounded-md border border-navy px-6 py-3 text-sm font-medium text-navy transition-colors hover:bg-navy/5"
        >
          提案の理由を見る
        </button>
        <button
          onClick={() => router.push("/demo/service/questions")}
          className="rounded-md border border-border px-6 py-3 text-sm font-medium text-text transition-colors hover:bg-surface"
        >
          質問に戻る
        </button>
        <PrimaryButton onClick={() => router.push("/demo/opening")}>
          最初に戻る
        </PrimaryButton>
      </div>
    </div>
  );
}
