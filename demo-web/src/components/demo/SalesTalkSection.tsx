"use client";

import { Recommendation } from "@/types/demo";

interface SalesTalkSectionProps {
  topRecommendation: Recommendation;
}

export function SalesTalkSection({ topRecommendation }: SalesTalkSectionProps) {
  // 推薦理由から営業トークを生成
  const salesTalkPoints = generateSalesTalk(topRecommendation);

  return (
    <section className="mx-auto mt-16 max-w-4xl rounded-lg border border-border bg-white p-8 shadow-sm">
      <h2 className="text-2xl font-light text-navy">
        販売店サポート（提案トーク）
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
          お客様に寄り添った丁寧な説明をすることで、納得感のある提案になります。
        </p>
      </div>
    </section>
  );
}

interface SalesTalkPoint {
  title: string;
  talk: string;
}

function generateSalesTalk(recommendation: Recommendation): SalesTalkPoint[] {
  const points: SalesTalkPoint[] = [];

  // 1. オープニング（ニーズの確認）
  points.push({
    title: "お客様のご要望の確認",
    talk: `お客様は快適性と安全性を重視されているとのことですね。${recommendation.model}はまさにそのニーズにお応えできる一台です。`,
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
    talk: `例えば、週末のご家族でのお出かけや日々の通勤など、様々なシーンで快適にご利用いただけます。特に${recommendation.model}の先進機能は、実際にお使いいただくとその良さを実感していただけると思います。`,
  });

  // 4. クロージング（次のアクション）
  points.push({
    title: "次のステップのご提案",
    talk: `ぜひ一度、実車をご覧いただき、試乗で${recommendation.model}の魅力を体感していただければと思います。お客様のご都合の良い日時で、試乗のご予約を承ります。`,
  });

  return points;
}
