"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api-client";

type KnowledgeBase = {
  all_needs: string[];
  all_loads: string[];
  all_services: Array<{
    id: string;
    title: string;
    one_liner: string;
    domain: string;
    direction: string;
  }>;
};

type SessionData = {
  matched_needs: string[];
  detected_loads: string[];
  recommended_services: Array<{
    id: string;
    title: string;
    score: number;
  }>;
};

function KnowledgeBaseContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");
  
  const [knowledge, setKnowledge] = useState<KnowledgeBase | null>(null);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<"needs" | "loads" | "services">("needs");

  useEffect(() => {
    async function fetchData() {
      try {
        // マスターデータ取得
        const masterData = await api.getMasterData();
        setKnowledge({
          all_needs: masterData.all_needs || [],
          all_loads: masterData.all_loads || [],
          all_services: masterData.all_services || [],
        });

        // セッションIDがある場合はセッションデータを取得
        if (sessionId) {
          try {
            const session = await api.getSession(sessionId);
            const services = await api.getServiceRecommendations(sessionId);
            
            const profile = session.profile || {};
            const mappedNeeds = profile.mapped_needs || [];
            const detectedLoads = profile.detected_loads || [];
            
            setSessionData({
              matched_needs: mappedNeeds,
              detected_loads: detectedLoads.map((l: { name: string }) => l.name),
              recommended_services: services.map((s: { id: string; title: string; score: number }) => ({
                id: s.id,
                title: s.title,
                score: s.score,
              })),
            });
          } catch (e) {
            console.warn("セッションデータ取得エラー:", e);
          }
        }
      } catch (e) {
        console.error("知識基盤取得エラー:", e);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-navy border-t-transparent"></div>
          <p className="mt-4 text-text-muted">知識基盤を読み込み中...</p>
        </div>
      </div>
    );
  }

  if (!knowledge) {
    return (
      <div className="mx-auto max-w-[840px] px-6 py-10">
        <div className="rounded-md border border-load/40 bg-load/10 p-6 text-center">
          <p className="mb-4 text-navy">知識基盤の読み込みに失敗しました</p>
          <button
            onClick={() => router.back()}
            className="rounded-md bg-navy px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-navy/90"
          >
            戻る
          </button>
        </div>
      </div>
    );
  }

  const matchedNeedsCount = sessionData ? sessionData.matched_needs.length : 0;
  const detectedLoadsCount = sessionData ? sessionData.detected_loads.length : 0;
  const recommendedServicesCount = sessionData ? sessionData.recommended_services.length : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-10">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* ヘッダー */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-navy">業務知識基盤</h1>
          <p className="mt-2 text-text-muted">
            システムが参照している構造化された知識辞書です
          </p>
          {sessionData && (
            <p className="mt-2 text-sm text-green-700 font-medium">
              ✓ 今回の提案で使用された知識を色付けして表示しています
            </p>
          )}
        </div>

        {/* 統計情報 */}
        <div className="mb-8 grid grid-cols-3 gap-4">
          <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
            <div className="text-sm font-medium text-text-muted">登録済みニーズ</div>
            <div className="mt-2 text-3xl font-bold text-navy">{knowledge.all_needs.length}</div>
            {sessionData && (
              <div className="mt-1 text-sm text-blue-600 font-medium">
                今回マッチ: {matchedNeedsCount}件
              </div>
            )}
            <div className="mt-1 text-xs text-text-muted">種類</div>
          </div>
          <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
            <div className="text-sm font-medium text-text-muted">登録済み懸念事項</div>
            <div className="mt-2 text-3xl font-bold text-navy">{knowledge.all_loads.length}</div>
            {sessionData && (
              <div className="mt-1 text-sm text-amber-600 font-medium">
                今回検出: {detectedLoadsCount}件
              </div>
            )}
            <div className="mt-1 text-xs text-text-muted">種類</div>
          </div>
          <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
            <div className="text-sm font-medium text-text-muted">登録済みサービス</div>
            <div className="mt-2 text-3xl font-bold text-navy">{knowledge.all_services.length}</div>
            {sessionData && (
              <div className="mt-1 text-sm text-indigo-600 font-medium">
                今回推薦: {recommendedServicesCount}件
              </div>
            )}
            <div className="mt-1 text-xs text-text-muted">種類</div>
          </div>
        </div>

        {/* タブ */}
        <div className="mb-6 flex gap-2 border-b border-border">
          <button
            onClick={() => setSelectedTab("needs")}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              selectedTab === "needs"
                ? "border-b-2 border-navy text-navy"
                : "text-text-muted hover:text-navy"
            }`}
          >
            ニーズ ({knowledge.all_needs.length})
          </button>
          <button
            onClick={() => setSelectedTab("loads")}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              selectedTab === "loads"
                ? "border-b-2 border-navy text-navy"
                : "text-text-muted hover:text-navy"
            }`}
          >
            懸念事項 ({knowledge.all_loads.length})
          </button>
          <button
            onClick={() => setSelectedTab("services")}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              selectedTab === "services"
                ? "border-b-2 border-navy text-navy"
                : "text-text-muted hover:text-navy"
            }`}
          >
            サービス ({knowledge.all_services.length})
          </button>
        </div>

        {/* コンテンツ */}
        <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
          {selectedTab === "needs" && (
            <div>
              <h3 className="mb-4 text-lg font-semibold text-navy">ニーズ一覧</h3>
              <div className="grid grid-cols-2 gap-3">
                {knowledge.all_needs.map((need, idx) => {
                  const isMatched = sessionData?.matched_needs.includes(need) || false;
                  return (
                    <div
                      key={idx}
                      className={`rounded-md border p-3 text-sm transition-all ${
                        isMatched
                          ? "border-blue-500 bg-blue-100 text-blue-900 font-semibold shadow-md"
                          : "border-blue-200 bg-blue-50 text-blue-900"
                      }`}
                    >
                      {isMatched && <span className="mr-2">✓</span>}
                      {need}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {selectedTab === "loads" && (
            <div>
              <h3 className="mb-4 text-lg font-semibold text-navy">懸念事項一覧</h3>
              <div className="space-y-3">
                {knowledge.all_loads.map((load, idx) => {
                  const isDetected = sessionData?.detected_loads.includes(load) || false;
                  return (
                    <div
                      key={idx}
                      className={`rounded-md border p-3 text-sm transition-all ${
                        isDetected
                          ? "border-amber-500 bg-amber-100 text-amber-900 font-semibold shadow-md"
                          : "border-yellow-200 bg-yellow-50 text-yellow-900"
                      }`}
                    >
                      {isDetected && <span className="mr-2">✓</span>}
                      {load}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {selectedTab === "services" && (
            <div>
              <h3 className="mb-4 text-lg font-semibold text-navy">サービス一覧</h3>
              <div className="space-y-3">
                {knowledge.all_services.map((service) => {
                  const matchedService = sessionData?.recommended_services.find(
                    (s) => s.id === service.id
                  );
                  const isRecommended = !!matchedService;
                  const score = matchedService ? Math.round(matchedService.score * 100) : 0;
                  
                  return (
                    <div
                      key={service.id}
                      className={`rounded-md border p-4 transition-all ${
                        isRecommended
                          ? "border-indigo-500 bg-indigo-100 shadow-md"
                          : "border-border bg-surface"
                      }`}
                    >
                      <div className="mb-2 flex items-start justify-between">
                        <div className="flex-1">
                          <span className="text-xs text-text-muted">{service.id}</span>
                          <h4 className={`mt-1 font-semibold ${isRecommended ? "text-indigo-900" : "text-navy"}`}>
                            {isRecommended && <span className="mr-2">✓</span>}
                            {service.title}
                          </h4>
                        </div>
                        <div className="flex gap-2">
                          {isRecommended && (
                            <span className="rounded-full bg-indigo-600 px-3 py-1 text-xs font-bold text-white">
                              {score}%
                            </span>
                          )}
                          <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                            {service.direction}
                          </span>
                          <span className="rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-600">
                            {service.domain}
                          </span>
                        </div>
                      </div>
                      <p className={`text-sm ${isRecommended ? "text-indigo-800" : "text-text-muted"}`}>
                        {service.one_liner}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* 戻るボタン */}
        <div className="mt-8 flex justify-center">
          <button
            onClick={() => router.back()}
            className="rounded-md border border-navy px-6 py-3 text-sm font-medium text-navy transition-colors hover:bg-navy/5"
          >
            戻る
          </button>
        </div>
      </div>
    </div>
  );
}

export default function KnowledgeBasePage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-navy border-t-transparent"></div>
          <p className="mt-4 text-text-muted">知識基盤を読み込み中...</p>
        </div>
      </div>
    }>
      <KnowledgeBaseContent />
    </Suspense>
  );
}
