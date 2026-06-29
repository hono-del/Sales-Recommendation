"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";

type FeedbackLog = {
  session_id: string;
  created_at: string;
  updated_at: string;
  feedback_count: number;
  feedbacks: Array<{
    service_id: string;
    service_rank: number;
    service_score: number;
    feedback_value: string;
    matched_needs: string[];
    matched_loads: string[];
    value_alignment: number;
    timestamp: string;
  }>;
};

export default function FeedbackLogsPage() {
  const [logs, setLogs] = useState<FeedbackLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalSessions, setTotalSessions] = useState(0);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch(`${api.getApiUrl()}/api/demo/feedback-logs`);
        if (!response.ok) {
          throw new Error("Failed to fetch feedback logs");
        }
        const data = await response.json();
        setLogs(data.feedbacks || []);
        setTotalSessions(data.total_sessions || 0);
      } catch (e) {
        console.error("Error fetching feedback logs:", e);
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-navy border-t-transparent"></div>
          <p className="mt-4 text-text-muted">フィードバックログを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-red-900">エラー: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-navy">サービスフィードバックログ</h1>
        <p className="mt-2 text-text-muted">
          全セッション: {totalSessions} / フィードバックあり: {logs.length}
        </p>
      </div>

      {logs.length === 0 ? (
        <div className="rounded-lg border border-border bg-surface p-8 text-center">
          <p className="text-text-muted">まだフィードバックがありません</p>
        </div>
      ) : (
        <div className="space-y-6">
          {logs.map((log) => (
            <div
              key={log.session_id}
              className="rounded-lg border border-border bg-surface p-6 shadow-sm"
            >
              <div className="mb-4 flex items-start justify-between border-b border-border pb-4">
                <div>
                  <p className="text-sm font-medium text-navy">
                    Session: {log.session_id.slice(0, 8)}...
                  </p>
                  <p className="mt-1 text-xs text-text-muted">
                    作成: {new Date(log.created_at).toLocaleString("ja-JP")}
                  </p>
                  <p className="text-xs text-text-muted">
                    更新: {new Date(log.updated_at).toLocaleString("ja-JP")}
                  </p>
                </div>
                <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
                  {log.feedback_count} 件
                </span>
              </div>

              <div className="space-y-3">
                {log.feedbacks.map((fb, idx) => (
                  <div
                    key={idx}
                    className="rounded-md border border-border/50 bg-white p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-navy px-2 py-0.5 text-xs font-bold text-white">
                            {fb.service_id}
                          </span>
                          <span className="text-xs text-text-muted">
                            Rank {fb.service_rank}
                          </span>
                          <span className="text-xs text-text-muted">
                            Score {Math.round(fb.service_score * 100)}%
                          </span>
                        </div>
                        <p className="mt-2 text-sm">
                          <span className="font-medium">Feedback:</span>{" "}
                          <span
                            className={`rounded px-2 py-0.5 text-xs font-medium ${
                              fb.feedback_value === "want_details"
                                ? "bg-green-100 text-green-800"
                                : fb.feedback_value === "somewhat_interested"
                                ? "bg-blue-100 text-blue-800"
                                : fb.feedback_value === "low_interest"
                                ? "bg-yellow-100 text-yellow-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {fb.feedback_value}
                          </span>
                        </p>
                        {fb.matched_needs.length > 0 && (
                          <p className="mt-1 text-xs text-text-muted">
                            Needs: {fb.matched_needs.slice(0, 3).join(", ")}
                            {fb.matched_needs.length > 3 &&
                              ` +${fb.matched_needs.length - 3}`}
                          </p>
                        )}
                      </div>
                      <div className="text-right text-xs text-text-muted">
                        {new Date(fb.timestamp).toLocaleString("ja-JP")}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 text-center">
        <a
          href="/demo/opening"
          className="text-sm text-navy underline hover:text-navy/80"
        >
          デモトップに戻る
        </a>
      </div>
    </div>
  );
}
