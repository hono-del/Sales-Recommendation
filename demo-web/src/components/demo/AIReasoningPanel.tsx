"use client";

type ValueItem = {
  key: string;
  label: string;
  percent: number;
};

type Props = {
  values: ValueItem[];
  loads: string[];
  vehicleName: string;
  visible?: boolean;
};

function generateReasoning(values: ValueItem[], loads: string[], vehicleName: string): string {
  const topValues = values.slice(0, 2).map((v) => `「${v.label}」`);
  const valueText =
    topValues.length === 2 ? `${topValues[0]}と${topValues[1]}` : topValues[0] || "バランス";

  const loadTexts = loads.slice(0, 2).map((l) => `「${l}」`);
  const loadText =
    loadTexts.length >= 2
      ? `${loadTexts[0]}と${loadTexts[1]}`
      : loadTexts.length === 1
        ? loadTexts[0]
        : "判断負荷";

  return `あなたは${valueText}を重視しながら、\n\n${loadText}に負担を感じる傾向があります。\n\nそのため、これらの価値を実現し、負荷を軽減しやすい\n${vehicleName}をおすすめしています。`;
}

export function AIReasoningPanel({ values, loads, vehicleName, visible = true }: Props) {
  const reasoning = generateReasoning(values, loads, vehicleName);
  const maxPercent = Math.max(...values.map((v) => v.percent), 1);

  return (
    <aside
      className="space-y-6 rounded-lg border border-border bg-white p-6 shadow-sm transition-opacity duration-500"
      style={{ opacity: visible ? 1 : 0.4 }}
      aria-label="AIの判断理由"
    >
      <h2 className="text-xl font-light text-navy">なぜこの提案か</h2>

      {/* 重視価値 */}
      <section>
        <h3 className="text-sm font-semibold text-navy">あなたの重視価値</h3>
        <ul className="mt-4 space-y-4">
          {values.map((v) => (
            <li key={v.key ?? v.label}>
              <div className="flex justify-between text-sm">
                <span className="font-medium text-navy">{v.label}</span>
                <span className="tabular-nums text-text-muted">{v.percent}%</span>
              </div>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full"
                style={{ background: "#E2E8F0" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    width: `${(v.percent / maxPercent) * 100}%`,
                    background: "linear-gradient(90deg, #1E40AF, #3B82F6)",
                  }}
                />
              </div>
              {v.percent === maxPercent && (
                <div className="mt-1 text-xs text-text-muted">
                  → {getValueExplanation(v.key)}
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>

      {/* AIの判断理由 */}
      <section>
        <h3 className="text-sm font-semibold text-navy">AIの判断理由</h3>
        <div
          className="mt-4 rounded-lg px-5 py-5 leading-relaxed"
          style={{
            background: "linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%)",
            border: "1px solid #DBEAFE",
          }}
        >
          <p className="whitespace-pre-line text-sm text-text">{reasoning}</p>
        </div>
      </section>

      {/* 検出された負荷 */}
      {loads.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-navy">検出された負荷</h3>
          <ul className="mt-4 space-y-3">
            {loads.map((load) => (
              <li key={load} className="flex gap-3 text-sm">
                <span
                  className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                  style={{ background: "#EF4444" }}
                  aria-hidden
                >
                  !
                </span>
                <span className="text-text">{load}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
  );
}

function getValueExplanation(key: string): string {
  const explanations: Record<string, string> = {
    efficiency: "日々の移動負荷を減らしたい傾向",
    family: "家族との時間を大切にしたい傾向",
    safety: "安全性を最優先したい傾向",
    enjoyment: "移動体験の質も重視する傾向",
    adventure: "アクティブな体験を求める傾向",
  };
  return explanations[key] || "この価値を最も重視";
}
