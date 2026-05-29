"use client";

import type { BuyerReviewItem, ExpertVoiceItem, StylePresentation } from "@/types/graph";
import type { ExcludedModel, Recommendation } from "@/types/demo";
import { RecommendationCard } from "./RecommendationCard";

type Props = {
  presentation?: StylePresentation;
  recommendations: Recommendation[];
  excluded: ExcludedModel[];
  delegationLevel: "guide" | "co_pilot" | "auto";
};

export function StyleAwareRecommendSection({
  presentation,
  recommendations,
  excluded,
  delegationLevel,
}: Props) {
  const mode = presentation?.ui_mode;

  if (!presentation || !mode || recommendations.length === 0) {
    return (
      <DefaultRecommendGrid
        recommendations={recommendations}
        excluded={excluded}
        delegationLevel={delegationLevel}
      />
    );
  }

  return (
    <div className="space-y-10">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wide text-gold">
          {presentation.style_label}向けの見せ方
        </p>
        <h3 className="mt-2 text-xl font-medium text-navy">{presentation.headline}</h3>
        {presentation.subheadline && (
          <p className="mt-2 text-sm text-text-muted">{presentation.subheadline}</p>
        )}
      </div>

      {mode === "comparison" && (
        <MaximizerComparisonView presentation={presentation} />
      )}
      {mode === "sufficiency" && (
        <SatisficerSufficiencyView presentation={presentation} />
      )}
      {mode === "trusted_pick" && (
        <TrustedPickView presentation={presentation} />
      )}
      {mode === "delegated_simple" && (
        <DelegatedSimpleView presentation={presentation} />
      )}
      {mode === "experience" && <ExperienceView presentation={presentation} />}
      {mode === "quick_pick" && <QuickPickView presentation={presentation} />}

      {!(mode === "delegated_simple") && (
        <DefaultRecommendGrid
          recommendations={recommendations}
          excluded={excluded}
          delegationLevel={delegationLevel}
          compactTitle="詳細スペック・カード表示"
        />
      )}
    </div>
  );
}

