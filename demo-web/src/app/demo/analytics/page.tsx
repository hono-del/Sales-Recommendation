"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";

type LogEntry = {
  session_id: string;
  logged_at: string;
  created_at: string;
  status: string;
  value_profile: {
    safety: number;
    family: number;
    efficiency: number;
    enjoyment: number;
    adventure: number;
  };
  mapped_needs: string[];
  detected_loads: Array<{
    name: string;
    description: string;
    related_values: string[];
  }>;
  recommended_services: Array<{
    service_id: string;
    title: string;
    rank: number;
    score: number;
    matched_needs: string[];
    matched_loads: string[];
  }>;
  service_feedbacks: Array<{
    service_id: string;
    service_rank: number;
    feedback_value: string;
    timestamp: string;
  }>;
  answers_count: number;
};

const FEEDBACK_LABELS: Record<string, string> = {
  not_fit: "合わない",
  low_interest: "あまり興味なし",
  somewhat_interested: "少し気になる",
  want_details: "詳しく知りたい",
};

export default function AnalyticsPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);

  useEffect(() => {
    async function fetchLogs() {
      try {
        setLoading(true);
        const data = await api.getAnalyticsLogs();
        
        // セッションIDごとに最新のログだけを取得
        const logsBySession = new Map<string, LogEntry>();
        (data.logs || []).forEach((log: LogEntry) => {
          const existing = logsBySession.get(log.session_id);
          if (!existing || new Date(log.logged_at) > new Date(existing.logged_at)) {
            logsBySession.set(log.session_id, log);
          }
        });
        
        // 最新順にソート
        const uniqueLogs = Array.from(logsBySession.values()).sort(
          (a, b) => new Date(b.logged_at).getTime() - new Date(a.logged_at).getTime()
        );
        
        setLogs(uniqueLogs);
      } catch (e) {
        console.error("ログ取得エラー:", e);
        setError(e instanceof Error ? e.message : "ログの取得に失敗しました");
      } finally {
        setLoading(false);
      }
    }

    fetchLogs();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-navy border-t-transparent"></div>
          <p className="mt-4 text-text-muted">ログデータを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-[840px] px-6 py-10">
        <div className="rounded-md border border-load/40 bg-load/10 p-6 text-center">
          <p className="mb-4 text-navy">{error}</p>
          <button
            onClick={() => router.push("/demo/service/reasoning")}
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
      <div className="mx-auto max-w-[1400px] px-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-navy">分析ログデータ</h1>
          <p className="mt-2 text-text-muted">
            過去のセッションデータと推薦結果を確認できます
          </p>
        </div>

        <div className="mb-6 flex items-center justify-between">
          <p className="text-sm text-text-muted">
            総ログ数: <span className="font-semibold text-navy">{logs.length}件</span>
          </p>
          <button
            onClick={() => router.push("/demo/service/reasoning")}
            className="rounded-md border border-navy px-4 py-2 text-sm font-medium text-navy transition-colors hover:bg-navy/5"
          >
            戻る
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {logs.map((log, idx) => (
            <div
              key={`${log.session_id}-${log.logged_at}`}
              className="rounded-lg border border-border bg-white p-6 shadow-sm transition-all hover:shadow-md"
            >
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-navy">
                    セッション #{logs.length - idx}
                  </h3>
                  <p className="mt-1 text-xs text-text-muted">
                    ID: {log.session_id.slice(0, 8)}... | 記録日時:{" "}
                    {new Date(log.logged_at).toLocaleString("ja-JP")}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedLog(selectedLog?.session_id === log.session_id ? null : log)}
                  className="text-sm text-navy hover:underline"
                >
                  {selectedLog?.session_id === log.session_id ? "閉じる ▲" : "詳細 ▼"}
                </button>
              </div>

              {/* 概要 */}
              <div className="grid grid-cols-4 gap-4 text-xs">
                <div>
                  <p className="font-medium text-navy">価値観トップ</p>
                  <p className="mt-1 text-text">
                    {Object.entries(log.value_profile)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 2)
                      .map(([key, val]) => `${Math.round(val)}%`)
                      .join(" / ")}
                  </p>
                </div>
                <div>
                  <p className="font-medium text-navy">ニーズ数</p>
                  <p className="mt-1 text-text">{log.mapped_needs.length}件</p>
                </div>
                <div>
                  <p className="font-medium text-navy">推薦サービス数</p>
                  <p className="mt-1 text-text">{log.recommended_services.length}件</p>
                </div>
                <div>
                  <p className="font-medium text-navy">フィードバック数</p>
                  <p className="mt-1 text-text">{log.service_feedbacks.length}件</p>
                </div>
              </div>

              {/* 詳細 */}
              {selectedLog?.session_id === log.session_id && (
                <div className="mt-6 space-y-4 border-t border-border pt-4">
                  {/* 価値観プロファイル */}
                  <div>
                    <h4 className="mb-2 text-sm font-semibold text-navy">価値観プロファイル</h4>
                    <div className="grid grid-cols-5 gap-2">
                      {Object.entries(log.value_profile).map(([key, value]) => (
                        <div key={key} className="rounded bg-gray-50 p-2 text-center">
                          <p className="text-xs text-text-muted capitalize">{key}</p>
                          <p className="text-sm font-bold text-navy">{Math.round(value)}%</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 懸念事項 */}
                  {log.detected_loads.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-sm font-semibold text-navy">懸念事項</h4>
                      <div className="space-y-2">
                        {log.detected_loads.map((load, i) => (
                          <div key={i} className="rounded bg-yellow-50 p-3 text-xs">
                            <p className="font-medium text-yellow-900">{load.name}</p>
                            <p className="mt-1 text-yellow-700">{load.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 推薦サービス */}
                  <div>
                    <h4 className="mb-2 text-sm font-semibold text-navy">推薦サービス</h4>
                    <div className="space-y-2">
                      {log.recommended_services.map((service) => {
                        const feedback = log.service_feedbacks.find(
                          (fb) => fb.service_id === service.service_id
                        );
                        return (
                          <div
                            key={service.service_id}
                            className="rounded border border-border bg-white p-3 text-xs"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="font-medium text-navy">
                                  {service.rank}. {service.title}
                                </p>
                                <p className="mt-1 text-text-muted">
                                  スコア: {Math.round(service.score * 100)}%
                                </p>
                              </div>
                              {feedback && (
                                <span className="ml-2 rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                                  {FEEDBACK_LABELS[feedback.feedback_value]}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {logs.length === 0 && (
          <div className="rounded-lg border border-border bg-surface p-8 text-center">
            <p className="text-text-muted">まだログデータがありません</p>
          </div>
        )}
      </div>
    </div>
  );
}
