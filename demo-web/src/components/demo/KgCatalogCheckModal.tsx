"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type KgCatalogResponse } from "@/lib/api-client";

const GROUP_LABELS: Record<string, string> = {
  Family: "ファミリー",
  Safety: "安心・安全",
  Comfort: "快適",
  Cargo: "荷物・収納",
  Economy: "経済性",
  Lifestyle: "ライフスタイル",
  Urban: "都市・運転",
  Accessibility: "乗り降り・介護",
  EV: "電動化",
};

const SOURCE_LABELS: Record<string, string> = {
  load: "負荷",
  value: "価値観",
  question: "回答",
  mapped: "マッピング",
};

const CATEGORY_LABELS: Record<string, string> = {
  safety: "安全",
  fuel_efficiency: "燃費",
  design: "デザイン",
  technology: "技術",
  space: "空間",
  comfort: "快適",
  family: "ファミリー",
  offroad: "走破",
  general: "一般",
  session: "セッション特定",
};

type CatalogKind = "needs" | "features";

type Props = {
  kind: CatalogKind;
  sessionId: string;
  topModel?: string;
  buttonLabel: string;
  className?: string;
};

export function KgCatalogCheckButton({
  kind,
  sessionId,
  topModel,
  buttonLabel,
  className = "",
}: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          className ||
          "rounded-md border border-navy/20 bg-white px-3 py-1.5 text-xs font-medium text-navy shadow-sm hover:bg-slate-50"
        }
      >
        {buttonLabel}
      </button>
      {open && (
        <KgCatalogModal
          kind={kind}
          sessionId={sessionId}
          topModel={topModel}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}

function KgCatalogModal({
  kind,
  sessionId,
  topModel,
  onClose,
}: {
  kind: CatalogKind;
  sessionId: string;
  topModel?: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<KgCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "selected">("selected");
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res =
        kind === "needs"
          ? await api.getKgNeedsCatalog(sessionId)
          : await api.getKgFeaturesCatalog(sessionId, topModel);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [kind, sessionId, topModel]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    if (!data?.items) return [];
    let list = data.items;
    if (filter === "selected") {
      list = list.filter((i) => i.selected);
    }
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((i) => {
      const hay = [
        i.name,
        i.label,
        i.group,
        i.category,
        ...(i.linked_needs ?? []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [data, filter, query]);

  const title =
    kind === "needs" ? "Need一覧（KG生活欲求）" : "TechnicalFeature一覧（製品機能）";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="kg-catalog-title"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-xl bg-surface shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="shrink-0 border-b border-border px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="kg-catalog-title" className="text-lg font-medium text-navy">
                {title}
              </h2>
              {data && (
                <p className="mt-1 text-sm text-text-muted">
                  あなたに特定:{" "}
                  <strong className="text-emerald-700">{data.selected_count}件</strong>
                  {" / "}
                  全{data.total}件
                  {kind === "features" && data.vehicle_name && (
                    <span className="ml-2">（参照車種: {data.vehicle_name}）</span>
                  )}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-text-muted hover:bg-slate-100"
              aria-label="閉じる"
            >
              ✕
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setFilter("selected")}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                filter === "selected"
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-100 text-text-muted"
              }`}
            >
              特定されたものだけ
            </button>
            <button
              type="button"
              onClick={() => setFilter("all")}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                filter === "all"
                  ? "bg-navy text-white"
                  : "bg-slate-100 text-text-muted"
              }`}
            >
              全件
            </button>
            <input
              type="search"
              placeholder="検索…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="min-w-[140px] flex-1 rounded-md border border-border px-3 py-1 text-sm"
            />
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {loading && (
            <p className="py-12 text-center text-sm text-text-muted">読み込み中…</p>
          )}
          {error && (
            <p className="py-8 text-center text-sm text-red-600">{error}</p>
          )}
          {!loading && !error && filtered.length === 0 && (
            <p className="py-8 text-center text-sm text-text-muted">
              {filter === "selected"
                ? "まだ特定された項目がありません。全件表示でマスタを確認できます。"
                : "該当する項目がありません。"}
            </p>
          )}
          {!loading && !error && filtered.length > 0 && (
            <ul className="space-y-2">
              {filtered.map((item) => (
                <li
                  key={item.name}
                  className={`rounded-lg border px-4 py-3 text-sm ${
                    item.selected
                      ? "border-emerald-300 bg-emerald-50/80"
                      : "border-border bg-white"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    {item.selected ? (
                      <span className="text-emerald-600" aria-hidden>
                        ✓
                      </span>
                    ) : (
                      <span className="text-slate-300" aria-hidden>
                        ○
                      </span>
                    )}
                    <span className="font-medium text-navy">
                      {kind === "needs" ? item.label || item.name : item.name}
                    </span>
                    {kind === "needs" && (
                      <code className="text-[10px] text-text-muted">{item.name}</code>
                    )}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-text-muted">
                    {kind === "needs" && item.group && (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5">
                        {GROUP_LABELS[item.group] ?? item.group}
                      </span>
                    )}
                    {kind === "needs" && item.selected && item.source && (
                      <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-800">
                        根拠: {SOURCE_LABELS[item.source] ?? item.source}
                        {item.source_load ? `（${item.source_load}）` : ""}
                      </span>
                    )}
                    {kind === "needs" && item.weight != null && (
                      <span>重み {item.weight}</span>
                    )}
                    {kind === "features" && item.category && (
                      <span className="rounded bg-purple-50 px-1.5 py-0.5 text-purple-800">
                        {CATEGORY_LABELS[item.category] ?? item.category}
                      </span>
                    )}
                    {kind === "features" &&
                      item.linked_needs &&
                      item.linked_needs.length > 0 && (
                        <span>
                          紐づく Need: {item.linked_needs.slice(0, 3).join(", ")}
                          {item.linked_needs.length > 3 ? "…" : ""}
                        </span>
                      )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <footer className="shrink-0 border-t border-border px-5 py-3 text-center">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md bg-navy px-6 py-2 text-sm text-white hover:bg-navy/90"
          >
            閉じる
          </button>
        </footer>
      </div>
    </div>
  );
}
