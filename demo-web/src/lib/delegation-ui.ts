export type DelegationLevel = "guide" | "co_pilot" | "auto";

export const DELEGATION_SUBTITLES: Record<DelegationLevel, string> = {
  guide: "候補と根拠をすべてご確認ください。最終判断はあなたにお任せします。",
  co_pilot: "Knowledge Graph が導いた、納得の3候補",
  auto: "AIが最適と判断した順に、スコアと結論を優先表示しています。",
};

export const DELEGATION_GRAPH_HINT: Record<DelegationLevel, string> = {
  guide: "つながりの全体像をご確認ください。",
  co_pilot: "あなたの価値観 → 負荷 → 機能 → 車種 のつながりを可視化しています",
  auto: "結論に至る主要な経路をハイライト表示しています",
};
