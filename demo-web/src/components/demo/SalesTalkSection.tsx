"use client";

import { RecommendationItem } from "@/types/demo";

interface SalesTalkSectionProps {
  topRecommendation: RecommendationItem;
}

export function SalesTalkSection({ topRecommendation }: SalesTalkSectionProps) {
  // 推薦理由から営業トークを生成
  const salesTalkPoints = generateSalesTalk(topRecommendation);

  return (
    <section className="mx-auto mt-16 max-w-4xl rounded-lg border border-border bg-white p-8 shadow-sm">
      <h2 className="text-2xl font-light text-navy">
        営業トーク案
      </h2>
      <p className="mt-2 text-sm text-text-muted">
        {topRecommendation.model} をお客様にご提案する際のポイント
      </p>

      <div className="mt-6 space-y-6">
        {salesTalkPoints.map((point, index) => (
          <div key={index} className="rounded-md bg-surface p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-navy text-sm font-medium text-white">
                {index + 1}
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-text">{point.title}</h3>
                <p className="mt-2 text-sm text-text-muted">{point.talk}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-md border border-border bg-blue-50 p-4">
        <h4 className="text-sm font-medium text-navy">💡 提案のポイント</h4>
        <p className="mt-2 text-sm text-text">
          お客様の価値観（{topRecommendation.decision_style || "バランス型"}）に合わせて、
          {topRecommendation.decision_style === "Maximizer" && "詳細な比較データと豊富な選択肢を提示"}
          {topRecommendation.decision_style === "Satisficer" && "必要十分な情報で迅速な意思決定をサポート"}
          {topRecommendation.decision_style === "Authority-driven" && "専門家の評価と実績を重視した説明"}
          {topRecommendation.decision_style === "Delegator" && "他のお客様の声と専門家の推奨を中心に"}
          {topRecommendation.decision_style === "Intuitive" && "実際の体験と感覚を大切にした提案"}
          {topRecommendation.decision_style === "Impulsive" && "今だけの特典と即決のメリットを強調"}
          {!topRecommendation.decision_style && "お客様に寄り添った丁寧な説明"}
          することで、納得感のある提案になります。
        </p>
      </div>
    </section>
  );
}

interface SalesTalkPoint {
  title: string;
  talk: string;
}

function generateSalesTalk(recommendation: RecommendationItem): SalesTalkPoint[] {
  const points: SalesTalkPoint[] = [];

  // 1. オープニング（ニーズの確認）
  points.push({
    title: "お客様のご要望の確認",
    talk: `お客様は${recommendation.matched_needs?.slice(0, 2).join("と") || "快適性と安全性"}を重視されているとのことですね。${recommendation.model}はまさにそのニーズにお応えできる一台です。`,
  });

  // 2. メリットの提示（上位の理由を活用）
  const topReason = recommendation.reason || "総合的なバランスの良さ";
  points.push({
    title: `${recommendation.model}の強み`,
    talk: `${recommendation.model}は${topReason}が特徴です。多くのお客様から「期待以上だった」とのお声をいただいています。`,
  });

  // 3. 具体的な利用シーン
  points.push({
    title: "実際の使用イメージ",
    talk: `例えば、週末のご家族でのお出かけや日々の通勤など、様々なシーンで快適にご利用いただけます。特に${recommendation.model}の${recommendation.features?.[0]?.name || "先進機能"}は、実際にお使いいただくとその良さを実感していただけると思います。`,
  });

  // 4. クロージング（次のアクション）
  points.push({
    title: "次のステップのご提案",
    talk: `ぜひ一度、実車をご覧いただき、試乗で${recommendation.model}の魅力を体感していただければと思います。お客様のご都合の良い日時で、試乗のご予約を承ります。`,
  });

  return points;
}
