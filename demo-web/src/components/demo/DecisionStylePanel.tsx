import type { DecisionStyleResult } from "@/lib/decision-style-calculator";

const STYLE_ORDER = [
  "Maximizer",
  "Satisficer",
  "Authority-driven",
  "Delegator",
  "Intuitive",
  "Impulsive",
] as const;

const SHORT_LABELS: Record<string, string> = {
  Maximizer: "徹底比較",
  Satisficer: "十分型",
  "Authority-driven": "権威依存",
  Delegator: "委任",
  Intuitive: "直感",
  Impulsive: "衝動",
};

type Props = {
  decisionStyle: DecisionStyleResult | null;
};

export function DecisionStylePanel({ decisionStyle }: Props) {
  if (!decisionStyle) {
    return (
      <div className="rounded-md border border-border bg-surface p-6">
        <h2 className="text-lg text-navy">あなたの Decision スタイル</h2>
        <p className="mt-4 text-sm text-text-muted">
          購買プロセスに関する質問（Q5〜Q7）に答えると表示されます
        </p>
      </div>
    );
  }

  const { label, description, confidence, scores, isMixed, secondaryLabel } =
    decisionStyle;

  return (
    <div className="rounded-md border border-border bg-surface p-6 shadow-sm">
      <h2 className="text-lg font-medium text-navy">あなたの Decision スタイル</h2>

      <div className="mt-4 rounded-md bg-navy/5 px-4 py-3">
        {isMixed ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-wide text-gold">
              混合型
            </p>
            <p className="mt-1 text-xl font-medium text-navy">
              {label}
              <span className="text-base font-normal text-text-muted">
                {" "}
                ＋ {secondaryLabel} の傾向
              </span>
            </p>
          </>
        ) : (
          <>
            <p className="text-xs text-text-muted">いまの推定</p>
            <p className="mt-1 text-xl font-medium text-navy">{label}</p>
          </>
        )}
        <p className="mt-2 text-sm leading-relaxed text-text">{description}</p>
        <p className="mt-2 text-xs text-text-muted">
          確信度 {Math.round(confidence)}%
        </p>
      </div>

      <ul className="mt-6 space-y-3">
        {STYLE_ORDER.map((key) => {
          const value = Math.round(scores[key] ?? 0);
          const isPrimary = key === decisionStyle.name;
          return (
            <li key={key}>
              <div className="mb-1 flex justify-between text-sm">
                <span
                  className={
                    isPrimary ? "font-medium text-navy" : "text-text-muted"
                  }
                >
                  {SHORT_LABELS[key] ?? key}
                </span>
                <span className="text-text-muted">{value}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-border">
                <div
                  className={`h-full rounded-full transition-all duration-300 ease-out ${
                    isPrimary ? "bg-gold" : "bg-navy/40"
                  }`}
                  style={{ width: `${value}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
