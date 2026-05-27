"use client";

import type { WhyPanelData } from "@/types/graph";

type Props = {
  data: WhyPanelData;
  visible?: boolean;
};

export function WhyPanel({ data, visible = true }: Props) {
  const maxPercent = Math.max(...data.values.map((v) => v.percent), 1);

  return (
    <aside
      className="space-y-6 rounded-md border border-border bg-surface p-5 transition-opacity duration-500"
      style={{ opacity: visible ? 1 : 0.4 }}
      aria-label="推薦の理由"
    >
      <h2 className="text-lg font-medium text-navy">なぜこの提案か</h2>

      <section>
        <h3 className="text-sm font-medium text-navy">重視価値</h3>
        <ul className="mt-3 space-y-3">
          {data.values.map((v) => (
            <li key={v.key ?? v.label}>
              <div className="flex justify-between text-sm">
                <span>{v.label}</span>
                <span className="tabular-nums text-text-muted">{v.percent}%</span>
              </div>
              <div
                className="mt-1 h-2 overflow-hidden rounded-full"
                style={{ background: "var(--color-border)" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    width: `${(v.percent / maxPercent) * 100}%`,
                    background: "linear-gradient(90deg, #1A365D, #2B6CB0)",
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>

      {data.loads.length > 0 && (
        <section>
          <h3 className="text-sm font-medium text-navy">検出された負荷</h3>
          <ul className="mt-3 space-y-2">
            {data.loads.map((load) => (
              <li key={load} className="flex gap-2 text-sm text-text">
                <span
                  className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                  style={{ background: "#38A169" }}
                  aria-hidden
                >
                  ✓
                </span>
                <span>{load}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.logic && (
        <section>
          <h3 className="text-sm font-medium text-navy">推薦ロジック</h3>
          <p
            className="mt-2 rounded-md px-3 py-3 text-sm leading-relaxed text-text"
            style={{
              background: "#F8FAFC",
              borderLeft: "3px solid #B8920C",
              fontFamily: "ui-monospace, monospace",
            }}
          >
            {data.logic}
          </p>
        </section>
      )}
    </aside>
  );
}
