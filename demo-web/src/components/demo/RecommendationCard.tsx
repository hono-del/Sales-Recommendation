import type { Recommendation } from "@/types/demo";

type Props = {
  item: Recommendation;
  rank: number;
  delegationLevel: "guide" | "co_pilot" | "auto";
};

export function RecommendationCard({ item, rank, delegationLevel }: Props) {
  const pct = Math.round(item.score * 100);
  const showFullReason = delegationLevel === "guide" || delegationLevel === "co_pilot";
  const reason =
    delegationLevel === "auto"
      ? item.reason.split("、")[0] || item.reason
      : item.reason;
  const metaParts = [
    item.price_range,
    item.fuel_type,
    item.seating_capacity ? `${item.seating_capacity}人乗り` : null,
  ].filter(Boolean);

  return (
    <article
      title={delegationLevel === "guide" ? item.reason : undefined}
      className={`flex h-full flex-col rounded-md border bg-surface p-5 shadow-sm transition-shadow hover:shadow-md lg:p-6 ${
        rank === 1 ? "border-gold" : "border-border"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {rank === 1 && (
            <span className="mb-2 inline-block rounded bg-gold/20 px-2 py-0.5 text-xs font-medium text-gold">
              Recommended
            </span>
          )}
          <h3 className="text-lg font-medium text-navy lg:text-xl">{item.model}</h3>
          <p className="mt-1 text-sm text-text-muted">{item.archetype}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-[28px] font-light leading-none text-navy">{pct}</p>
          <p className="text-xs text-text-muted">おすすめ度 %</p>
        </div>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-border">
        <div
          className="h-full rounded-full bg-navy"
          style={{ width: `${pct}%` }}
        />
      </div>
      {metaParts.length > 0 && (
        <p className="mt-2 text-xs text-text-muted">{metaParts.join(" · ")}</p>
      )}
      {item.appeal_points && item.appeal_points.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2">
          {item.appeal_points.map((pt) => (
            <li
              key={pt}
              className="rounded-full px-2 py-0.5 text-xs"
              style={{ background: "#EEF2F7", color: "var(--color-navy)" }}
            >
              {pt.length > 28 ? `${pt.slice(0, 28)}…` : pt}
            </li>
          ))}
        </ul>
      )}
      <div className="mt-auto pt-4">
        {showFullReason && (
          <p className="text-sm leading-relaxed text-text">{reason}</p>
        )}
        {!showFullReason && (
          <p className="text-sm font-medium text-navy">{reason}</p>
        )}
      </div>
      {item.similar_consumers && item.similar_consumers.length > 0 && (
        <p className="mt-2 text-xs text-text-muted">
          類似購入者: {item.similar_consumers.length}名
        </p>
      )}
      {item.gap_vs_top && item.gap_vs_top.length > 0 && (
        <div className="mt-3 rounded-md bg-slate-50 px-3 py-2">
          <p className="text-[10px] font-semibold uppercase text-slate-600">
            第1推薦との違い
          </p>
          <ul className="mt-1 space-y-1">
            {item.gap_vs_top.map((gap) => (
              <li key={gap} className="text-xs text-slate-700">
                · {gap}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