function MaximizerComparisonView({ presentation }: { presentation: StylePresentation }) {
  const vehicles = presentation.vehicles ?? [];
  const rows = presentation.comparison_rows ?? [];

  return (
    <div className="space-y-6">
      {presentation.why_rank1_points && presentation.why_rank1_points.length > 0 && (
        <div className="rounded-lg border border-gold/40 bg-gold/5 p-5">
          <h4 className="font-medium text-navy">
            {presentation.why_rank1_title ?? "第1位が最もおすすめな理由"}
          </h4>
          <ul className="mt-3 space-y-2 text-sm text-text">
            {presentation.why_rank1_points.map((p) => (
              <li key={p}>✓ {p}</li>
            ))}
          </ul>
        </div>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-slate-50">
                <th className="px-4 py-3 font-medium text-navy">比較項目</th>
                {vehicles.map((v) => (
                  <th
                    key={v.model}
                    className={`px-4 py-3 font-medium ${
                      v.rank === 1 ? "text-gold" : "text-navy"
                    }`}
                  >
                    {v.rank}位 {v.model}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.label} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 text-text-muted">{row.label}</td>
                  {row.values.map((val, i) => (
                    <td
                      key={`${row.label}-${i}`}
                      className={`px-4 py-3 ${i === 0 ? "font-medium text-navy" : "text-text"}`}
                    >
                      {val}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {vehicles.map((v) => (
          <article
            key={v.model}
            className={`rounded-lg border p-4 ${
              v.rank === 1 ? "border-gold bg-gold/5" : "border-border bg-surface"
            }`}
          >
            <p className="text-xs text-text-muted">{v.rank}位</p>
            <h4 className="text-lg font-medium text-navy">{v.model}</h4>
            <p className="mt-2 text-xs text-text-muted">{v.verdict}</p>
            {v.highlights && v.highlights.length > 0 && (
              <ul className="mt-3 space-y-1 text-xs text-emerald-800">
                {v.highlights.map((h) => (
                  <li key={h}>+ {h}</li>
                ))}
              </ul>
            )}
            {v.gaps && v.gaps.length > 0 && (
              <ul className="mt-3 space-y-1 text-xs text-slate-600">
                <li className="font-medium">第1位に不足する点</li>
                {v.gaps.map((g) => (
                  <li key={g}>− {g}</li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

function SatisficerSufficiencyView({ presentation }: { presentation: StylePresentation }) {
  const hero = presentation.hero_vehicle as {
    model?: string;
    score_pct?: number;
    price_range?: string;
    summary?: string;
    confidence_points?: string[];
  } | undefined;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {(presentation.checklist ?? []).map((item) => (
          <div
            key={item.title}
            className={`rounded-lg border p-4 ${
              item.met ? "border-emerald-200 bg-emerald-50/50" : "border-border bg-surface"
            }`}
          >
            <p className="text-xs font-semibold text-navy">
              {item.met ? "✓" : "○"} {item.title}
            </p>
            <ul className="mt-2 space-y-1 text-sm text-text">
              {item.items.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            {item.note && (
              <p className="mt-2 text-xs text-text-muted">{item.note}</p>
            )}
          </div>
        ))}
      </div>

      {hero?.model && (
        <div className="rounded-xl border-2 border-gold bg-surface p-6 shadow-sm">
          <p className="text-xs text-gold">十分基準を満たしたおすすめ</p>
          <h4 className="mt-1 text-2xl font-medium text-navy">{hero.model}</h4>
          <p className="mt-2 text-sm text-text">{hero.summary}</p>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-text-muted">
            {hero.score_pct != null && <span>マッチ {hero.score_pct}%</span>}
            {hero.price_range && <span>{hero.price_range}</span>}
          </div>
          {hero.confidence_points && (
            <ul className="mt-4 space-y-1 text-sm text-text">
              {hero.confidence_points.map((p) => (
                <li key={p}>✓ {p}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {presentation.alternatives_note && (
        <p className="text-center text-sm text-text-muted">
          {presentation.alternatives_note}
        </p>
      )}
    </div>
  );
}

function TrustedPickView({ presentation }: { presentation: StylePresentation }) {
  const hero = presentation.hero_vehicle as {
    model?: string;
    score_pct?: number;
    proof_points?: string[];
    reason?: string;
  };

  return (
    <div className="mx-auto max-w-xl rounded-xl border border-border bg-surface p-6">
      <h4 className="text-xl font-medium text-navy">{hero?.model}</h4>
      <ul className="mt-4 space-y-2 text-sm text-text">
        {(hero?.proof_points ?? []).map((p) => (
          <li key={p}>🏅 {p}</li>
        ))}
      </ul>
      {hero?.reason && <p className="mt-4 text-sm text-text-muted">{hero.reason}</p>}
    </div>
  );
}

function DelegatedSimpleView({ presentation }: { presentation: StylePresentation }) {
  const hero = presentation.hero_vehicle as {
    model?: string;
    one_liner?: string;
    reason?: string;
    trust_note?: string;
  };
  const reviews = presentation.buyer_reviews ?? [];
  const experts = presentation.expert_voices ?? [];

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="rounded-xl border-2 border-navy/20 bg-navy/5 p-8 text-center">
        <p className="text-sm text-text-muted">専門家・購入者の声を踏まえたおすすめ</p>
        <h4 className="mt-2 text-3xl font-light text-navy">{hero?.model}</h4>
        <p className="mt-3 text-lg text-navy">{hero?.one_liner}</p>
        {hero?.trust_note && (
          <p className="mt-3 text-sm font-medium text-emerald-800">{hero.trust_note}</p>
        )}
        {hero?.reason && <p className="mt-4 text-sm text-text-muted">{hero.reason}</p>}
      </div>

      {reviews.length > 0 && (
        <section aria-labelledby="delegator-reviews-heading">
          <div className="mb-4 flex items-baseline justify-between gap-2">
            <h4 id="delegator-reviews-heading" className="text-lg font-medium text-navy">
              購入者のレビュー
            </h4>
            {presentation.review_count_label && (
              <span className="text-xs text-text-muted">{presentation.review_count_label}</span>
            )}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {reviews.map((review, i) => (
              <BuyerReviewCard key={`${review.meta}-${i}`} review={review} />
            ))}
          </div>
        </section>
      )}

      {experts.length > 0 && (
        <section aria-labelledby="delegator-experts-heading">
          <div className="mb-4 flex items-baseline justify-between gap-2">
            <h4 id="delegator-experts-heading" className="text-lg font-medium text-navy">
              有識者・専門家の声
            </h4>
            {presentation.expert_count_label && (
              <span className="text-xs text-text-muted">{presentation.expert_count_label}</span>
            )}
          </div>
          <div className="space-y-4">
            {experts.map((voice, i) => (
              <ExpertVoiceCard key={`${voice.source}-${i}`} voice={voice} />
            ))}
          </div>
        </section>
      )}

      {presentation.optional_others && presentation.optional_others.length > 0 && (
        <p className="text-center text-xs text-text-muted">
          参考: 他の候補 {presentation.optional_others.join("、")}
        </p>
      )}
    </div>
  );
}

function BuyerReviewCard({ review }: { review: BuyerReviewItem }) {
  const stars = review.rating ?? 5;
  return (
    <blockquote className="rounded-lg border border-border bg-surface p-5 shadow-sm">
      <div className="mb-2 flex items-center gap-1 text-amber-500" aria-label={`満足度 ${stars}/5`}>
        {Array.from({ length: Math.min(5, stars) }).map((_, i) => (
          <span key={i} aria-hidden>
            ★
          </span>
        ))}
      </div>
      <p className="text-sm leading-relaxed text-text">&ldquo;{review.quote}&rdquo;</p>
      <footer className="mt-3 text-xs text-text-muted">— {review.meta}</footer>
      {review.source === "kg_outcome" && (
        <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">
          ナレッジグラフ購入者データ
        </p>
      )}
    </blockquote>
  );
}

function ExpertVoiceCard({ voice }: { voice: ExpertVoiceItem }) {
  return (
    <article className="flex gap-4 rounded-lg border border-gold/30 bg-amber-50/40 p-5">
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gold/20 text-lg"
        aria-hidden
      >
        🎓
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-gold">{voice.source}</p>
        <h5 className="mt-0.5 font-medium text-navy">{voice.title}</h5>
        <p className="mt-2 text-sm leading-relaxed text-text">{voice.quote}</p>
      </div>
    </article>
  );
}

function ExperienceView({ presentation }: { presentation: StylePresentation }) {
  const hero = presentation.hero_vehicle as { model?: string; feeling?: string };

  return (
    <div className="space-y-4">
      {(presentation.scenes ?? []).map((scene) => (
        <blockquote
          key={scene}
          className="border-l-4 border-gold pl-4 text-lg font-light italic text-navy"
        >
          {scene}
        </blockquote>
      ))}
      <p className="text-center text-sm text-text">
        → {hero?.model}：{hero?.feeling}
      </p>
    </div>
  );
}

function QuickPickView({ presentation }: { presentation: StylePresentation }) {
  const hero = presentation.hero_vehicle as {
    model?: string;
    score_pct?: number;
    price_range?: string;
    quick_reason?: string;
  };

  return (
    <div className="mx-auto flex max-w-md flex-col items-center rounded-xl bg-navy px-8 py-10 text-center text-white">
      <p className="text-4xl font-light">{hero?.model}</p>
      <p className="mt-2 text-gold">{hero?.quick_reason}</p>
      <p className="mt-4 text-sm opacity-80">
        {hero?.score_pct}% マッチ · {hero?.price_range}
      </p>
    </div>
  );
}

function DefaultRecommendGrid({
  recommendations,
  excluded,
  delegationLevel,
  compactTitle,
}: {
  recommendations: Recommendation[];
  excluded: ExcludedModel[];
  delegationLevel: "guide" | "co_pilot" | "auto";
  compactTitle?: string;
}) {
  if (recommendations.length === 0) return null;

  return (
    <>
      {compactTitle && (
        <h4 className="text-center text-sm font-medium text-text-muted">{compactTitle}</h4>
      )}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {recommendations.map((item, i) => (
          <RecommendationCard
            key={item.model}
            item={item}
            rank={i + 1}
            delegationLevel={delegationLevel}
          />
        ))}
      </div>
      {excluded.length > 0 && (
        <details className="rounded-lg border border-border bg-surface p-4">
          <summary className="cursor-pointer text-sm font-medium text-navy">
            なぜ他の車種は外した？
          </summary>
          <ul className="mt-4 space-y-2 text-sm text-text-muted">
            {excluded.map((ex) => (
              <li key={ex.model}>
                <span className="font-medium text-text">{ex.model}</span>
                {" — "}
                {ex.reason}
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
