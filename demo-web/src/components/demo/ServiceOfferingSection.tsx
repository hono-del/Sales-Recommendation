"use client";

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
  feedback_adjusted?: boolean;
  feedback_adjustment_info?: string | null;
};

type FeedbackValue = "not_fit" | "low_interest" | "somewhat_interested" | "want_details";

type Props = {
  services: ServiceOffering[];
  loading?: boolean;
  sessionId?: string | null;
  feedbacks?: Record<string, FeedbackValue>;
  onFeedbackChange?: (serviceId: string, value: FeedbackValue) => void;
};

const DIRECTION_LABEL: Record<string, { label: string; color: string; icon: string }> = {
  upgrade: { label: "アップグレード", color: "text-blue-600 bg-blue-50", icon: "↑" },
  downgrade: { label: "ダウングレード", color: "text-green-600 bg-green-50", icon: "↓" },
  neutral: { label: "最適化", color: "text-gray-600 bg-gray-50", icon: "→" },
};

const DOMAIN_LABEL: Record<string, string> = {
  maintenance: "メンテナンス",
  upgrade_path: "機能追加・カスタマイズ",
  connectivity: "コネクティビティ",
  downgrade_path: "コスト削減",
  ownership_program: "オーナーシッププログラム",
  concierge_support: "コンシェルジュサポート",
};

export function ServiceOfferingSection({ services, loading, sessionId, feedbacks, onFeedbackChange }: Props) {
  if (loading) {
    return (
      <div className="rounded-md border border-border bg-surface p-8">
        <div className="flex items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-navy border-t-transparent"></div>
          <span className="ml-3 text-text-muted">サービス提案を生成中...</span>
        </div>
      </div>
    );
  }

  if (!services || services.length === 0) {
    return (
      <div className="rounded-md border border-border bg-surface p-8">
        <p className="text-center text-text-muted">
          現在、推薦できるサービスがありません
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {services.map((service, idx) => (
        <ServiceCard 
          key={service.id} 
          service={service} 
          rank={idx + 1} 
          feedback={feedbacks?.[service.id] || null}
          onFeedbackChange={onFeedbackChange}
        />
      ))}
    </div>
  );
}

function ServiceCard({ 
  service, 
  rank, 
  feedback,
  onFeedbackChange,
}: { 
  service: ServiceOffering; 
  rank: number; 
  feedback: FeedbackValue | null;
  feedback: FeedbackValue | null;
  onFeedbackChange?: (serviceId: string, value: FeedbackValue) => void;
}) {
  const directionInfo = DIRECTION_LABEL[service.direction] || DIRECTION_LABEL.neutral;
  const domainLabel = DOMAIN_LABEL[service.domain] || service.domain;

  const handleFeedback = (value: FeedbackValue) => {
    if (onFeedbackChange) {
      onFeedbackChange(service.id, value);
    }
  };

  const feedbackOptions: Array<{ value: FeedbackValue; label: string; emoji: string }> = [
    { value: "not_fit", label: "合わない", emoji: "✕" },
    { value: "low_interest", label: "あまり興味なし", emoji: "△" },
    { value: "somewhat_interested", label: "少し気になる", emoji: "○" },
    { value: "want_details", label: "詳しく知りたい", emoji: "◎" },
  ];

  return (
    <div className="group rounded-lg border border-border bg-surface p-6 shadow-sm transition-all hover:border-navy hover:shadow-md">
      {/* ヘッダー */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-navy text-xs font-bold text-white">
              {rank}
            </span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${directionInfo.color}`}
            >
              {directionInfo.icon} {directionInfo.label}
            </span>
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-600">
              {domainLabel}
            </span>
            {service.feedback_adjusted && service.feedback_adjustment_info && (
              <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                🌱 {service.feedback_adjustment_info}
              </span>
            )}
          </div>
          <h3 className="text-lg font-semibold text-navy">{service.title}</h3>
        </div>
        <div className="ml-4 text-right">
          <div className="text-2xl font-bold text-navy">
            {Math.round(service.score * 100)}
          </div>
          <div className="text-xs text-text-muted">適合度</div>
        </div>
      </div>

      {/* 説明 */}
      <p className="mb-4 text-sm text-text">{service.one_liner}</p>

      {/* 提案文 */}
      {service.pitch && (
        <div className="mb-4 rounded-md bg-blue-50 p-3">
          <p className="text-sm text-blue-900">💡 {service.pitch}</p>
        </div>
      )}

      {/* マッチ情報 */}
      <div className="space-y-2 text-xs text-text-muted">
        {/* 参照した知識セクション */}
        {(service.matched_needs.length > 0 || service.matched_loads.length > 0) && (
          <div className="mb-3 rounded-md border border-purple-200 bg-purple-50 p-3">
            <div className="mb-2 font-semibold text-purple-900">📚 参照した知識</div>
            {service.matched_needs.length > 0 && (
              <div className="mb-1">
                <span className="font-medium text-purple-800">Need: </span>
                <span className="text-purple-700">
                  {service.matched_needs.slice(0, 2).join(" / ")}
                  {service.matched_needs.length > 2 && ` 他${service.matched_needs.length - 2}件`}
                </span>
              </div>
            )}
            {service.matched_loads.length > 0 && (
              <div className="mb-1">
                <span className="font-medium text-purple-800">Load: </span>
                <span className="text-purple-700">{service.matched_loads.join(" / ")}</span>
              </div>
            )}
            <div>
              <span className="font-medium text-purple-800">Service: </span>
              <span className="text-purple-700">{service.title}</span>
            </div>
          </div>
        )}
        
        {service.need_rationale && (
          <div className="mt-2 border-t border-border pt-2">
            <span className="font-medium text-navy">推薦理由: </span>
            <span>{service.need_rationale}</span>
          </div>
        )}
      </div>

      {/* アクションボタン */}
      <div className="mt-4 flex gap-2">
        <button className="flex-1 rounded-md border border-navy px-4 py-2 text-sm font-medium text-navy transition-colors hover:bg-navy hover:text-white">
          詳細を見る
        </button>
        <button className="flex-1 rounded-md bg-navy px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-navy/90">
          お問い合わせ
        </button>
      </div>

      {/* フィードバック */}
      <div className="mt-4 border-t border-border pt-3">
        <p className="mb-2 text-xs text-text-muted">このサービスについて</p>
        <div className="flex gap-2">
          {feedbackOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => handleFeedback(option.value)}
              className={`flex-1 rounded-md border px-2 py-1.5 text-xs font-medium transition-all ${
                feedback === option.value
                  ? "border-navy bg-navy text-white"
                  : "border-border bg-white text-text hover:border-navy/50 hover:bg-navy/5"
              }`}
            >
              <span className="mr-1">{option.emoji}</span>
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
