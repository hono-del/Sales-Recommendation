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
  feedbacks?: Record<string, FeedbackValue>;
  onFeedbackChange?: (serviceId: string, value: FeedbackValue) => void;
  layout?: "comparison" | "hero" | "authority" | "popular" | "visual" | "urgent" | "default";
  showDetailedScores?: boolean;
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

export function ServiceOfferingSection({ services, loading, feedbacks, onFeedbackChange, layout = "default", showDetailedScores = false }: Props) {
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

  // Satisficer（十分型）: 1位を大きく、他は小さく
  if (layout === "hero" && services.length > 0) {
    return (
      <div className="space-y-6">
        {/* 1位: 大きく表示 */}
        <div className="rounded-lg border-2 border-gold bg-gradient-to-br from-gold/5 to-transparent p-1">
          <div className="rounded-lg bg-white p-6">
            <div className="mb-3 flex items-center gap-2">
              <span className="rounded-full bg-gold px-3 py-1 text-sm font-bold text-white">
                ⭐ あなたに最適な1つ
              </span>
            </div>
            <ServiceCard 
              service={services[0]} 
              rank={1} 
              feedback={feedbacks?.[services[0].id] || null}
              onFeedbackChange={onFeedbackChange}
              layout={layout}
              showDetailedScores={showDetailedScores}
              isHeroCard={true}
            />
          </div>
        </div>

        {/* 2位以降: 控えめに */}
        {services.length > 1 && (
          <details className="group">
            <summary className="cursor-pointer rounded-lg border border-border bg-surface p-4 text-center text-sm font-medium text-navy hover:bg-surface/80">
              参考：他の選択肢も見る（{services.length - 1}件）
            </summary>
            <div className="mt-4 space-y-3">
              {services.slice(1).map((service, idx) => (
                <ServiceCard 
                  key={service.id} 
                  service={service} 
                  rank={idx + 2} 
                  feedback={feedbacks?.[service.id] || null}
                  onFeedbackChange={onFeedbackChange}
                  layout={layout}
                  showDetailedScores={showDetailedScores}
                  isHeroCard={false}
                />
              ))}
            </div>
          </details>
        )}
      </div>
    );
  }

  // その他のレイアウト
  return (
    <div className="space-y-4">
      {layout === "authority" && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
          <p className="text-sm font-medium text-blue-900">
            ✓ 実績と評価に基づいた信頼性の高いサービスをご提案しています
          </p>
        </div>
      )}
      {layout === "popular" && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-4 text-center">
          <p className="text-sm font-medium text-green-900">
            👥 多くのお客様に選ばれているサービスです
          </p>
        </div>
      )}
      {layout === "urgent" && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-center">
          <p className="text-sm font-medium text-red-900">
            ⚡ 今だけの特別なご提案です
          </p>
        </div>
      )}
      
      {services.map((service, idx) => (
        <ServiceCard 
          key={service.id} 
          service={service} 
          rank={idx + 1} 
          feedback={feedbacks?.[service.id] || null}
          onFeedbackChange={onFeedbackChange}
          layout={layout}
          showDetailedScores={showDetailedScores}
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
  layout = "default",
  showDetailedScores = false,
  isHeroCard = false,
}: { 
  service: ServiceOffering; 
  rank: number; 
  feedback: FeedbackValue | null;
  onFeedbackChange?: (serviceId: string, value: FeedbackValue) => void;
  layout?: string;
  showDetailedScores?: boolean;
  isHeroCard?: boolean;
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

  // ヒーローカード（Satisficer 1位）は大きく表示
  const cardSizeClass = isHeroCard ? "p-8" : "p-6";
  const titleSizeClass = isHeroCard ? "text-2xl" : "text-lg";
  const scoreSizeClass = isHeroCard ? "text-4xl" : "text-2xl";

  return (
    <div className={`group rounded-lg border border-border bg-surface ${cardSizeClass} shadow-sm transition-all hover:border-navy hover:shadow-md`}>
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
            {layout === "authority" && rank === 1 && (
              <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                👑 専門家推奨 No.1
              </span>
            )}
            {layout === "authority" && rank === 2 && (
              <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                ⭐ 実績評価トップクラス
              </span>
            )}
            {layout === "authority" && rank >= 3 && (
              <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-600">
                ✓ 信頼性確認済み
              </span>
            )}
            {layout === "visual" && rank === 1 && (
              <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700">
                ✨ あなたの直感にぴったり
              </span>
            )}
            {layout === "visual" && rank === 2 && (
              <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700">
                💎 魅力的な体験
              </span>
            )}
            {layout === "visual" && rank >= 3 && (
              <span className="rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-600">
                🌟 感動価値あり
              </span>
            )}
            {layout === "popular" && rank <= 3 && (
              <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-700">
                👥 人気 No.{rank}
              </span>
            )}
            {layout === "urgent" && rank === 1 && (
              <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700 animate-pulse">
                ⚡ 今だけ
              </span>
            )}
          </div>
          <h3 className={`${titleSizeClass} font-semibold text-navy`}>{service.title}</h3>
        </div>
        <div className="ml-4 text-right">
          <div className={`${scoreSizeClass} font-bold text-navy`}>
            {Math.round(service.score * 100)}
          </div>
          <div className="text-xs text-text-muted">適合度</div>
          {showDetailedScores && (
            <div className="mt-2 space-y-1 text-xs text-text-muted">
              <div>ニーズ: {Math.round((service.matched_needs.length / 3) * 100)}%</div>
              <div>負荷: {Math.round((service.matched_loads.length / 2) * 100)}%</div>
              <div>価値観: {Math.round(service.value_alignment * 100)}%</div>
            </div>
          )}
        </div>
      </div>

      {/* 説明 */}
      <p className={`mb-4 ${isHeroCard ? 'text-base' : 'text-sm'} text-text`}>{service.one_liner}</p>

      {/* Satisficer用の「この1台で十分な理由」 */}
      {isHeroCard && (
        <div className="mb-4 rounded-lg border border-gold/30 bg-gold/5 p-4">
          <h4 className="mb-2 text-sm font-semibold text-navy">✓ このサービスがあなたに最適な理由</h4>
          <ul className="space-y-1 text-sm text-text">
            <li>• 必要な条件を満たしています</li>
            <li>• あなたの価値観に合致しています（適合度 {Math.round(service.score * 100)}%）</li>
            <li>• 過不足のないバランスの良い選択です</li>
          </ul>
        </div>
      )}

      {/* Authority-driven用の専門家推薦情報 */}
      {layout === "authority" && rank <= 3 && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
          <div className="flex items-start gap-2">
            <span className="text-blue-600">🏆</span>
            <div className="flex-1 text-sm text-blue-900">
              <p className="font-semibold mb-1">
                {rank === 1 && "○○モビリティ愛知 推奨サービス"}
                {rank === 2 && "業界実績トップクラス"}
                {rank === 3 && "専門家評価 高評価獲得"}
              </p>
              <p className="text-xs text-blue-700">
                {rank === 1 && "全国200店舗以上で採用されている実績のあるサービスです"}
                {rank === 2 && "多くのディーラーで採用されている信頼性の高いサービスです"}
                {rank === 3 && "品質と実績が認められたサービスです"}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Visual（Intuitive）用の魅力訴求 */}
      {layout === "visual" && rank === 1 && (
        <div className="mb-4 rounded-lg border border-purple-200 bg-gradient-to-r from-purple-50 to-pink-50 p-3">
          <div className="flex items-start gap-2">
            <span className="text-purple-600">✨</span>
            <div className="flex-1 text-sm text-purple-900">
              <p className="font-semibold mb-1">あなたの価値観にぴったりマッチ</p>
              <p className="text-xs text-purple-700">
                心地よい体験と充実感を提供するサービスです
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 提案文 */}
      {service.pitch && (
        <div className={`mb-4 rounded-md p-3 ${
          layout === "visual" 
            ? "bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200" 
            : layout === "authority"
            ? "bg-blue-50 border border-blue-200"
            : "bg-blue-50"
        }`}>
          <p className={`text-sm ${
            layout === "visual" ? "text-purple-900 font-medium" : "text-blue-900"
          }`}>
            {layout === "visual" && "✨ "}
            {layout === "authority" && "👑 "}
            💡 {service.pitch}
          </p>
        </div>
      )}

      {/* マッチ情報 */}
      {layout !== "visual" && (
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
          
          {service.need_rationale && layout !== "visual" && (
            <div className="mt-2 border-t border-border pt-2">
              <span className="font-medium text-navy">推薦理由: </span>
              <span>{service.need_rationale}</span>
            </div>
          )}
        </div>
      )}

      {/* アクションボタン */}
      <div className="mt-4 flex gap-2">
        <button className="flex-1 rounded-md border border-navy px-4 py-2 text-sm font-medium text-navy transition-colors hover:bg-navy hover:text-white">
          詳細を見る
        </button>
        <button className={`flex-1 rounded-md ${isHeroCard || layout === "urgent" ? 'bg-gold hover:bg-gold/90' : 'bg-navy hover:bg-navy/90'} px-4 py-2 text-sm font-medium text-white transition-colors`}>
          {layout === "urgent" ? "今すぐ相談" : "お問い合わせ"}
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
