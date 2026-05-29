"use client";

import type { DecisionStyleInfo, StylePresentation } from "@/types/graph";

type Props = {
  decisionStyle?: DecisionStyleInfo;
  presentation?: StylePresentation;
  visible: boolean;
};

export function DecisionStyleStorySection({
  decisionStyle,
  presentation,
  visible,
}: Props) {
  if (!decisionStyle && !presentation) return null;

  const label = presentation?.style_label ?? decisionStyle?.label ?? "";
  const description =
    presentation?.style_description ?? decisionStyle?.description ?? "";

  return (
    <section
      className={`rounded-xl border border-gold/30 bg-gradient-to-br from-amber-50/80 to-surface p-6 transition-all duration-700 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0"
      }`}
      aria-hidden={!visible}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-gold">
        あなたの Decision スタイル
      </p>
      <h2 className="mt-2 text-xl font-medium text-navy">{label}</h2>
      {description && (
        <p className="mt-2 text-sm leading-relaxed text-text">{description}</p>
      )}
      {presentation?.subheadline && (
        <p className="mt-3 rounded-md bg-white/60 px-3 py-2 text-sm text-navy">
          {presentation.subheadline}
        </p>
      )}
      {presentation?.ui_mode === "delegated_simple" &&
        (presentation.buyer_reviews?.length ?? 0) > 0 && (
          <p className="mt-3 text-xs text-text-muted">
            グラフ画面では購入者レビュー {presentation.buyer_reviews!.length}件・
            専門家コメント {presentation.expert_voices?.length ?? 0}件を表示します
          </p>
        )}
      {decisionStyle?.is_mixed && decisionStyle.secondary_label && (
        <p className="mt-2 text-xs text-text-muted">
          副次的傾向: {decisionStyle.secondary_label}
        </p>
      )}
    </section>
  );
}
