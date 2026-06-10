"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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

export default function KnowledgeBasePage() {
  const router = useRouter();
  const [knowledge, setKnowledge] = useState<KnowledgeBase | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<"needs" | "loads" | "services">("needs");

  useEffect(() => {
    async function fetchKnowledge() {
      try {
        const data = await api.getMasterData();
        setKnowledge({
          all_needs: data.all_needs || [],
          all_loads: data.all_loads || [],
          all_services: data.all_services || [],
        });
      } catch (e) {
        console.error("知識基盤取得エラー:", e);
      } finally {
        setLoading(false);
      }
    }

    fetchKnowledge();
  }, []);

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-10">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* ヘッダー */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-navy">業務知識基盤</h1>
          <p className="mt-2 text-text-muted">
            システムが参照している構造化された知識辞書です
          </p>
        </div>

        {/* 統計情報 */}
        <div className="mb-8 grid grid-cols-3 gap-4">
          <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
            <div className="text-sm font-medium text-text-muted">登録済みニーズ</div>
            <div className="mt-2 text-3xl font-bold text-navy">{knowledge.all_needs.length}</div>
            <div className="mt-1 text-xs text-text-muted">種類</div>
          </div>
          <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
            <div className="text-sm font-medium text-text-muted">登録済み懸念事項</div>
            <div className="mt-2 text-3xl font-bold text-navy">{knowledge.all_loads.length}</div>
            <div className="mt-1 text-xs text-text-muted">種類</div>
          </div>
          <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
            <div className="text-sm font-medium text-text-muted">登録済みサービス</div>
            <div className="mt-2 text-3xl font-bold text-navy">{knowledge.all_services.length}</div>
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
                {knowledge.all_needs.map((need, idx) => (
                  <div
                    key={idx}
                    className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900"
                  >
                    {need}
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedTab === "loads" && (
            <div>
              <h3 className="mb-4 text-lg font-semibold text-navy">懸念事項一覧</h3>
              <div className="space-y-3">
                {knowledge.all_loads.map((load, idx) => (
                  <div
                    key={idx}
                    className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-900"
                  >
                    {load}
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedTab === "services" && (
            <div>
              <h3 className="mb-4 text-lg font-semibold text-navy">サービス一覧</h3>
              <div className="space-y-3">
                {knowledge.all_services.map((service) => (
                  <div
                    key={service.id}
                    className="rounded-md border border-border bg-surface p-4"
                  >
                    <div className="mb-2 flex items-start justify-between">
                      <div>
                        <span className="text-xs text-text-muted">{service.id}</span>
                        <h4 className="mt-1 font-semibold text-navy">{service.title}</h4>
                      </div>
                      <div className="flex gap-2">
                        <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                          {service.direction}
                        </span>
                        <span className="rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-600">
                          {service.domain}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-text-muted">{service.one_liner}</p>
                  </div>
                ))}
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
